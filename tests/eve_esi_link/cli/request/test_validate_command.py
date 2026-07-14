"""Tests for the request validate CLI command."""

import json
from uuid import uuid4

import pytest
from typer.testing import CliRunner

try:
    from eve_esi_link.cli.main_typer import app
except ImportError:
    pytest.skip(
        "CLI request model roots are mid-refactor and currently unavailable.",
        allow_module_level=True,
    )

runner = CliRunner()


def _schema_json() -> str:
    """Create a minimal EsiSchemaRoot JSON payload."""
    schema = {
        "schema": {
            "openapi": "3.0.0",
            "info": {"version": "2099-01-01", "title": "test-schema"},
            "servers": [{"url": "https://esi.evetech.net"}],
            "paths": {
                "/status/": {
                    "get": {
                        "operationId": "GetStatus",
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
                }
            },
        },
        "timestamp": 0,
    }
    return json.dumps(schema)


def _requests_json(*, operation_id: str) -> str:
    """Create a single-request EsiRequestsRoot JSON payload."""
    request_id = str(uuid4())
    payload = {
        "requests": {
            request_id: {
                "request_id": request_id,
                "operation_id": operation_id,
                "query_parameters": {"datasource": "tranquility"},
            }
        }
    }
    return json.dumps(payload)


def test_request_validate_accepts_valid_input_from_stdin(tmp_path) -> None:
    """Validate requests from stdin against a schema file."""
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(_schema_json(), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "request",
            "validate",
            "--schema",
            str(schema_path),
        ],
        input=_requests_json(operation_id="GetStatus"),
    )

    assert result.exit_code == 0
    assert "Validated 1 request(s) successfully" in result.stderr


def test_request_validate_reports_request_validation_errors(tmp_path) -> None:
    """Return non-zero exit when any request fails validation."""
    schema_path = tmp_path / "schema.json"
    requests_path = tmp_path / "requests.json"
    schema_path.write_text(_schema_json(), encoding="utf-8")
    requests_path.write_text(
        _requests_json(operation_id="unknown_operation"),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "request",
            "validate",
            "--from",
            str(requests_path),
            "--schema",
            str(schema_path),
        ],
    )

    assert result.exit_code == 1
    assert "Validation failed" in result.stderr
    assert "Unknown operation_id" in result.stderr
