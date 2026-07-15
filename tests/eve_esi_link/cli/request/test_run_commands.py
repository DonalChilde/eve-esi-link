"""Tests for the request run CLI commands."""

import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from api_request import Response
from api_request.request.models import FailedResponse, Request, ResponseMetadata, Source
from typer.testing import CliRunner

from eve_esi_link.cli.request import run as run_command
from eve_esi_link.cli.request import run_group as run_group_command
from eve_esi_link.esi_request.models import (
    EsiResponse,
    EsiResponseGroup,
    FailedEsiResponse,
    RuntimeEsiRequest,
)
from eve_esi_link.esi_request.validate import EsiRequestValidationErrors
from eve_esi_link.settings import EsiLinkSettings

runner = CliRunner()


class _FakeEsiLink:
    """Async context manager stub for CLI execution tests."""

    def __init__(
        self, *, result: EsiResponseGroup | None = None, error: Exception | None = None
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[object, object]] = []

    async def __aenter__(self) -> _FakeEsiLink:
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Exit the async context manager."""
        return None

    async def make_requests(self, *, esi_requests, schema):  # noqa: ANN001
        """Return the prepared result or raise the prepared error."""
        self.calls.append((esi_requests, schema))
        if self.error is not None:
            raise self.error
        return self.result


@pytest.fixture
def settings(tmp_path: Path) -> EsiLinkSettings:
    """Build EsiLink settings rooted in the pytest temp directory."""
    application_directory = tmp_path / "app"
    return EsiLinkSettings(
        application_directory=application_directory,
        logging_directory=application_directory / "logs",
        schema_cache_directory=application_directory / "schema-cache",
        auth_manager_db_file=application_directory / "auth.sqlite",
        api_request_cache_file=application_directory / "api.sqlite",
    )


def _single_request_json(*, request_id: UUID, operation_id: str = "GetStatus") -> str:
    """Build JSON for a single EsiRequest payload."""
    return json.dumps({
        "request_id": str(request_id),
        "operation_id": operation_id,
        "query_parameters": {"datasource": "tranquility"},
    })


def _request_group_json(*, request_id: UUID, operation_id: str = "GetStatus") -> str:
    """Build JSON for an EsiRequestGroup payload."""
    return json.dumps({
        "requests": {
            str(request_id): {
                "request_id": str(request_id),
                "operation_id": operation_id,
                "query_parameters": {"datasource": "tranquility"},
            }
        }
    })


def _request_model(*, request_id: UUID) -> Request:
    """Build a minimal api_request Request fixture."""
    return Request(
        request_key=request_id,
        url="https://esi.evetech.net/status/",
        method="GET",
    )


def _runtime_request(*, request_id: UUID) -> RuntimeEsiRequest:
    """Build a runtime request fixture with a redactable token."""
    return RuntimeEsiRequest(
        request_key=request_id,
        url="https://esi.evetech.net/status/",
        method="GET",
        cache_key=None,
        rate_limit_key="status",
        headers={"accept-language": "en"},
        access_token="secret-token",
    )


def _successful_response_group(*, request_id: UUID) -> EsiResponseGroup:
    """Build a response group with one successful response."""
    runtime_request = _runtime_request(request_id=request_id)
    request = _request_model(request_id=request_id)
    response = Response(
        metadata=ResponseMetadata(
            status_code=200,
            reason_phrase="OK",
            url=request.url,
            elapsed=1,
            bytes_downloaded=10,
        ),
        json={"status": "ok"},
        request=request,
        source=Source.NETWORK,
    )
    return EsiResponseGroup(
        successful_responses={
            request_id: EsiResponse(
                esi_runtime_request=runtime_request,
                response=response,
            )
        }
    )


def _failed_response_group(*, request_id: UUID) -> EsiResponseGroup:
    """Build a response group with one failed response."""
    runtime_request = _runtime_request(request_id=request_id)
    request = _request_model(request_id=request_id)
    failed_response = FailedResponse(
        request=request,
        error_messages=["request failed"],
    )
    return EsiResponseGroup(
        failed_responses={
            request_id: FailedEsiResponse(
                esi_runtime_request=runtime_request,
                failed_response=failed_response,
            )
        }
    )


def test_request_run_prints_plain_success_json(
    monkeypatch: pytest.MonkeyPatch,
    settings: EsiLinkSettings,
    tmp_path: Path,
) -> None:
    """Print the successful response body when run writes to stdout."""
    request_id = uuid4()
    schema_path = tmp_path / "schema.json"
    schema_path.write_text("{}", encoding="utf-8")
    fake_link = _FakeEsiLink(result=_successful_response_group(request_id=request_id))
    schema = object()

    monkeypatch.setattr(
        run_command, "get_eve_link_settings_from_context", lambda _ctx: settings
    )
    monkeypatch.setattr(
        run_command,
        "get_stdin",
        lambda: _single_request_json(request_id=request_id),
    )
    monkeypatch.setattr(run_command, "load_esi_schema_from_file", lambda _path: schema)
    monkeypatch.setattr(run_command, "esi_link_factory", lambda _settings: fake_link)

    result = runner.invoke(
        run_command.app,
        ["--schema", str(schema_path), "--plain"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"status": "ok"}
    assert fake_link.calls[0][1] is schema
    assert fake_link.calls[0][0].requests[request_id].operation_id == "GetStatus"


def test_request_run_saves_debug_failed_response_before_exiting(
    monkeypatch: pytest.MonkeyPatch,
    settings: EsiLinkSettings,
    tmp_path: Path,
) -> None:
    """Write the serialized failed response in debug mode before fail-check exit."""
    request_id = uuid4()
    schema_path = tmp_path / "schema.json"
    schema_path.write_text("{}", encoding="utf-8")
    output_path = tmp_path / "response.json"
    fake_link = _FakeEsiLink(result=_failed_response_group(request_id=request_id))
    saved: dict[str, object] = {}

    monkeypatch.setattr(
        run_command, "get_eve_link_settings_from_context", lambda _ctx: settings
    )
    monkeypatch.setattr(
        run_command,
        "get_stdin",
        lambda: _single_request_json(request_id=request_id),
    )
    monkeypatch.setattr(
        run_command, "load_esi_schema_from_file", lambda _path: object()
    )
    monkeypatch.setattr(run_command, "esi_link_factory", lambda _settings: fake_link)

    def fake_save_text_file(**kwargs):  # noqa: ANN003
        saved.update(kwargs)
        return output_path

    monkeypatch.setattr(run_command, "save_text_file", fake_save_text_file)

    result = runner.invoke(
        run_command.app,
        ["--schema", str(schema_path), "--debug", "--to", str(output_path)],
    )

    assert result.exit_code == 1
    assert "Error: Request failed" in result.stderr
    assert saved["directory"] == output_path.parent
    assert saved["filename"] == output_path.name
    assert "failed_response" in saved["text"]
    assert "REDACTED" in saved["text"]


def test_request_run_reports_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
    settings: EsiLinkSettings,
    tmp_path: Path,
) -> None:
    """Surface aggregated request validation errors from the async runner."""
    request_id = uuid4()
    schema_path = tmp_path / "schema.json"
    schema_path.write_text("{}", encoding="utf-8")
    fake_link = _FakeEsiLink(
        error=EsiRequestValidationErrors([
            "operation_id=GetStatus: Unknown operation_id for provided schema."
        ])
    )

    monkeypatch.setattr(
        run_command, "get_eve_link_settings_from_context", lambda _ctx: settings
    )
    monkeypatch.setattr(
        run_command,
        "get_stdin",
        lambda: _single_request_json(request_id=request_id),
    )
    monkeypatch.setattr(
        run_command, "load_esi_schema_from_file", lambda _path: object()
    )
    monkeypatch.setattr(run_command, "esi_link_factory", lambda _settings: fake_link)

    result = runner.invoke(
        run_command.app,
        ["--schema", str(schema_path)],
    )

    assert result.exit_code == 1
    assert "Requests failed due to validation errors" in result.stderr
    assert "Unknown operation_id for provided schema" in result.stderr


def test_run_group_prints_plain_serialized_response_group(
    monkeypatch: pytest.MonkeyPatch,
    settings: EsiLinkSettings,
    tmp_path: Path,
) -> None:
    """Print the serialized response group when run-group writes to stdout."""
    request_id = uuid4()
    schema_path = tmp_path / "schema.json"
    schema_path.write_text("{}", encoding="utf-8")
    fake_link = _FakeEsiLink(result=_successful_response_group(request_id=request_id))

    monkeypatch.setattr(
        run_group_command, "get_eve_link_settings_from_context", lambda _ctx: settings
    )
    monkeypatch.setattr(
        run_group_command,
        "get_stdin",
        lambda: _request_group_json(request_id=request_id),
    )
    monkeypatch.setattr(
        run_group_command, "load_esi_schema_from_file", lambda _path: object()
    )
    monkeypatch.setattr(
        run_group_command, "esi_link_factory", lambda _settings: fake_link
    )

    result = runner.invoke(
        run_group_command.app,
        ["--schema", str(schema_path), "--plain"],
    )

    assert result.exit_code == 0
    assert "successful_responses" in result.stdout
    assert "REDACTED" in result.stdout


def test_run_group_reports_failed_requests_after_writing_output(
    monkeypatch: pytest.MonkeyPatch,
    settings: EsiLinkSettings,
    tmp_path: Path,
) -> None:
    """Persist the response group, then exit non-zero with a readable failed-count message."""
    request_id = uuid4()
    schema_path = tmp_path / "schema.json"
    schema_path.write_text("{}", encoding="utf-8")
    output_path = tmp_path / "responses.json"
    fake_link = _FakeEsiLink(result=_failed_response_group(request_id=request_id))
    saved: dict[str, object] = {}

    monkeypatch.setattr(
        run_group_command, "get_eve_link_settings_from_context", lambda _ctx: settings
    )
    monkeypatch.setattr(
        run_group_command,
        "get_stdin",
        lambda: _request_group_json(request_id=request_id),
    )
    monkeypatch.setattr(
        run_group_command, "load_esi_schema_from_file", lambda _path: object()
    )
    monkeypatch.setattr(
        run_group_command, "esi_link_factory", lambda _settings: fake_link
    )

    def fake_save_text_file(**kwargs):  # noqa: ANN003
        saved.update(kwargs)
        return output_path

    monkeypatch.setattr(run_group_command, "save_text_file", fake_save_text_file)

    result = runner.invoke(
        run_group_command.app,
        ["--schema", str(schema_path), "--to", str(output_path)],
    )

    assert result.exit_code == 1
    assert saved["directory"] == output_path.parent
    assert saved["filename"] == output_path.name
    assert "There were 1 failed requests." in result.stderr
    assert "request failed" in result.stderr
