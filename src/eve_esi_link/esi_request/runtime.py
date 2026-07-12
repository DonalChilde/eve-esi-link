"""Set runtime attributes for ESI requests based on the ESI schema."""

from uuid import uuid5

from eve_esi_link.helpers.canonicalize_url import combine_and_canonicalize_url

from ..schema.models import EsiSchema
from ..settings import APP_NAMESPACE
from .models import EsiRequest


def set_runtime_attributes(esi_request: EsiRequest, esi_schema: EsiSchema) -> None:
    """Set the runtime attributes of an ESI request based on the schema.

    Args:
        esi_request: The ESI request to set the runtime attributes for.
        esi_schema: The ESI schema to use for setting the runtime attributes.
    """
    _set_url(esi_request, esi_schema)
    _set_queries(esi_request, esi_schema)
    _set_headers(esi_request, esi_schema)
    _set_method(esi_request, esi_schema)
    _set_rate_limit(esi_request, esi_schema)

    # Run this last to ensure all required attributes are set before generating the
    # cache key
    _set_cache_key(esi_request, esi_schema)


def _set_url(esi_request: EsiRequest, esi_schema: EsiSchema) -> None:
    """Set the URL of an ESI request based on the schema.

    Args:
        esi_request: The ESI request to set the URL for.
        esi_schema: The ESI schema to use for setting the URL.
    """
    esi_request.url = esi_schema.operation_url(esi_request.operation_id)


def _set_method(esi_request: EsiRequest, esi_schema: EsiSchema) -> None:
    """Set the HTTP method of an ESI request based on the schema.

    Args:
        esi_request: The ESI request to set the HTTP method for.
        esi_schema: The ESI schema to use for setting the HTTP method.
    """
    operation = esi_schema.operations.get(esi_request.operation_id)
    if operation is None:
        raise ValueError(
            f"Operation ID '{esi_request.operation_id}' not found in ESI schema."
        )
    esi_request.method = operation.method.value


def _set_cache_key(esi_request: EsiRequest, esi_schema: EsiSchema) -> None:
    """Set the cache key of an ESI request based on the schema.

    Args:
        esi_request: The ESI request to set the cache key for.
        esi_schema: The ESI schema to use for setting the cache key.
    """
    # Generate a cache key based on a number of factors.
    method = esi_request.method
    url = combine_and_canonicalize_url(
        esi_request.url, esi_request.runtime_query_parameters or {}
    )
    authorization_key = (
        str(esi_request.authorization.authorization_key)
        if esi_request.authorization
        else ""
    )
    compatibility_date = esi_request.runtime_headers.get(
        "X-Compatibility-Date".lower(), ""
    )
    cache_key = uuid5(
        APP_NAMESPACE,
        f"{method}:{url}:{authorization_key}:{compatibility_date}",
    )
    esi_request.cache_key = cache_key


def _set_rate_limit(esi_request: EsiRequest, esi_schema: EsiSchema) -> None:
    """Set the rate limit group of an ESI request based on the schema.

    Args:
        esi_request: The ESI request to set the rate limit for.
        esi_schema: The ESI schema to use for setting the rate limit.
    """
    operation = esi_schema.operations.get(esi_request.operation_id)
    if operation is None:
        raise ValueError(
            f"Operation ID '{esi_request.operation_id}' not found in ESI schema."
        )
    rate_limit = operation.rate_limit
    rate_limit_group = (
        rate_limit.get("group", "") if isinstance(rate_limit, dict) else ""
    )
    esi_request.rate_limit_key = rate_limit_group


def _set_headers(esi_request: EsiRequest, esi_schema: EsiSchema) -> None:
    """Set the runtime headers of an ESI request based on the schema.

    Args:
        esi_request: The ESI request to set the headers for.
        esi_schema: The ESI schema to use for setting the headers.
    """
    schema_compatibility_date = esi_schema.compatibility_date
    # get the request headers, with lower case keys for case-insensitive matching
    request_headers = {k.lower(): v for k, v in esi_request.header_parameters.items()}
    if "accept-language" not in request_headers:
        esi_request.set_runtime_header(name="Accept-Language", value="en")
    if "x-tenant" not in request_headers:
        esi_request.set_runtime_header(name="X-Tenant", value="tranquility")
    if "x-compatibility-date" not in request_headers:
        esi_request.set_runtime_header(
            name="X-Compatibility-Date", value=schema_compatibility_date
        )


def _set_queries(esi_request: EsiRequest, esi_schema: EsiSchema) -> None:
    """Set the runtime query parameters of an ESI request based on the schema.

    Args:
        esi_request: The ESI request to set the queries for.
        esi_schema: The ESI schema to use for setting the queries.
    """
    if esi_request._runtime_query_parameters is None:  # type: ignore
        esi_request._runtime_query_parameters = {}  # type: ignore
    operation = esi_schema.operations.get(esi_request.operation_id)
    if operation is None:
        raise ValueError(
            f"Operation ID '{esi_request.operation_id}' not found in ESI schema."
        )
    if operation.is_paged:
        esi_request.set_runtime_query_parameter(name="page", value=1)
