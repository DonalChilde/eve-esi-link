from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4, uuid5

from pydantic import RootModel


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
    json_body: Any | None = None
    """The JSON body of the request, if applicable. This is used for POST, PUT, PATCH 
        requests."""
    # The following fields are set at run time, and are not normally serialized with the request.
    # A None value signals that the runtime values have not been set yet.
    _url: str | None = field(default=None, init=False, repr=False)
    _method: str | None = field(default=None, init=False, repr=False)
    _cache_key: UUID | None = field(default=None, init=False, repr=False)
    _rate_limit_key: str | None = field(default=None, init=False, repr=False)
    _runtime_headers: dict[str, str] | None = field(
        default=None, init=False, repr=False
    )
    _runtime_query_parameters: dict[str, str | int | float] | None = field(
        default=None, init=False, repr=False
    )

    def is_runnable(self) -> bool:
        """Check if the request is runnable.

        A request is considered runnable if it has all the runtime values set, which are
        required to make the actual HTTP request.

        Returns:
            True if the request is runnable, False otherwise.
        """
        return all([
            self._url is not None,
            self._method is not None,
            self._cache_key is not None,
            self._rate_limit_key is not None,
            self._runtime_headers is not None,
            self._runtime_query_parameters is not None,
        ])

    @property
    def url(self) -> str:
        """The URL of the request, if applicable.

        This is set at run time, and is used to make the actual HTTP request.

        Returns:
            The URL of the request, or None if not set.
        """
        if self._url is None:
            raise ValueError("URL has not been set yet.")
        return self._url

    @url.setter
    def url(self, value: str) -> None:
        """Set the URL of the request.

        This is set at run time, and is used to make the actual HTTP request.

        Args:
            value: The URL of the request.
        """
        self._url = value

    @property
    def method(self) -> str:
        """The HTTP method of the request, if applicable.

        This is set at run time, and is used to make the actual HTTP request.

        Returns:
            The HTTP method of the request.
        """
        if self._method is None:
            raise ValueError("HTTP method has not been set yet.")
        return self._method

    @method.setter
    def method(self, value: str) -> None:
        """Set the HTTP method of the request.

        This is set at run time, and is used to make the actual HTTP request.

        Args:
            value: The HTTP method of the request.
        """
        self._method = value

    @property
    def cache_key(self) -> UUID:
        """The cache key for the request, if applicable.

        This is set at run time, and is used to cache the response for the request.

        Returns:
            The cache key of the request.
        """
        if self._cache_key is None:
            raise ValueError("Cache key has not been set yet.")
        return self._cache_key

    @cache_key.setter
    def cache_key(self, value: UUID) -> None:
        """Set the cache key of the request.

        This is set at run time, and is used to cache the response for the request.

        Args:
            value: The cache key of the request.
        """
        self._cache_key = value

    @property
    def rate_limit_key(self) -> str:
        """The rate limit key for the request, if applicable.

        This is set at run time, and is used to track the rate limit for the request.

        Returns:
            The rate limit key of the request.
        """
        if self._rate_limit_key is None:
            raise ValueError("Rate limit key has not been set yet.")
        return self._rate_limit_key

    @rate_limit_key.setter
    def rate_limit_key(self, value: str) -> None:
        """Set the rate limit key of the request.

        This is set at run time, and is used to track the rate limit for the request.

        Args:
            value: The rate limit key of the request.
        """
        self._rate_limit_key = value

    @property
    def runtime_headers(self) -> dict[str, str]:
        """The runtime headers for the request.

        The _runtime_headers field is set at run time, and is used to set the runtime
        headers for the actual HTTP request.

        These headers should include
        - Accept-Language - if missing, set to `en` at run time.
        - X-Tenant - if missing, set to the default tenant at run time.
        - X-Compatibility-Date - if missing, set to the most recent compatibility date at run time.
        - Authorization (if applicable)

        This property returns the combined headers, with the _runtime_headers taking
        precedence over the header_parameters field, normalized to lower case keys.

        Returns:
            The headers of the request.
        """
        if self._runtime_headers is None:
            raise ValueError("Runtime headers have not been set yet.")
        # normalize header keys to lower case for consistency, and combine
        # query headers with runtime headers. runtime headers take precedence.
        combined_headers = {
            **{k.lower(): v for k, v in self.header_parameters.items()},
            **{k.lower(): v for k, v in self._runtime_headers.items()},
        }
        return combined_headers

    @runtime_headers.setter
    def runtime_headers(self, value: dict[str, str]) -> None:
        """Set the runtime headers of the request.

        This is set at run time, and is used to set the runtime headers for the actual
        HTTP request.

        Args:
            value: The runtime headers of the request.
        """
        self._runtime_headers = value

    @property
    def runtime_query_parameters(self) -> dict[str, str | int | float]:
        """The runtime query parameters for the request.

        The _runtime_query_parameters field is set at run time, and is used to set the
        runtime query parameters for the actual HTTP request.

        These query parameters should include
        - page - if missing, set to 1 at run time.

        This property returns the combined query parameters, with the
        _runtime_query_parameters taking precedence over the query_parameters field.


        Returns:
            The combined query parameters of the request.
        """
        if self._runtime_query_parameters is None:
            raise ValueError("Runtime query parameters have not been set yet.")
        combined_query_parameters = (
            self.query_parameters | self._runtime_query_parameters
        )
        return combined_query_parameters

    @runtime_query_parameters.setter
    def runtime_query_parameters(self, value: dict[str, str | int | float]) -> None:
        """Set the runtime query parameters of the request.

        This is set at run time, and is used to set the runtime query parameters for the actual
        HTTP request.

        Args:
            value: The runtime query parameters of the request.
        """
        self._runtime_query_parameters = value

    def inject_authorization_header(self) -> None:
        """Inject the authorization header into the runtime headers.

        This is used to authenticate requests to the ESI API on behalf of a character.
        If the request does not require authorization,signaled by the authorization
        attribute == None, this method does nothing.

        This should be called after the runtime headers have been set, and before the
        request is executed.

        Raises:
            ValueError: If the runtime headers have not been set yet.
            ValueError: If the authorization access token is not set when authorization
                is required.
        """
        if self.authorization is None:
            return
        if self._runtime_headers is None:
            raise ValueError("Runtime headers have not been set yet.")
        if self.authorization.access_token is None:
            raise ValueError(
                "Authorization access token is not set. Cannot inject authorization header."
            )
        self._runtime_headers["authorization"] = (
            f"Bearer {self.authorization.access_token}"
        )

    def loggable(self) -> dict[str, Any]:
        """Return a loggable representation of the request.

        This is used to log the request in a human-readable format. It removes any
        sensitive information from the request, such as the authorization access token.

        Returns:
            A loggable representation of the request.
        """
        return {
            "request_id": str(self.request_id),
            "description": self.description,
            "operation_id": self.operation_id,
            "path_parameters": self.path_parameters,
            "query_parameters": self.query_parameters,
            "header_parameters": self.header_parameters,
            "authorization": {
                "character_id": self.authorization.character_id,
                "credential_id": str(self.authorization.credential_id),
                "access_token": "PRESENT->REDACTED"
                if self.authorization.access_token is not None
                else None,
            }
            if self.authorization is not None
            else None,
            "json_body": self.json_body,
        }

    def loggable_runtime(self) -> dict[str, Any]:
        """Return a loggable representation of the request with runtime values.

        This is used to log the request in a human-readable format. It removes any
        sensitive information from the request, such as the authorization access token.

        Returns:
            A loggable representation of the request with runtime values.
        """
        return {
            **self.loggable(),
            "url": self._url,
            "method": self._method,
            "cache_key": str(self._cache_key) if self._cache_key is not None else None,
            "rate_limit_key": self._rate_limit_key,
            "runtime_headers": self._runtime_headers,
            "runtime_query_parameters": self._runtime_query_parameters,
        }


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
