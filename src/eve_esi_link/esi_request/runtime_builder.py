"""Build deterministic RuntimeEsiRequest objects from validated EsiRequest inputs."""

from uuid import UUID, uuid5

from eve_esi_link.esi_request.models import EsiRequest, RuntimeEsiRequest
from eve_esi_link.helpers.canonicalize_url import combine_and_canonicalize_url
from eve_esi_link.schema.models import EsiSchema, SchemaOperation
from eve_esi_link.settings import APP_NAMESPACE


def build_runtime_esi_request(
    esi_request: EsiRequest, esi_schema: EsiSchema
) -> RuntimeEsiRequest:
    """Build a runtime ESI request from an ESI request and schema.

    Args:
        esi_request (EsiRequest): The ESI request object.
        esi_schema (EsiSchema): The ESI schema object.

    Returns:
        RuntimeEsiRequest: The constructed runtime ESI request.
    """
    operation = _check_operation(esi_schema, esi_request.operation_id)
    url = _url(esi_request, esi_schema)
    method = _method(esi_request, esi_schema)
    rate_limit_key = _rate_limit_key(esi_request, esi_schema)
    headers = _headers(esi_request, esi_schema)
    query_parameters = _query_parameters(esi_request, esi_schema)
    json_payload = esi_request.json_payload
    if esi_request.has_authorization:
        authorization_slug = esi_request.authorization_slug
    else:
        authorization_slug = None
    if operation.is_cached:
        cache_key = _cache_key(
            method=method,
            url=url,
            query_parameters=query_parameters,
            authorization_slug=authorization_slug,
            compatibility_date=headers["x-compatibility-date"],
            accept_language=headers["accept-language"],
        )
    else:
        cache_key = None

    runtime_request = RuntimeEsiRequest(
        request_key=uuid5(APP_NAMESPACE, str(esi_request.request_id)),
        url=url,
        method=method,
        cache_key=cache_key,
        rate_limit_key=rate_limit_key,
        headers=headers,
        query_parameters=query_parameters,
        json_payload=json_payload,
        access_token=None,
    )
    return runtime_request


def _check_operation(esi_schema: EsiSchema, operation_id: str) -> SchemaOperation:
    operation = esi_schema.operations.get(operation_id)
    if operation is None:
        raise ValueError(f"Operation ID '{operation_id}' not found in ESI schema.")
    return operation


def _url(esi_request: EsiRequest, esi_schema: EsiSchema) -> str:
    """Build the URL for the runtime ESI request based on the ESI request and schema.

    This function takes the ESI request and the corresponding ESI schema,
    extracts the URL template from the schema, and formats it with the
    path parameters from the request to produce the final URL.

    Args:
        esi_request (EsiRequest): The ESI request object.
        esi_schema (EsiSchema): The ESI schema object.

    Returns:
        str: The URL for the runtime ESI request.
    """
    url_template = esi_schema.operation_url(esi_request.operation_id)
    path_parameters = esi_request.path_parameters
    url = url_template.format(**path_parameters)
    return url


def _method(esi_request: EsiRequest, esi_schema: EsiSchema) -> str:
    operation = _check_operation(esi_schema, esi_request.operation_id)
    return operation.method


def _rate_limit_key(esi_request: EsiRequest, esi_schema: EsiSchema) -> str:
    operation = _check_operation(esi_schema, esi_request.operation_id)
    rate_limit = operation.rate_limit
    rate_limit_group = (
        rate_limit.get("group", "") if isinstance(rate_limit, dict) else ""
    )
    return rate_limit_group


def _headers(esi_request: EsiRequest, esi_schema: EsiSchema) -> dict[str, str]:
    """Ensure runtime headers are properly set for the request.

    This includes setting default headers such as 'Accept-Language',
    'X-Tenant', and 'X-Compatibility-Date' if they are not already present
    in the request headers.

    Args:
        esi_request (EsiRequest): The ESI request object.
        esi_schema (EsiSchema): The ESI schema object.

    Returns:
        dict[str, str]: The runtime headers for the request.
    """
    runtime_headers: dict[str, str] = {}
    schema_compatibility_date = esi_schema.compatibility_date
    # get the request headers, with lower case keys for case-insensitive matching
    request_headers = {k.lower(): v for k, v in esi_request.header_parameters.items()}
    runtime_headers.update(request_headers)
    if "accept-language" not in runtime_headers:
        runtime_headers["accept-language"] = "en"
    if "x-tenant" not in runtime_headers:
        runtime_headers["x-tenant"] = "tranquility"
    if "x-compatibility-date" not in runtime_headers:
        runtime_headers["x-compatibility-date"] = schema_compatibility_date
    return runtime_headers


def _query_parameters(
    esi_request: EsiRequest, esi_schema: EsiSchema
) -> dict[str, int | float | str]:
    """Build the query parameters for the runtime ESI request based on the ESI request and schema.

    Args:
        esi_request (EsiRequest): The ESI request object.
        esi_schema (EsiSchema): The ESI schema object.

    Returns:
        dict[str, int | float | str]: The query parameters for the runtime ESI request.
    """
    runtime_query_parameters: dict[str, int | float | str] = {}
    runtime_query_parameters.update(esi_request.query_parameters)
    operation = _check_operation(esi_schema, esi_request.operation_id)
    if operation.is_paged:
        runtime_query_parameters["page"] = esi_request.query_parameters.get("page", 1)
    return runtime_query_parameters


def _cache_key(
    method: str,
    url: str,
    query_parameters: dict[str, int | float | str],
    authorization_slug: UUID | None,
    compatibility_date: str,
    accept_language: str,
) -> UUID:
    canonical_url = combine_and_canonicalize_url(url, query_parameters or {})
    cache_key = uuid5(
        APP_NAMESPACE,
        f"{method}:{canonical_url}:{str(authorization_slug) if authorization_slug is not None else ''}:{compatibility_date}:{accept_language}",
    )
    return cache_key
