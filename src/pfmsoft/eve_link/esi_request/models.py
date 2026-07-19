"""Data models for ESI request input, runtime request state, and responses.

These models define serialization and token-redaction boundaries for request and
response payloads used by both CLI and library code.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4, uuid5

from pfmsoft.api_request import Response
from pfmsoft.api_request.request.models import FailedResponse
from pydantic import RootModel


class UserSettableHeaders(StrEnum):
    ACCEPT_LANGUAGE = "Accept-Language"
    X_TENANT = "X-Tenant"
    X_COMPATIBILITY_DATE = "X-Compatibility-Date"


@dataclass(slots=True, kw_only=True)
class EsiRequest:
    """Represents a single ESI request to be executed.

    Can be loaded from a file or created programmatically. The request_id is used to
    identify the request.

    Requests can be be contained in a RequestGroup, and the request_id is used
    to link the Request to its RuntimeRequest, and to the final EsiResponse.
    """

    request_id: UUID = field(default_factory=uuid4)
    """The unique identifier for the request. This is used to link the request to various 
        objects during the request lifecycle."""
    name: str | None = None
    """An optional name for the request. This is used for documentation purposes, 
        and can be used to provide context for the request when viewing it in a UI or in 
        logs."""
    description: str | None = None
    """An optional description of the request. This is used for documentation purposes, 
        and can be used to provide context for the request when viewing it in a UI or in 
        logs."""
    operation_id: str
    """The operation ID of the request, corresponding to the operationId in the ESI 
        OpenAPI schema."""
    path_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The path parameters for the request, if applicable. This is used to fill in the 
        path parameters in the URL template."""
    query_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The query parameters for the request, if applicable.
    
    This is used to fill in the query parameters in the URL template.
    
    NOTE: The page parameter is handled automatically by eve-link, and should not 
        be set manually. If it is set, it will raise a validation error. This is to help 
        normalize cache keys, which rely on predictable parameters.
    """
    header_parameters: dict[str, str] = field(default_factory=dict[str, str])
    """The header parameters for the request, if applicable. 
    
        Acceptable headers are:
        - Accept-Language
        - X-Tenant
        - X-Compatibility-Date
        
        Do not use this to set:
        
        - If-None-Match
        - If-Modified-Since headers. 

        Those are set at runtime during HTTP execution."""
    json_payload: Any | None = None
    """The JSON payload of the request, if applicable. This is used for POST, PUT, and PATCH 
        requests."""
    character_id: int | None = None
    """The character ID used for authorization."""
    credential_id: UUID | None = None
    """The credential ID for authorization. This is used to link the authorization
        to the credential that was used to obtain it. This UUID is obtained from the 
        credential manager that provides the access token."""

    @property
    def has_authorization(self) -> bool:
        """Check if the request has an authorization."""
        return self.character_id is not None and self.credential_id is not None

    @property
    def authorization_slug(self) -> UUID:
        """Get the authorization slug for the authorization.

        This is a UUID that is generated from the character ID and credential ID, and is
        used as part of the cache key to differentiate between different cached
        authorized requests.

        Returns:
            The authorization slug for the authorization.
        """
        if not self.has_authorization:
            raise ValueError(
                "Cannot generate authorization key without both character_id and credential_id."
            )
        return uuid5(self.credential_id, str(self.character_id))  # type: ignore


EsiRequestRoot = RootModel[EsiRequest]


@dataclass(slots=True, kw_only=True)
class RuntimeEsiRequest:
    request_key: UUID
    """The unique key for this runtime request."""
    url: str
    """The URL for this runtime request."""

    method: str
    """The HTTP method for this runtime request."""
    cache_key: UUID | None
    """The cache key for this runtime request, if any."""

    rate_limit_key: str
    """The rate limit key for this runtime request, if any."""

    headers: dict[str, str] = field(default_factory=dict[str, str])
    """The headers for this runtime request."""

    query_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The query parameters for this runtime request."""
    json_payload: dict[str, Any] | None = None
    """The JSON payload for this runtime request, if any."""
    access_token: str | None = None
    """The access token for this runtime request, if any."""

    def purge_access_token(self) -> None:
        """Purge the access token for this runtime request.

        THIS SHOULD BE CALLED BEFORE SERIALIZATION TO UNTRUSTED DESTINATIONS.

        If the access token is already `None`, this method does nothing.
        Otherwise, it sets the access token to `"REDACTED"`.
        """
        if self.access_token is None:
            return
        self.access_token = "REDACTED"

    @property
    def headers_with_authorization(self) -> dict[str, str]:
        """Return the combined headers for this runtime request.

        This includes the runtime headers, and the Authorization header if an access
        token is present.

        """
        combined = dict(self.headers)
        if self.access_token is not None:
            combined["Authorization"] = f"Bearer {self.access_token}"
        return combined


