"""Library entrypoint for schema-validated ESI request execution.

The EsiLink class is the main API used by library consumers. It coordinates
schema validation, runtime request construction, authorization token lookup,
batch HTTP execution, and response shaping.
"""

import logging
from pathlib import Path
from types import TracebackType
from typing import Self
from uuid import UUID

import api_request
from api_request.cache import SqliteCacheFactory
from api_request.rate_limit import AiolimiterRateLimiterFactory
from api_request.request.models import Responses
from eve_auth_manager.sqlite.manager import SqliteAuthManager

from eve_esi_link.esi_request.models import (
    EsiRequest,
    EsiRequestGroup,
    EsiResponse,
    EsiResponseGroup,
    FailedEsiResponse,
    RuntimeEsiRequest,
)
from eve_esi_link.esi_request.runtime_builder import build_runtime_esi_request
from eve_esi_link.esi_request.validate import (
    EsiRequestValidationErrors,
    validate_esi_request,
)
from eve_esi_link.schema.models import EsiSchema, SchemaOperation

logger = logging.getLogger(__name__)


class EsiLink:
    """Execute ESI request groups with schema validation and runtime services.

    This class must be used as an async context manager so request and auth
    backends are initialized and cleaned up correctly.
    """

    def __init__(
        self,
        auth_manager_db_path: Path,
        web_cache_path: Path,
        max_rate: float = 20.0,
        time_period: float = 1.0,
    ):
        """Configure an EsiLink instance.

        Args:
            auth_manager_db_path: Path to the SqliteAuthManager database.
            web_cache_path: Path to the HTTP response cache database.
            max_rate: Maximum number of requests per rate-limit window.
            time_period: Window duration in seconds for rate limiting.
        """
        self.api_requester: api_request.ApiRequester | None = None
        self.auth_manager: SqliteAuthManager | None = None
        self.auth_manager_db_path = auth_manager_db_path
        self.web_cache_path = web_cache_path
        self.max_rate = max_rate
        self.time_period = time_period

    async def __aenter__(self) -> Self:
        """Initialize API requester and auth manager resources.

        Returns:
            The initialized EsiLink instance.
        """
        web_cache_factory = SqliteCacheFactory(db_path=self.web_cache_path)
        rate_limiter_factory = AiolimiterRateLimiterFactory(
            max_rate=self.max_rate, time_period=self.time_period
        )
        self.api_requester = api_request.ApiRequester(
            cache_factory=web_cache_factory, rate_limiter_factory=rate_limiter_factory
        )
        self.auth_manager = SqliteAuthManager(db_path=self.auth_manager_db_path)
        await self.api_requester.__aenter__()
        self.auth_manager.__enter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ):
        """Release API requester and auth manager resources."""
        if self.api_requester is not None:
            await self.api_requester.__aexit__(exc_type, exc_value, traceback)
        if self.auth_manager is not None:
            self.auth_manager.__exit__(exc_type, exc_value, traceback)

    def _check_api_requester_initialized(self) -> api_request.ApiRequester:
        """Return initialized ApiRequester instance.

        Returns:
            Initialized ApiRequester.

        Raises:
            RuntimeError: If EsiLink is used outside async context manager scope.
        """
        if self.api_requester is None:
            raise RuntimeError("EsiLink must be used as an async context manager.")
        return self.api_requester

    def _check_auth_manager(self) -> SqliteAuthManager:
        """Return initialized SqliteAuthManager instance.

        Returns:
            Initialized SqliteAuthManager.

        Raises:
            RuntimeError: If EsiLink is used outside async context manager scope.
        """
        if self.auth_manager is None:
            raise RuntimeError("EsiLink must be used as an async context manager.")
        return self.auth_manager

    def _check_operation(
        self, operation_id: str, esi_schema: EsiSchema
    ) -> SchemaOperation:
        """Check if the operation_id exists in the schema.

        Args:
            operation_id (str): The operation ID to check.
            esi_schema (EsiSchema): The schema to check against.

        Returns:
            SchemaOperation: The schema operation corresponding to the operation ID.

        Raises:
            ValueError: If the operation ID is not found in the schema.
        """
        operation = esi_schema.operations.get(operation_id)
        if operation is None:
            raise ValueError(f"Operation ID '{operation_id}' not found in ESI schema.")
        return operation

    async def _check_required_access_token(
        self,
        esi_request: EsiRequest,
        runtime_esi_request: RuntimeEsiRequest,
    ) -> None:
        """Attach access token to runtime request when authorization is required.

        Args:
            esi_request: The ESI request to check.
            runtime_esi_request: Runtime request to mutate with access token.

        Raises:
            ValueError: If authorization tuple is incomplete.
        """
        if not esi_request.has_authorization:
            return
        auth_manager = self._check_auth_manager()
        cred_id = esi_request.credential_id
        character_id = esi_request.character_id
        if cred_id is None or character_id is None:
            raise ValueError(
                "Credential ID and Character ID must be provided for authorized requests."
            )
        access_token = auth_manager.get_character(cred_id, character_id).access_token
        runtime_esi_request.access_token = access_token

    async def make_requests(
        self,
        esi_requests: EsiRequestGroup,
        schema: EsiSchema,
    ) -> EsiResponseGroup:
        """Validate, execute, and group responses for an ESI request batch.

        Args:
            esi_requests: ESI requests to execute.
            schema: Schema used for operation lookup and validation.

        Returns:
            Grouped successful and failed responses keyed by runtime request key.

        Raises:
            RuntimeError: If EsiLink is used outside async context manager scope.
            EsiRequestValidationErrors: If any request fails schema validation.
            Exception: Any backend execution exception from request or auth layers.
        """
        requester = self._check_api_requester_initialized()

        runtime_requests: dict[UUID, RuntimeEsiRequest] = {}
        for _, request in esi_requests.requests.items():
            self.validate_request(request, schema)
            runtime_request = build_runtime_esi_request(request, schema)
            await self._check_required_access_token(request, runtime_request)
            runtime_requests[runtime_request.request_key] = runtime_request

        request_objects = {
            key: _make_request_from_runtime_request(request)
            for key, request in runtime_requests.items()
        }
        responses: Responses = await requester.process_requests(request_objects)
        esi_responses = _make_esi_response_group(
            responses, esi_requests, runtime_requests
        )
        return esi_responses

    @staticmethod
    def validate_request(
        esi_request: EsiRequest,
        schema: EsiSchema,
    ) -> None:
        """Validate one ESI request against the provided schema.

        Args:
            esi_request: The ESI request to validate.
            schema: Schema used for validation rules.

        Raises:
            EsiRequestValidationErrors: If request data violates schema-derived rules.
        """
        try:
            validate_esi_request(esi_request, schema)
        except EsiRequestValidationErrors as e:
            logger.error("Validation failed for request %s: %s", esi_request, e)
            raise


