from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from pydantic import RootModel
from whenever import Instant


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
    _access_token: str | None = field(default=None, init=False, repr=False)
    """The access token for the authorization. This is used to authenticate
        requests to the ESI API on behalf of the character."""

    @property
    def access_token(self) -> str | None:
        """Get the access token for the authorization.

        Returns:
            The access token for the authorization, or None if not set.
        """
        return self._access_token


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

        Those are set at runtime."""
    authorization: EsiAuthorization | None = None
    """The authorization for the request, if applicable. This is used to authenticate
        requests to the ESI API on behalf of a character. If the request does not 
        require authorization, this should be None."""
    json_body: Any | None = None
    """The JSON body of the request, if applicable. This is used for POST, PUT, PATCH 
        requests."""
    # The following fields are set at run time, and are not serialized with the request.
    _url: str | None = field(default=None, init=False, repr=False)
    _cache_key: UUID | None = field(default=None, init=False, repr=False)
    _rate_limit_key: str | None = field(default=None, init=False, repr=False)
    _headers: dict[str, str] | None = field(default=None, init=False, repr=False)

    @property
    def url(self) -> str | None:
        """The URL of the request, if applicable.

        This is set at run time, and is used to make the actual HTTP request.

        Returns:
            The URL of the request, or None if not set.
        """
        return self._url

    @property
    def cache_key(self) -> UUID | None:
        """The cache key for the request, if applicable.

        This is set at run time, and is used to cache the response for the request.

        Returns:
            The cache key of the request, or None if not set.
        """
        return self._cache_key

    @property
    def rate_limit_key(self) -> str | None:
        """The rate limit key for the request, if applicable.

        This is set at run time, and is used to track the rate limit for the request.

        Returns:
            The rate limit key of the request, or None if not set.
        """
        return self._rate_limit_key

    @property
    def headers(self) -> dict[str, str] | None:
        """The headers for the request, if applicable.

        This is set at run time, and is used to set the headers for the actual HTTP request.

        These headers should include
        - Accept-Language - if missing, set to `en` at run time.
        - X-Tenant - if missing, set to the default tenant at run time.
        - X-Compatibility-Date - if missing, set to the most recent compatibility date at run time.
        - Authorization (if applicable)

        Returns:
            The headers of the request, or None if not set.
        """
        return self._headers


EsiRequestRoot = RootModel[EsiRequest]


@dataclass(slots=True, kw_only=True, frozen=True)
class EsiResponse:
    esi_request: EsiRequest
    """The request that generated this response."""


@dataclass(slots=True, kw_only=True, frozen=True)
class FailedResponse:
    esi_request: EsiRequest
    """The request that generated this failed response."""
    error: str
    """The error message associated with the failed response."""


@dataclass(slots=True, kw_only=True, frozen=True)
class EsiResponses:
    successful: dict[UUID, EsiResponse] = field(default_factory=dict[UUID, EsiResponse])
    failed: dict[UUID, FailedResponse] = field(
        default_factory=dict[UUID, FailedResponse]
    )


EsiResponsesRoot = RootModel[EsiResponses]


EsiRequests = dict[UUID, EsiRequest]

EsiRequestsRoot = RootModel[EsiRequests]
