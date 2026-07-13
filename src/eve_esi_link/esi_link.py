"""Hold the EsiLink class."""

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
    EsiRequestList,
    EsiResponse,
    EsiResponseGroup,
    EsiResponseList,
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
    def __init__(
        self,
        auth_manager_db_path: Path,
        web_cache_path: Path,
        max_rate: float = 20.0,
        time_period: float = 1.0,
    ):
        """Initialize the EsiLink class.

        Args:
            auth_manager_db_path (Path): The path to the database file for the SqliteAuthManager.
            web_cache_path (Path): The path to the web cache.
            max_rate (float): The maximum number of requests per time period.
            time_period (float): The time period for rate limiting in seconds.
        """
        self.api_requester: api_request.ApiRequester | None = None
        self.auth_manager: SqliteAuthManager | None = None
        self.auth_manager_db_path = auth_manager_db_path
        self.web_cache_path = web_cache_path
        self.max_rate = max_rate
        self.time_period = time_period

    async def __aenter__(self) -> Self:
        """Async context manager entry point."""
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
        """Async context manager exit point."""
        if self.api_requester is not None:
            await self.api_requester.__aexit__(exc_type, exc_value, traceback)
        if self.auth_manager is not None:
            self.auth_manager.__exit__(exc_type, exc_value, traceback)

    def _check_api_requester_initialized(self) -> api_request.ApiRequester:
        """Check if the api_requester is initialized.

        Returns:
            ApiRequester: The initialized api_requester.
        """
        if self.api_requester is None:
            raise RuntimeError("EsiLink must be used as an async context manager.")
        return self.api_requester

    def _check_auth_manager(self) -> SqliteAuthManager:
        """Check if the auth_manager is initialized.

        Returns:
            SqliteAuthManager: The initialized auth_manager.
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
        """Check if the ESI request requires an access token and if it is provided.

        Args:
            esi_request: The ESI request to check.
            runtime_esi_request: The runtime ESI request object to populate with the
            access token if required.

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
        esi_requests: EsiRequestList | EsiRequestGroup,
        schema: EsiSchema,
    ) -> EsiResponseList | EsiResponseGroup:
        """Perform the given ESI requests and return the responses.

        This function accepts two different groupings of ESI requests: `EsiRequestList`
        and `EsiRequestGroup`. The primary difference between the two is how the requests
        are made. The `EsiRequestList` represents a simple list of requests that will be
        run one after another. These will still benefit from async processing, but only
        if they are paged requests. The pages will be requested concurrently, while the
        `EsiRequestGroup` allows for grouping requests together, and they will all be
        executed concurrently as a group.

        Args:
            esi_requests (EsiRequestList | EsiRequestGroup): The ESI requests to perform.
            schema (EsiSchema): The schema to use for the requests.

        Returns:
            EsiResponseList | EsiResponseGroup: The responses from the ESI requests.
        """
        requester = self._check_api_requester_initialized()
        if isinstance(esi_requests, EsiRequestGroup):
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
            # FIXME continue refactor from here
            return _make_esi_responses_from_responses(esi_requests, responses)

    @staticmethod
    def validate_request(
        esi_request: EsiRequest,
        schema: EsiSchema,
    ) -> None:
        """Validate the given ESI requests against the provided schema.

        Args:
            esi_request (EsiRequest): The ESI request to validate.
            schema (EsiSchema): The schema to validate against.

        Raises:
            EsiRequestValidationErrors: If any of the requests are invalid according to the schema.
        """
        try:
            validate_esi_request(esi_request, schema)
        except EsiRequestValidationErrors as e:
            logger.error("Validation failed for request %s: %s", esi_request, e)
            raise


def _make_request_from_runtime_request(
    runtime_request: RuntimeEsiRequest,
) -> api_request.Request:
    """Convert an EsiRequest to a Request object.

    Args:
        runtime_request (RuntimeEsiRequest): The runtime ESI request to convert.

    Returns:
        api_request.Request: The converted Request object.
    """
    return api_request.Request(
        request_key=runtime_request.request_key,
        method=runtime_request.method,
        url=runtime_request.url,
        headers=runtime_request.headers,
        body=runtime_request.json_payload,
        parameters=runtime_request.query_parameters,
        cache_key=runtime_request.cache_key,
        rate_key=runtime_request.rate_limit_key,
    )


def _make_esi_responses_from_responses(
    esi_requests: EsiRequests, responses: Responses
) -> EsiResponses:
    """Convert a Responses object to EsiResponses.

    Args:
        esi_requests (EsiRequests): The original ESI requests.
        responses (Responses): The Responses object to convert.

    Returns:
        EsiResponses: The converted EsiResponses.
    """
    successful_responses: dict[UUID, EsiResponse] = {}
    failed_responses: dict[UUID, FailedEsiResponse] = {}
    for request_id, response in responses.successful.items():
        esi_request = esi_requests[request_id]
        successful_responses[request_id] = EsiResponse(
            esi_request=esi_request, response=response
        )
    for request_id, response in responses.failed.items():
        esi_request = esi_requests[request_id]
        failed_responses[request_id] = FailedEsiResponse(
            esi_request=esi_request,
            failed_response=response,
        )
    return EsiResponses(successful=successful_responses, failed=failed_responses)
