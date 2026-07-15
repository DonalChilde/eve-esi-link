"""Tests for the request validate CLI command."""

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from eve_esi_link.cli.main_typer import app
from eve_esi_link.cli.request import validate as validate_command

runner = CliRunner()


class _FakeEsiLink:
    """Small validator stub for request validate command tests."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[object, object]] = []

    def validate_request(self, request, schema) -> None:  # noqa: ANN001
        """Record the validation call and optionally raise an error."""
        self.calls.append((request, schema))
        if self.error is not None:
            raise self.error


class _FakeSchemaManager:
    """Schema cache stub for validating cached schema selection branches."""

    def __init__(self, *, entries: list[SimpleNamespace], loaded: dict[str, object]) -> None:
        self._entries = entries
        self._loaded = loaded
        self.load_calls: list[str] = []

    def list_entries(self) -> list[SimpleNamespace]:
        """Return configured cache entries."""
        return self._entries

    def load(self, *, compatibility_date: str) -> object:
        """Return a configured schema and record the requested date."""
        self.load_calls.append(compatibility_date)
        return self._loaded[compatibility_date]


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


def test_request_validate_rejects_schema_and_date_together(tmp_path: Path) -> None:
    """Return a usage error when both schema selection options are supplied."""
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(_schema_json(), encoding="utf-8")

    result = runner.invoke(
        validate_command.app,
        ["--schema", str(schema_path), "--date", "2026-06-09"],
        input=_requests_json(operation_id="GetStatus"),
    )

    assert result.exit_code == 1
    assert "mutually exclusive" in result.stderr


def test_request_validate_uses_most_recent_cached_schema_quietly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Use the newest cached schema when no date is provided and suppress output with --quiet."""
    fake_link = _FakeEsiLink()
    schema = object()
    manager = _FakeSchemaManager(
        entries=[
            SimpleNamespace(compatibility_date="2026-06-09"),
            SimpleNamespace(compatibility_date="2026-06-10"),
        ],
        loaded={"2026-06-10": schema},
    )
    settings = SimpleNamespace(schema_cache_directory=tmp_path / "schema-cache")

    monkeypatch.setattr(
        validate_command,
        "get_eve_link_settings_from_context",
        lambda _ctx: settings,
    )
    monkeypatch.setattr(
        validate_command,
        "get_stdin",
        lambda: _requests_json(operation_id="GetStatus"),
    )
    monkeypatch.setattr(validate_command, "SchemaCacheManager", lambda **_kwargs: manager)
    monkeypatch.setattr(validate_command, "esi_link_factory", lambda _settings: fake_link)

    result = runner.invoke(validate_command.app, ["--quiet"])

    assert result.exit_code == 0
    assert result.stderr == ""
    assert manager.load_calls == ["2026-06-10"]
    assert len(fake_link.calls) == 1
    assert fake_link.calls[0][1] is schema


def test_request_validate_reports_parse_errors_from_stdin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fail early when stdin does not contain valid EsiRequestGroup JSON."""
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(_schema_json(), encoding="utf-8")
    monkeypatch.setattr(
        validate_command,
        "get_eve_link_settings_from_context",
        lambda _ctx: SimpleNamespace(schema_cache_directory=tmp_path / "schema-cache"),
    )
    monkeypatch.setattr(
        validate_command,
        "esi_link_factory",
        lambda _settings: _FakeEsiLink(),
    )

    result = runner.invoke(
        validate_command.app,
        ["--schema", str(schema_path)],
        input="{not json}",
    )

    assert result.exit_code == 1
    assert "Failed to parse ESI requests JSON" in result.stderr


def test_request_validate_reports_empty_cache_without_generic_followup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report an empty schema cache once, without a second generic cache-load error."""
    fake_link = _FakeEsiLink()
    manager = _FakeSchemaManager(entries=[], loaded={})
    settings = SimpleNamespace(schema_cache_directory=tmp_path / "schema-cache")

    monkeypatch.setattr(
        validate_command,
        "get_eve_link_settings_from_context",
        lambda _ctx: settings,
    )
    monkeypatch.setattr(
        validate_command,
        "get_stdin",
        lambda: _requests_json(operation_id="GetStatus"),
    )
    monkeypatch.setattr(validate_command, "SchemaCacheManager", lambda **_kwargs: manager)
    monkeypatch.setattr(validate_command, "esi_link_factory", lambda _settings: fake_link)

    result = runner.invoke(validate_command.app, [])

    assert result.exit_code == 1
    assert "No cached schemas found" in result.stderr
    assert "Failed to load cached schema" not in result.stderr


def test_request_validate_reports_unexpected_validator_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Aggregate unexpected exceptions as per-request validation failures."""
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(_schema_json(), encoding="utf-8")
    settings = SimpleNamespace(schema_cache_directory=tmp_path / "schema-cache")
    fake_link = _FakeEsiLink(error=RuntimeError("boom"))

    monkeypatch.setattr(
        validate_command,
        "get_eve_link_settings_from_context",
        lambda _ctx: settings,
    )
    monkeypatch.setattr(
        validate_command,
        "get_stdin",
        lambda: _requests_json(operation_id="GetStatus"),
    )
    monkeypatch.setattr(validate_command, "esi_link_factory", lambda _settings: fake_link)

    result = runner.invoke(validate_command.app, ["--schema", str(schema_path)])

    assert result.exit_code == 1
    assert "Validation failed" in result.stderr
    assert "Unexpected validation error -" in result.stderr
    assert "boom" in result.stderr