def _make_esi_response_group(
    responses: Responses,
    requests: EsiRequestGroup,
    runtime_requests: dict[UUID, RuntimeEsiRequest],
) -> EsiResponseGroup:
    """Convert api_request response groups into EsiResponseGroup containers."""
    successful_responses: dict[UUID, EsiResponse] = {}
    failed_responses: dict[UUID, FailedEsiResponse] = {}
    for request_id, response in responses.successful.items():
        runtime_request = runtime_requests[request_id]
        successful_responses[request_id] = EsiResponse(
            esi_runtime_request=runtime_request, response=response
        )
    for request_id, response in responses.failed.items():
        runtime_request = runtime_requests[request_id]
        failed_responses[request_id] = FailedEsiResponse(
            esi_runtime_request=runtime_request,
            failed_response=response,
        )
    return EsiResponseGroup(
        name=requests.name,
        description=requests.description,
        requests=requests.requests,
        successful_responses=successful_responses,
        failed_responses=failed_responses,
    )


def _make_request_from_runtime_request(
    runtime_request: RuntimeEsiRequest,
) -> api_request.Request:
    """Convert RuntimeEsiRequest to api_request.Request.

    Args:
        runtime_request: Runtime ESI request to convert.

    Returns:
        Converted api_request.Request object.
    """
    return api_request.Request(
        request_key=runtime_request.request_key,
        method=runtime_request.method,
        url=runtime_request.url,
        headers=runtime_request.headers_with_authorization,
        body=runtime_request.json_payload,
        parameters=runtime_request.query_parameters,
        cache_key=runtime_request.cache_key,
        rate_key=runtime_request.rate_limit_key,
    )
