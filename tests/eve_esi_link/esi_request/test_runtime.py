"""Tests for runtime request attribute population."""

from eve_esi_link.esi_link import _make_request_from_esi_request
from eve_esi_link.esi_request.models import EsiRequest
from eve_esi_link.esi_request.runtime import set_runtime_attributes
from eve_esi_link.schema.models import EsiSchema


def _make_schema() -> EsiSchema:
    """Build a minimal schema for runtime attribute tests."""
    raw_schema = {
        "openapi": "3.0.0",
        "info": {"version": "2020-01-01", "title": "test-schema"},
        "servers": [{"url": "https://esi.evetech.net"}],
        "paths": {
            "/status/": {
                "get": {
                    "operationId": "GetStatus",
                    "x-rate-limit": {"group": "status"},
                    "responses": {"200": {"description": "ok"}},
                }
            },
            "/characters/{character_id}/assets/": {
                "get": {
                    "operationId": "GetCharacterAssets",
                    "x-rate-limit": {"group": "character_assets"},
                    "parameters": [
                        {
                            "in": "path",
                            "name": "character_id",
                            "required": True,
                            "schema": {"type": "integer"},
                        },
                        {
                            "in": "query",
                            "name": "page",
                            "required": False,
                            "schema": {"type": "integer"},
                        },
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            },
        },
    }
    return EsiSchema.from_raw_schema(raw_schema)


def test_set_runtime_attributes_sets_default_headers() -> None:
    """Set runtime defaults when no optional headers are supplied."""
    schema = _make_schema()
    request = EsiRequest(operation_id="GetStatus")

    set_runtime_attributes(request, schema)

    assert request.runtime_headers == {
        "accept-language": "en",
        "x-tenant": "tranquility",
        "x-compatibility-date": "2020-01-01",
    }


def test_set_runtime_attributes_respects_user_provided_headers() -> None:
    """Keep user-provided optional headers instead of injecting defaults."""
    schema = _make_schema()
    request = EsiRequest(
        operation_id="GetStatus",
        header_parameters={
            "Accept-Language": "de",
            "X-Tenant": "singularity",
            "X-Compatibility-Date": "2025-05-05",
        },
    )

    set_runtime_attributes(request, schema)

    assert request.runtime_headers == {
        "accept-language": "de",
        "x-tenant": "singularity",
        "x-compatibility-date": "2025-05-05",
    }


def test_make_request_includes_runtime_headers() -> None:
    """Include generated runtime headers in outgoing Request objects."""
    schema = _make_schema()
    request = EsiRequest(operation_id="GetStatus")

    set_runtime_attributes(request, schema)
    outgoing = _make_request_from_esi_request(request)

    assert outgoing.headers == {
        "accept-language": "en",
        "x-tenant": "tranquility",
        "x-compatibility-date": "2020-01-01",
    }


def test_set_runtime_attributes_sets_page_for_paged_operation() -> None:
    """Set runtime page query parameter for paged operations."""
    schema = _make_schema()
    request = EsiRequest(
        operation_id="GetCharacterAssets", path_parameters={"character_id": 123}
    )

    set_runtime_attributes(request, schema)

    assert request.runtime_query_parameters == {"page": 1}