@dataclass(slots=True, kw_only=True, frozen=True)
class EsiResponse:
    esi_runtime_request: RuntimeEsiRequest
    """The request that generated this response."""
    response: Response
    """The response associated with this EsiResponse."""

    def _purge_secrets(self) -> None:
        """Purge the access tokens from this response."""
        self.esi_runtime_request.purge_access_token()
        # FIXME: will be in next api-request release.
        # self.response.purge_secrets()

    def serialize(self, indent: int | None = None) -> str:
        """Serialize the EsiResponse."""
        response_copy = deepcopy(self)
        response_copy._purge_secrets()
        return EsiResponseRoot(root=response_copy).model_dump_json(indent=indent)


EsiResponseRoot = RootModel[EsiResponse]


@dataclass(slots=True, kw_only=True, frozen=True)
class FailedEsiResponse:
    esi_runtime_request: RuntimeEsiRequest
    """The request that generated this failed response."""
    failed_response: FailedResponse
    """The failed response associated with this FailedEsiResponse."""

    def _purge_secrets(self) -> None:
        """Purge the access tokens from this response."""
        self.esi_runtime_request.purge_access_token()
        # FIXME: will be in next api-request release.
        # self.failed_response.purge_secrets()

    def serialize(self, indent: int | None = None) -> str:
        """Serialize the FailedEsiResponse."""
        response_copy = deepcopy(self)
        response_copy._purge_secrets()
        return FailedEsiResponseRoot(root=response_copy).model_dump_json(indent=indent)


FailedEsiResponseRoot = RootModel[FailedEsiResponse]


# NOTE: This is for a future possible feature to make it easier to hand code requests,
# as the UUID could be generated on deserialization. These would be converted to
# EsiRequestGroup objects for runtime execution. This is not currently used, but is
# left here for future consideration.
@dataclass(slots=True, kw_only=True)
class EsiRequestList:
    name: str | None = None
    """The name of this list of runtime ESI requests."""
    description: str | None = None
    """An optional description of this list of runtime ESI requests."""
    requests: list[EsiRequest] = field(default_factory=list[EsiRequest])
    """The list of ESI requests."""


EsiRequestListRoot = RootModel[EsiRequestList]


@dataclass(slots=True, kw_only=True)
class EsiRequestGroup:
    name: str | None = None
    """The name of this group of runtime ESI requests."""
    description: str | None = None
    """An optional description of this group of runtime ESI requests."""
    requests: dict[UUID, EsiRequest] = field(default_factory=dict[UUID, EsiRequest])
    """The dict of  ESI requests in this group."""


EsiRequestGroupRoot = RootModel[EsiRequestGroup]


@dataclass(slots=True, kw_only=True)
class EsiResponseList(EsiRequestList):
    successful_responses: dict[UUID, EsiResponse] = field(
        default_factory=dict[UUID, EsiResponse]
    )
    """The dict of successful ESI responses."""
    failed_responses: dict[UUID, FailedEsiResponse] = field(
        default_factory=dict[UUID, FailedEsiResponse]
    )
    """The dict of failed ESI responses."""

    def purge_tokens(self) -> None:
        """Purge the access tokens from all successful and failed ESI responses."""
        for response in self.successful_responses.values():
            response.esi_runtime_request.purge_access_token()
        for failed_response in self.failed_responses.values():
            failed_response.esi_runtime_request.purge_access_token()


EsiResponseListRoot = RootModel[EsiResponseList]


@dataclass(slots=True, kw_only=True)
class EsiResponseGroup(EsiRequestGroup):
    successful_responses: dict[UUID, EsiResponse] = field(
        default_factory=dict[UUID, EsiResponse]
    )
    """The dict of successful ESI responses in this group."""
    failed_responses: dict[UUID, FailedEsiResponse] = field(
        default_factory=dict[UUID, FailedEsiResponse]
    )
    """The dict of failed ESI responses in this group."""

    def _purge_secrets(self) -> None:
        """Purge the access tokens from all successful and failed ESI responses in this group."""
        for response in self.successful_responses.values():
            response._purge_secrets()  # type: ignore
        for failed_response in self.failed_responses.values():
            failed_response._purge_secrets()  # type: ignore

    def serialize(self, indent: int | None = None) -> str:
        """Purge secrets and serialize the EsiResponseGroup to a JSON string."""
        copied_object = deepcopy(self)
        copied_object._purge_secrets()
        return EsiResponseGroupRoot(root=copied_object).model_dump_json(indent=indent)


EsiResponseGroupRoot = RootModel[EsiResponseGroup]
