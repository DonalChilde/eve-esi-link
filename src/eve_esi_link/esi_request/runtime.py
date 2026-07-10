from ..schema.models import EsiSchema
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
    ...


def _set_method(esi_request: EsiRequest, esi_schema: EsiSchema) -> None:
    """Set the HTTP method of an ESI request based on the schema.

    Args:
        esi_request: The ESI request to set the HTTP method for.
        esi_schema: The ESI schema to use for setting the HTTP method.
    """
    ...


def _set_cache_key(esi_request: EsiRequest, esi_schema: EsiSchema) -> None:
    """Set the cache key of an ESI request based on the schema.

    Args:
        esi_request: The ESI request to set the cache key for.
        esi_schema: The ESI schema to use for setting the cache key.
    """
    ...


def _set_rate_limit(esi_request: EsiRequest, esi_schema: EsiSchema) -> None:
    """Set the rate limit of an ESI request based on the schema.

    Args:
        esi_request: The ESI request to set the rate limit for.
        esi_schema: The ESI schema to use for setting the rate limit.
    """
    ...


def _set_headers(esi_request: EsiRequest, esi_schema: EsiSchema) -> None:
    """Set the headers of an ESI request based on the schema.

    Args:
        esi_request: The ESI request to set the headers for.
        esi_schema: The ESI schema to use for setting the headers.
    """
    ...


def _set_queries(esi_request: EsiRequest, esi_schema: EsiSchema) -> None:
    """Set the queries of an ESI request based on the schema.

    Args:
        esi_request: The ESI request to set the queries for.
        esi_schema: The ESI schema to use for setting the queries.
    """
    ...
