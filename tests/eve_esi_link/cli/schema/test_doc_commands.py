"""Tests for schema documentation CLI commands."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from eve_esi_link.cli.schema import doc as doc_command
from eve_esi_link.cli.schema.cache import doc as cache_doc_command

runner = CliRunner()


class _FakeCacheManager:
    """Minimal cache manager stub for schema doc command tests."""

    def __init__(
        self, *, entries: list[SimpleNamespace], loaded: object | None = None
    ) -> None:
        self._entries = entries
        self._loaded = loaded
        self.load_calls: list[str] = []

    def list_entries(self) -> list[SimpleNamespace]:
        """Return configured cache entries."""
        return self._entries

    def load(self, *, compatibility_date: str) -> object:
        """Return the configured schema and record the requested date."""
        self.load_calls.append(compatibility_date)
        return self._loaded


@pytest.fixture
def settings(tmp_path: Path) -> SimpleNamespace:
    """Return the minimal settings surface required by schema cache doc."""
    return SimpleNamespace(schema_cache_directory=tmp_path / "schema-cache")


def test_cache_doc_reports_missing_cached_date_once(
    monkeypatch: pytest.MonkeyPatch,
    settings: SimpleNamespace,
) -> None:
    """Report a missing cached schema date without a generic follow-up error."""
    manager = _FakeCacheManager(
        entries=[SimpleNamespace(compatibility_date="2026-06-09")]
    )

    monkeypatch.setattr(
        cache_doc_command,
        "get_eve_link_settings_from_context",
        lambda _ctx: settings,
    )
    monkeypatch.setattr(
        cache_doc_command,
        "SchemaCacheManager",
        lambda **_kwargs: manager,
    )

    result = runner.invoke(cache_doc_command.app, ["--date", "2026-06-10"])

    assert result.exit_code == 1
    assert "No cached schema found for 2026-06-10" in result.stderr
    assert "Failed to load cached schema" not in result.stderr


def test_cache_doc_saves_directory_output_with_default_filename(
    monkeypatch: pytest.MonkeyPatch,
    settings: SimpleNamespace,
    tmp_path: Path,
) -> None:
    """Save cached schema docs to a directory using the auto-generated filename."""
    schema = object()
    manager = _FakeCacheManager(
        entries=[SimpleNamespace(compatibility_date="2026-06-09")],
        loaded=schema,
    )
    output_dir = tmp_path / "docs"
    saved: dict[str, object] = {}

    monkeypatch.setattr(
        cache_doc_command,
        "get_eve_link_settings_from_context",
        lambda _ctx: settings,
    )
    monkeypatch.setattr(
        cache_doc_command,
        "SchemaCacheManager",
        lambda **_kwargs: manager,
    )
    monkeypatch.setattr(
        cache_doc_command,
        "generate_esi_schema_markdown_doc",
        lambda *, schema, fenced_format: "# Cached Schema Doc\n",
    )

    def fake_save_text_file(**kwargs):  # noqa: ANN003
        saved.update(kwargs)
        return output_dir / kwargs["filename"]

    monkeypatch.setattr(cache_doc_command, "save_text_file", fake_save_text_file)

    result = runner.invoke(
        cache_doc_command.app,
        ["--date", "2026-06-09", "--to", str(output_dir)],
    )

    assert result.exit_code == 0
    assert manager.load_calls == ["2026-06-09"]
    assert saved["directory"] == output_dir
    assert saved["filename"] == "schema_docs_2026-06-09.md"
    assert "Markdown documentation saved to" in result.stderr


def test_generate_doc_reports_invalid_stdin_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return a user-facing error when stdin JSON is valid but not a schema."""
    monkeypatch.setattr(doc_command, "get_stdin", lambda: '{"invalid": true}')

    result = runner.invoke(doc_command.app, ["--from", "-"])

    assert result.exit_code == 1
    assert "Failed to load schema from JSON input" in result.stderr


def test_generate_doc_prints_plain_markdown_from_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generate markdown from stdin and print plain text to stdout."""
    schema = SimpleNamespace(compatibility_date="2026-06-09")

    monkeypatch.setattr(doc_command, "get_stdin", lambda: '{"schema": {}}')
    monkeypatch.setattr(doc_command.json_io, "json_loads", lambda _text: {"schema": {}})
    monkeypatch.setattr(doc_command, "load_esi_schema", lambda _schema: schema)
    monkeypatch.setattr(
        doc_command,
        "generate_esi_schema_markdown_doc",
        lambda *, schema, fenced_format: "# Generated Schema Doc\n",
    )

    result = runner.invoke(doc_command.app, ["--from", "-", "--plain"])

    assert result.exit_code == 0
    assert result.stdout == "# Generated Schema Doc\n\n"


def test_generate_doc_saves_directory_output_with_default_filename(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Save generated docs to a directory using the schema compatibility date."""
    input_path = tmp_path / "schema.json"
    input_path.write_text("{}", encoding="utf-8")
    output_dir = tmp_path / "docs"
    schema = SimpleNamespace(compatibility_date="2026-06-09")
    saved: dict[str, object] = {}

    monkeypatch.setattr(
        doc_command, "load_esi_schema_from_file", lambda *, file_path: schema
    )
    monkeypatch.setattr(
        doc_command,
        "generate_esi_schema_markdown_doc",
        lambda *, schema, fenced_format: "# Generated Schema Doc\n",
    )

    def fake_save_text_file(**kwargs):  # noqa: ANN003
        saved.update(kwargs)
        return output_dir / kwargs["filename"]

    monkeypatch.setattr(doc_command, "save_text_file", fake_save_text_file)

    result = runner.invoke(
        doc_command.app,
        ["--from", str(input_path), "--to", str(output_dir)],
    )

    assert result.exit_code == 0
    assert saved["directory"] == output_dir
    assert saved["filename"] == "schema_docs_2026-06-09.md"
    assert "Markdown documentation saved to" in result.stderr
