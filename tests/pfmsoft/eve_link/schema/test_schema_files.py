"""Tests for schema file loaders and shape detection helpers."""

import json
from pathlib import Path

import pytest
from whenever import Instant

from pfmsoft.eve_link.schema.helpers.schema_check import (
    is_esi_schema_td,
    is_open_api_schema,
    is_raw_schema,
    is_timestamped_schema,
)
from pfmsoft.eve_link.schema.helpers.schema_files import (
    default_file_name_for_cached_schema,
    load_esi_schema,
    load_esi_schema_from_file,
)


def _raw_openapi_schema() -> dict[str, object]:
    """Build a minimal raw OpenAPI schema with an internal ref."""
    return {
        "openapi": "3.0.0",
        "info": {"version": "2026-06-09", "title": "test-schema"},
        "servers": [{"url": "https://esi.evetech.net"}],
        "paths": {
            "/status/": {
                "get": {
                    "operationId": "GetStatus",
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Status"}
                                }
                            },
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "Status": {
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                }
            }
        },
    }


def _dereferenced_openapi_schema() -> dict[str, object]:
    """Build a minimal dereferenced OpenAPI schema."""
    schema = _raw_openapi_schema()
    schema["paths"]["/status/"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] = {"type": "object", "properties": {"status": {"type": "string"}}}
    return schema


def test_schema_shape_helpers_identify_supported_payloads() -> None:
    """Recognize raw OpenAPI, EsiSchemaTD, and timestamped-schema shapes."""
    raw = _raw_openapi_schema()

    assert is_open_api_schema(raw) is True
    assert is_raw_schema(raw) is True
    assert is_esi_schema_td({"dereferenced_schema": {}, "timestamp": None}) is True
    assert is_timestamped_schema({"schema": {}, "timestamp": 1}) is True


def test_schema_shape_helpers_reject_non_matching_shapes() -> None:
    """Return false when required top-level keys are missing."""
    incomplete = {"openapi": "3.0.0", "info": {}, "paths": {}}

    assert is_open_api_schema(incomplete) is False
    assert is_raw_schema(_dereferenced_openapi_schema()) is False
    assert is_esi_schema_td({"schema": {}, "timestamp": 1}) is False
    assert is_timestamped_schema({"dereferenced_schema": {}, "timestamp": 1}) is False


def test_load_esi_schema_dereferences_raw_openapi_and_applies_timestamp() -> None:
    """Load raw OpenAPI payloads through the dereferencing path."""
    instant = Instant("2026-07-15T12:00:00Z")

    schema = load_esi_schema(_raw_openapi_schema(), timestamp=instant)

    assert schema.timestamp == instant.timestamp_nanos()
    assert schema.operations["GetStatus"].responses_200 == {
        "type": "object",
        "properties": {"status": {"type": "string"}},
    }


def test_load_esi_schema_accepts_dereferenced_openapi_without_timestamp() -> None:
    """Treat already-dereferenced OpenAPI payloads as EsiSchemaTD content."""
    schema = load_esi_schema(_dereferenced_openapi_schema())

    assert schema.timestamp is None
    assert schema.version == "2026-06-09"
    assert schema.operations["GetStatus"].responses_200 == {
        "type": "object",
        "properties": {"status": {"type": "string"}},
    }


def test_load_esi_schema_accepts_esi_schema_td_envelope() -> None:
    """Load a pre-dereferenced EsiSchemaTD envelope directly."""
    schema = load_esi_schema({
        "dereferenced_schema": _dereferenced_openapi_schema(),
        "timestamp": 123,
    })

    assert schema.timestamp == 123
    assert schema.compatibility_date == "2026-06-09"


def test_load_esi_schema_accepts_timestamped_schema_envelope() -> None:
    """Load a timestamped raw schema envelope through the raw-schema path."""
    schema = load_esi_schema({
        "schema": _raw_openapi_schema(),
        "timestamp": 456,
    })

    assert schema.timestamp == 456
    assert schema.operations["GetStatus"].path == "/status/"


def test_load_esi_schema_from_file_loads_json_file(tmp_path: Path) -> None:
    """Read the JSON payload from disk before delegating to the loader."""
    file_path = tmp_path / "schema.json"
    file_path.write_text(
        json.dumps({"schema": _raw_openapi_schema(), "timestamp": 789}),
        encoding="utf-8",
    )

    schema = load_esi_schema_from_file(file_path)

    assert schema.timestamp == 789
    assert schema.base_url == "https://esi.evetech.net"


def test_load_esi_schema_rejects_unknown_top_level_shape() -> None:
    """Raise a descriptive error for unsupported schema payloads."""
    with pytest.raises(ValueError, match="top-level keys were invalid"):
        load_esi_schema({"invalid": True})


def test_default_file_name_for_cached_schema_uses_date_and_timestamp() -> None:
    """Generate cache filenames from compatibility date and timestamp."""
    schema = load_esi_schema({"schema": _raw_openapi_schema(), "timestamp": 123456})

    assert (
        default_file_name_for_cached_schema(schema)
        == "schema_2026-06-09_123456_esi_schema.json"
    )
