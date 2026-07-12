"""Models for ESI requests and responses."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4, uuid5

from api_request import Response
from api_request.request.models import FailedResponse
from pydantic import RootModel


class UserSettableHeaders(StrEnum):
    ACCEPT_LANGUAGE = "Accept-Language"
    X_TENANT = "X-Tenant"
    X_COMPATIBILITY_DATE = "X-Compatibility-Date"


@dataclass(slots=True, kw_only=True)
class EsiAuthorization:
    """Represents an ESI authorization for a character.

    This is used to authenticate requests to the ESI API on behalf of a character.

    Because access tokens expire, they are not serialized with the EsiAuthorization object.
    Access tokens are expected to be provided at runtime, and can be obtained from the
    credential manager that provides the access token. The access token is used to
    authenticate requests to the ESI API on behalf of the character.
    """

    character_id: int
    """The character ID for the authorization."""
    credential_id: UUID
    """The credential ID for the authorization. This is used to link the authorization
        to the credential that was used to obtain it. This UUID is obtained from the 
        credential manager that provides the access token."""

    @property
    def authorization_key(self) -> UUID:
        """Get the authorization key for the authorization.

        This is a UUID that is generated from the character ID and credential ID, and is
        used to as part of the cache key to differentiate between different authorizations.

        Returns:
            The authorization key for the authorization.
        """
        return uuid5(self.credential_id, str(self.character_id))


@dataclass(slots=True, kw_only=True)
class EsiRequest:
    """Represents a single ESI request to be executed.

    Can be loaded from a file or created programmatically. The request_id is used to
    identify the request.

    Requests can be be contained in a RequestGroup, and the request_id is used
    to link the Request to its RuntimeRequest, and to the final Response.
    """

    request_id: UUID = field(default_factory=uuid4)
    """The unique identifier for the request. This is used to link the request to various 
        objects during the request lifecycle."""
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
    
    NOTE: The page parameter is handled automatically by the esi-link, and should not 
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
    authorization: EsiAuthorization | None = None
    """The authorization for the request, if applicable. This is used to authenticate
        requests to the ESI API on behalf of a character. If the request does not 
        require authorization, this should be None."""
    json_payload: Any | None = None
    """The JSON payload of the request, if applicable. This is used for POST, PUT, PATCH 
        requests."""


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
    """The runtime headers for this runtime request."""

    query_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The runtime query parameters for this runtime request."""
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
    def combined_headers(self) -> dict[str, str]:
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


@dataclass(slots=True, kw_only=True, frozen=True)
class FailedEsiResponse:
    esi_runtime_request: RuntimeEsiRequest
    """The request that generated this failed response."""
    failed_response: FailedResponse
    """The failed response associated with this FailedEsiResponse."""


@dataclass(slots=True, kw_only=True)
class EsiRequestList:
    name: str
    """The name of this list of runtime ESI requests."""
    description: str | None = None
    """An optional description of this list of runtime ESI requests."""
    requests: list[EsiRequest] = field(default_factory=list[EsiRequest])
    """The list of ESI requests."""


@dataclass(slots=True, kw_only=True)
class EsiRequestGroup:
    name: str
    """The name of this group of runtime ESI requests."""
    description: str | None = None
    """An optional description of this group of runtime ESI requests."""
    requests: dict[UUID, EsiRequest] = field(default_factory=dict[UUID, EsiRequest])
    """The dict of  ESI requests in this group."""


@dataclass(slots=True, kw_only=True)
class EsiResponseList(EsiRequestList):
    successful_responses: list[EsiResponse] = field(default_factory=list[EsiResponse])
    """The list of successful ESI responses."""
    failed_responses: list[FailedEsiResponse] = field(
        default_factory=list[FailedEsiResponse]
    )
    """The list of failed ESI responses."""

    def purge_tokens(self) -> None:
        """Purge the access tokens from all successful and failed ESI responses."""
        for response in self.successful_responses:
            response.esi_runtime_request.purge_access_token()
        for failed_response in self.failed_responses:
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

    def purge_tokens(self) -> None:
        """Purge the access tokens from all successful and failed ESI responses in this group."""
        for response in self.successful_responses.values():
            response.esi_runtime_request.purge_access_token()
        for failed_response in self.failed_responses.values():
            failed_response.esi_runtime_request.purge_access_token()


EsiResponseGroupRoot = RootModel[EsiResponseGroup]
