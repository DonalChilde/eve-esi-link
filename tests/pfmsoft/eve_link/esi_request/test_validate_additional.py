"""Additional branch coverage for ESI request validation."""

from uuid import uuid4

import pytest

from pfmsoft.eve_link.esi_request.models import EsiRequest
from pfmsoft.eve_link.esi_request.validate import (
    EsiRequestValidationErrors,
    validate_esi_request,
)
from pfmsoft.eve_link.schema.models import EsiSchema


def _raw_schema() -> dict[str, object]:
    """Build a mutable raw schema for validator branch tests."""
    return {
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
                                    "required": ["title"],
                                    "properties": {
                                        "title": {"type": "string"},
                                        "priority": {"type": "string"},
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


def _make_schema(mutator=None) -> EsiSchema:  # noqa: ANN001
    """Create a schema and optionally mutate the raw payload first."""
    raw = _raw_schema()
    if mutator is not None:
        mutator(raw)
    return EsiSchema.from_raw_schema(raw)


def _auth_fields() -> dict[str, object]:
    """Build authorization field values for authenticated requests."""
    return {"character_id": 123, "credential_id": uuid4()}


def test_validate_rejects_missing_required_path_and_query_parameters() -> None:
    """Report missing required path and query parameters."""
    schema = _make_schema()
    request = EsiRequest(operation_id="get_character_assets", **_auth_fields())

    with pytest.raises(EsiRequestValidationErrors) as exc_info:
        validate_esi_request(request, schema)

    assert any(
        "Missing required path parameter 'character_id'" in message
        for message in exc_info.value.errors
    )
    assert any(
        "Missing required query parameter 'datasource'" in message
        for message in exc_info.value.errors
    )


def test_validate_allows_nullable_query_parameter_value() -> None:
    """Accept null values when the schema marks the parameter nullable."""
    schema = _make_schema(
        lambda raw: raw["paths"]["/status/"]["get"]["parameters"].append({
            "in": "query",
            "name": "nickname",
            "required": False,
            "schema": {"type": "string", "nullable": True},
        })
    )
    request = EsiRequest(
        operation_id="get_status",
        query_parameters={"nickname": None},
    )

    validate_esi_request(request, schema)


def test_validate_rejects_unsupported_parameter_schema_metadata() -> None:
    """Reject parameters whose schema metadata does not declare a usable type."""
    schema = _make_schema(
        lambda raw: raw["paths"]["/status/"]["get"]["parameters"].append({
            "in": "query",
            "name": "broken",
            "required": False,
            "schema": {"description": "missing type"},
        })
    )
    request = EsiRequest(
        operation_id="get_status",
        query_parameters={"broken": "value"},
    )

    with pytest.raises(EsiRequestValidationErrors) as exc_info:
        validate_esi_request(request, schema)

    assert any(
        "query parameter 'broken' has unsupported schema type metadata" in message
        for message in exc_info.value.errors
    )


def test_validate_rejects_non_string_header_and_invalid_auth_types() -> None:
    """Reject header value type mismatches and invalid authorization field types."""
    schema = _make_schema()
    request = EsiRequest(
        operation_id="get_character_assets",
        path_parameters={"character_id": 123},
        query_parameters={"datasource": "tranquility"},
        header_parameters={"Accept-Language": 5},
        character_id=True,
        credential_id="not-a-uuid",
    )

    with pytest.raises(EsiRequestValidationErrors) as exc_info:
        validate_esi_request(request, schema)

    assert any(
        "Header 'accept-language' must be a string" in m for m in exc_info.value.errors
    )
    assert any(
        "Authorization.character_id must be an integer" in m
        for m in exc_info.value.errors
    )
    assert any(
        "Authorization.credential_id must be a UUID" in m for m in exc_info.value.errors
    )


def test_validate_rejects_request_body_when_operation_has_no_body() -> None:
    """Reject json_payload on operations that do not define requestBody."""
    schema = _make_schema()
    request = EsiRequest(
        operation_id="get_status",
        json_payload={"unexpected": True},
    )

    with pytest.raises(EsiRequestValidationErrors) as exc_info:
        validate_esi_request(request, schema)

    assert any(
        "json_body is not allowed" in message for message in exc_info.value.errors
    )


def test_validate_rejects_missing_required_request_body() -> None:
    """Reject absent request bodies when the operation marks them required."""
    schema = _make_schema()
    request = EsiRequest(
        operation_id="post_character_note",
        path_parameters={"character_id": 123},
        **_auth_fields(),
    )

    with pytest.raises(EsiRequestValidationErrors) as exc_info:
        validate_esi_request(request, schema)

    assert any("json_body is required" in message for message in exc_info.value.errors)


@pytest.mark.parametrize(
    ("mutator", "payload", "expected_message"),
    [
        (
            lambda raw: raw["paths"]["/characters/{character_id}/notes/"]["post"][
                "requestBody"
            ].update({"content": "broken"}),
            {"title": "x"},
            "requestBody schema content metadata is invalid",
        ),
        (
            lambda raw: (
                raw["paths"]["/characters/{character_id}/notes/"]["post"][
                    "requestBody"
                ]["content"].update({"text/plain": {"schema": {"type": "string"}}})
                or raw["paths"]["/characters/{character_id}/notes/"]["post"][
                    "requestBody"
                ]["content"].pop("application/json")
            ),
            {"title": "x"},
            "Only application/json request bodies are currently supported",
        ),
        (
            lambda raw: raw["paths"]["/characters/{character_id}/notes/"]["post"][
                "requestBody"
            ]["content"]["application/json"].update({"schema": "broken"}),
            {"title": "x"},
            "requestBody application/json schema metadata is invalid",
        ),
    ],
)
def test_validate_rejects_invalid_request_body_metadata(
    mutator,
    payload: dict[str, object],
    expected_message: str,
) -> None:
    """Reject malformed requestBody metadata before schema validation runs."""
    schema = _make_schema(mutator)
    request = EsiRequest(
        operation_id="post_character_note",
        path_parameters={"character_id": 123},
        json_payload=payload,
        **_auth_fields(),
    )

    with pytest.raises(EsiRequestValidationErrors) as exc_info:
        validate_esi_request(request, schema)

    assert any(expected_message in message for message in exc_info.value.errors)


def test_validate_rejects_unsupported_json_schema_keywords_and_missing_type() -> None:
    """Reject unsupported OpenAPI keywords and schemas without a type."""
    unsupported_schema = _make_schema(
        lambda raw: raw["paths"]["/characters/{character_id}/notes/"]["post"][
            "requestBody"
        ]["content"]["application/json"].update({
            "schema": {"oneOf": [{"type": "string"}, {"type": "integer"}]}
        })
    )
    missing_type_schema = _make_schema(
        lambda raw: raw["paths"]["/characters/{character_id}/notes/"]["post"][
            "requestBody"
        ]["content"]["application/json"].update({
            "schema": {"properties": {"title": {"type": "string"}}}
        })
    )
    request = EsiRequest(
        operation_id="post_character_note",
        path_parameters={"character_id": 123},
        json_payload={"title": "x"},
        **_auth_fields(),
    )

    with pytest.raises(EsiRequestValidationErrors) as unsupported:
        validate_esi_request(request, unsupported_schema)
    with pytest.raises(EsiRequestValidationErrors) as missing_type:
        validate_esi_request(request, missing_type_schema)

    assert any("unsupported keyword(s): oneOf" in m for m in unsupported.value.errors)
    assert any(
        "schema is missing supported 'type' metadata" in m
        for m in missing_type.value.errors
    )


def test_validate_rejects_invalid_object_schema_metadata_and_additional_property_types() -> (
    None
):
    """Reject bad object schema metadata and validate typed additional properties."""
    invalid_properties_schema = _make_schema(
        lambda raw: raw["paths"]["/characters/{character_id}/notes/"]["post"][
            "requestBody"
        ]["content"]["application/json"].update({
            "schema": {
                "type": "object",
                "properties": "broken",
            }
        })
    )
    invalid_required_schema = _make_schema(
        lambda raw: raw["paths"]["/characters/{character_id}/notes/"]["post"][
            "requestBody"
        ]["content"]["application/json"].update({
            "schema": {
                "type": "object",
                "properties": {},
                "required": "broken",
            }
        })
    )
    typed_additional_schema = _make_schema(
        lambda raw: raw["paths"]["/characters/{character_id}/notes/"]["post"][
            "requestBody"
        ]["content"]["application/json"].update({
            "schema": {
                "type": "object",
                "properties": {"title": {"type": "string"}},
                "additionalProperties": {"type": "integer"},
            }
        })
    )

    request = EsiRequest(
        operation_id="post_character_note",
        path_parameters={"character_id": 123},
        json_payload={"title": "x", "extra": "bad"},
        **_auth_fields(),
    )

    with pytest.raises(EsiRequestValidationErrors) as invalid_properties:
        validate_esi_request(request, invalid_properties_schema)
    with pytest.raises(EsiRequestValidationErrors) as invalid_required:
        validate_esi_request(request, invalid_required_schema)
    with pytest.raises(EsiRequestValidationErrors) as typed_additional:
        validate_esi_request(request, typed_additional_schema)

    assert any(
        "object schema has invalid 'properties'" in m
        for m in invalid_properties.value.errors
    )
    assert any(
        "object schema has invalid 'required'" in m
        for m in invalid_required.value.errors
    )
    assert any(
        "json_body.extra expected type 'integer'" in m
        for m in typed_additional.value.errors
    )


def test_validate_rejects_invalid_nested_property_schema_and_array_items() -> None:
    """Reject malformed nested property schemas and arrays with invalid items metadata."""
    invalid_property_schema = _make_schema(
        lambda raw: raw["paths"]["/characters/{character_id}/notes/"]["post"][
            "requestBody"
        ]["content"]["application/json"].update({
            "schema": {
                "type": "object",
                "properties": {"title": "broken"},
            }
        })
    )
    invalid_items_schema = _make_schema(
        lambda raw: raw["paths"]["/characters/{character_id}/notes/"]["post"][
            "requestBody"
        ]["content"]["application/json"].update({
            "schema": {
                "type": "array",
                "items": "broken",
            }
        })
    )

    request = EsiRequest(
        operation_id="post_character_note",
        path_parameters={"character_id": 123},
        json_payload={"title": "x"},
        **_auth_fields(),
    )
    array_request = EsiRequest(
        operation_id="post_character_note",
        path_parameters={"character_id": 123},
        json_payload=["x"],
        **_auth_fields(),
    )

    with pytest.raises(EsiRequestValidationErrors) as invalid_property:
        validate_esi_request(request, invalid_property_schema)
    with pytest.raises(EsiRequestValidationErrors) as invalid_items:
        validate_esi_request(array_request, invalid_items_schema)

    assert any(
        "json_body.title schema metadata is invalid" in m
        for m in invalid_property.value.errors
    )
    assert any(
        "array schema has invalid 'items'" in m for m in invalid_items.value.errors
    )


def test_validate_accepts_optional_request_body_when_omitted() -> None:
    """Allow missing json_payload when requestBody exists but is not required."""
    schema = _make_schema(
        lambda raw: raw["paths"]["/characters/{character_id}/notes/"]["post"][
            "requestBody"
        ].update({"required": False})
    )
    request = EsiRequest(
        operation_id="post_character_note",
        path_parameters={"character_id": 123},
        **_auth_fields(),
    )

    validate_esi_request(request, schema)
