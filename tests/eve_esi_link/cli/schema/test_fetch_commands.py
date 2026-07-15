"""Tests for schema fetch-style CLI commands."""

import json
from contextlib import nullcontext
from pathlib import Path

import pytest
from typer.testing import CliRunner

from eve_esi_link.cli.schema import fetch as fetch_command
from eve_esi_link.cli.schema import fetch_changelog as fetch_changelog_command
from eve_esi_link.cli.schema import fetch_dates as fetch_dates_command
from eve_esi_link.schema.helpers.fetch import (
    TimestampedCompatibilityDates,
    TimestampedSchema,
)
from eve_esi_link.schema.helpers.io_format import SchemaIOFormat

runner = CliRunner()


def _timestamped_schema(*, date: str = "2026-06-09") -> TimestampedSchema:
    """Build a minimal fetched schema fixture."""
    return TimestampedSchema(
        schema={
            "openapi": "3.0.0",
            "info": {"version": date, "title": "test-schema"},
            "servers": [{"url": "https://esi.evetech.net"}],
            "paths": {},
            "components": {},
        },
        timestamp=123,
    )


def test_fetch_schema_plain_unaltered_stdout_emits_raw_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Print raw schema JSON in plain stdout mode without double-encoding it."""
    schema_data = _timestamped_schema()

    monkeypatch.setattr(fetch_command, "client_manager", lambda: nullcontext(object()))
    monkeypatch.setattr(
        fetch_command,
        "fetch_schema",
        lambda _session, *, schema_as_of: schema_data,
    )

    result = runner.invoke(
        fetch_command.app,
        ["--plain", "--format", SchemaIOFormat.UNALTERED.value],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout) == schema_data.schema


def test_fetch_schema_saves_directory_output_with_default_filename(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Choose the format-specific default filename when --to points at a directory."""
    schema_data = _timestamped_schema(date="2026-06-10")
    output_dir = tmp_path / "schemas"
    saved: dict[str, object] = {}

    monkeypatch.setattr(fetch_command, "client_manager", lambda: nullcontext(object()))
    monkeypatch.setattr(
        fetch_command,
        "fetch_schema",
        lambda _session, *, schema_as_of: schema_data,
    )

    def fake_save_text_file(**kwargs):  # noqa: ANN003
        saved.update(kwargs)
        return output_dir / kwargs["filename"]

    monkeypatch.setattr(fetch_command, "save_text_file", fake_save_text_file)

    result = runner.invoke(
        fetch_command.app,
        ["--to", str(output_dir), "--format", SchemaIOFormat.TIMESTAMPED.value],
    )

    assert result.exit_code == 0
    assert saved["directory"] == output_dir
    assert saved["filename"] == "schema_2026-06-10_timestamped.json"
    assert "Schema saved to" in result.stderr


def test_fetch_compatibility_dates_saves_default_filename(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Use the default compatibility date filename when --to points at a directory."""
    output_dir = tmp_path / "dates"
    saved: dict[str, object] = {}

    monkeypatch.setattr(
        fetch_dates_command, "client_manager", lambda: nullcontext(object())
    )
    monkeypatch.setattr(
        fetch_dates_command,
        "fetch_compatibility_dates",
        lambda _session: TimestampedCompatibilityDates(
            compatibility_dates=("2026-06-09", "2026-06-10"),
            timestamp=123,
        ),
    )

    def fake_save_text_file(**kwargs):  # noqa: ANN003
        saved.update(kwargs)
        return output_dir / kwargs["filename"]

    monkeypatch.setattr(fetch_dates_command, "save_text_file", fake_save_text_file)

    result = runner.invoke(fetch_dates_command.app, ["--to", str(output_dir)])

    assert result.exit_code == 0
    assert saved["directory"] == output_dir
    assert saved["filename"] == "compatibility_dates.json"
    assert "Compatibility dates saved to" in result.stderr


def test_fetch_compatibility_dates_reports_fetch_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return a user-facing error when fetching compatibility dates fails."""
    monkeypatch.setattr(
        fetch_dates_command, "client_manager", lambda: nullcontext(object())
    )
    monkeypatch.setattr(
        fetch_dates_command,
        "fetch_compatibility_dates",
        lambda _session: (_ for _ in ()).throw(RuntimeError("dates boom")),
    )

    result = runner.invoke(fetch_dates_command.app, [])

    assert result.exit_code == 1
    assert "Failed to fetch compatibility dates - dates boom" in result.stderr


def test_fetch_changelog_plain_minus_one_indent_outputs_compact_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Treat --indent -1 as compact JSON when printing the changelog."""
    changelog = {"changelog": {"2026-06-09": [{"path": "/status/"}]}}

    monkeypatch.setattr(
        fetch_changelog_command, "client_manager", lambda: nullcontext(object())
    )
    monkeypatch.setattr(
        fetch_changelog_command,
        "fetch_changelog",
        lambda _session: changelog,
    )

    result = runner.invoke(
        fetch_changelog_command.app,
        ["--plain", "--indent", "-1"],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == json.dumps(changelog, separators=(",", ":"))


def test_fetch_changelog_reports_fetch_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return a user-facing error when fetching the changelog fails."""
    monkeypatch.setattr(
        fetch_changelog_command, "client_manager", lambda: nullcontext(object())
    )
    monkeypatch.setattr(
        fetch_changelog_command,
        "fetch_changelog",
        lambda _session: (_ for _ in ()).throw(RuntimeError("changelog boom")),
    )

    result = runner.invoke(fetch_changelog_command.app, [])

    assert result.exit_code == 1
    assert "Failed to fetch schema - changelog boom" in result.stderr
