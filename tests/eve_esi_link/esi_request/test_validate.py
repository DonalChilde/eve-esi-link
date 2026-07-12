"""Tests for ESI request validation."""

from uuid import uuid4

import pytest

from eve_esi_link.esi_request.models import EsiAuthorization, EsiRequest
from eve_esi_link.esi_request.validate import (
    EsiRequestValidationErrors,
    validate_esi_request,
)
from eve_esi_link.schema.models import EsiSchema


def _make_schema() -> EsiSchema:
    """Build a minimal schema for request validation tests."""
    raw_schema = {
        "openapi": "3.0.0",
        "info": {"version": "2099-01-01", "title": "test-schema"},
        "servers": [{"url": "https://esi.evetech.net"}],
        "paths": {
            "/characters/{character_id}/assets/": {
                "get": {
                    "operationId": "get_character_assets",
                    "security": [{"evesso": ["esi-assets.read_assets.v1"]}],
                    "parameters": [
                        {
                            "in": "path",
                            "name": "character_id",
                            "required": True,
                            "schema": {"type": "integer"},
                        },
                        {
                            "in": "query",
                            "name": "datasource",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "enum": ["tranquility", "singularity"],
                            },
                        },
                        {
                            "in": "header",
                            "name": "Accept-Language",
                            "required": False,
                            "schema": {"type": "string"},
                        },
                        {
                            "in": "header",
                            "name": "X-Compatibility-Date",
                            "required": False,
                            "schema": {"type": "string"},
                        },
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            },
            "/status/": {
                "get": {
                    "operationId": "get_status",
                    "parameters": [
                        {
                            "in": "query",
                            "name": "datasource",
                            "required": False,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            },
            "/characters/{character_id}/notes/": {
                "post": {
                    "operationId": "post_character_note",
                    "security": [{"evesso": ["esi-characters.read_notes.v1"]}],
                    "parameters": [
                        {
                            "in": "path",
                            "name": "character_id",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title", "priority"],
                                    "properties": {
                                        "title": {"type": "string"},
                                        "priority": {
                                            "type": "string",
                                            "enum": ["low", "high"],
                                        },
                                        "tags": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                    "additionalProperties": False,
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            },
        },
    }
    return EsiSchema.from_raw_schema(raw_schema)


def _auth() -> EsiAuthorization:
    """Create authorization without an access token set."""
    return EsiAuthorization(character_id=123, credential_id=uuid4())


def test_validate_allows_valid_authenticated_request_without_token_by_default() -> None:
    """Accept an auth-required request when token requirement is disabled."""
    schema = _make_schema()
    request = EsiRequest(
        operation_id="get_character_assets",
        path_parameters={"character_id": 123},
        query_parameters={"datasource": "tranquility"},
        header_parameters={"Accept-Language": "en"},
        authorization=_auth(),
    )

    validate_esi_request(request, schema)


def test_validate_rejects_unknown_operation_id() -> None:
    """Reject operation IDs that are not present in the schema."""
    schema = _make_schema()
    request = EsiRequest(operation_id="missing_operation")

    with pytest.raises(EsiRequestValidationErrors) as exc_info:
        validate_esi_request(request, schema)

    assert any("Unknown operation_id" in message for message in exc_info.value.errors)


def test_validate_rejects_page_query_parameter() -> None:
    """Reject user-supplied page parameter in query arguments."""
    schema = _make_schema()
    request = EsiRequest(
        operation_id="get_character_assets",
        path_parameters={"character_id": 123},
        query_parameters={"datasource": "tranquility", "page": 2},
        authorization=_auth(),
    )

    with pytest.raises(EsiRequestValidationErrors) as exc_info:
        validate_esi_request(request, schema)

    assert any("'page' must not be set" in message for message in exc_info.value.errors)


def test_validate_rejects_runtime_managed_headers_and_unknown_headers() -> None:
    """Reject forbidden runtime headers and headers not declared by operation."""
    schema = _make_schema()
    request = EsiRequest(
        operation_id="get_character_assets",
        path_parameters={"character_id": 123},
        query_parameters={"datasource": "tranquility"},
        header_parameters={
            "If-None-Match": "abc",
            "X-Tenant": "tenant-a",
            "Accept-Language": "zz",
        },
        authorization=_auth(),
    )

    with pytest.raises(EsiRequestValidationErrors) as exc_info:
        validate_esi_request(request, schema)

    assert any("runtime-managed" in message for message in exc_info.value.errors)
    assert any("not allowed" in message for message in exc_info.value.errors)
    assert any(
        "supported language codes" in message for message in exc_info.value.errors
    )


def test_validate_rejects_authorization_on_public_operation() -> None:
    """Reject authorization data for non-authenticated operations."""
    schema = _make_schema()
    request = EsiRequest(
        operation_id="get_status",
        query_parameters={"datasource": "tranquility"},
        authorization=_auth(),
    )

    with pytest.raises(EsiRequestValidationErrors) as exc_info:
        validate_esi_request(request, schema)

    assert any("must be None" in message for message in exc_info.value.errors)


def test_validate_aggregates_multiple_errors() -> None:
    """Return multiple validation messages for a single invalid request."""
    schema = _make_schema()
    request = EsiRequest(
        operation_id="post_character_note",
        path_parameters={"character_id": "bad"},
        query_parameters={"page": 1, "unknown": "value"},
        json_payload={"priority": "invalid", "extra": "x"},
        authorization=_auth(),
    )

    with pytest.raises(EsiRequestValidationErrors) as exc_info:
        validate_esi_request(request, schema)

    assert len(exc_info.value.errors) >= 4
    assert any(
        "expected type 'integer'" in message for message in exc_info.value.errors
    )
    assert any(
        "Unknown query parameter 'unknown'" in message
        for message in exc_info.value.errors
    )
    assert any("'page' must not be set" in message for message in exc_info.value.errors)
    assert any(
        "json_body.title is required" in message for message in exc_info.value.errors
    )
