"""Tests for schema cache CLI commands."""

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from eve_esi_link.cli.schema.cache import clear as clear_command
from eve_esi_link.cli.schema.cache import list as list_command
from eve_esi_link.cli.schema.cache import update as update_command

runner = CliRunner()


class _FakeCacheManager:
	"""Minimal schema cache stub for cache CLI command tests."""

	def __init__(
		self,
		*,
		clear_all_result: int = 0,
		clear_date_result: int = 0,
		entries: list[SimpleNamespace] | None = None,
	) -> None:
		self.clear_all_result = clear_all_result
		self.clear_date_result = clear_date_result
		self.entries = entries or []
		self.saved: list[object] = []
		self.clear_date_calls: list[str] = []
		self.clear_all_calls = 0

	def clear_all(self) -> int:
		"""Return the configured count of removed cache entries."""
		self.clear_all_calls += 1
		return self.clear_all_result

	def clear_date(self, *, compatibility_date: str) -> int:
		"""Return the configured count of removed entries for one date."""
		self.clear_date_calls.append(compatibility_date)
		return self.clear_date_result

	def list_entries(self) -> list[SimpleNamespace]:
		"""Return configured cache entries."""
		return self.entries

	def save(self, *, schema) -> None:  # noqa: ANN001
		"""Record saved schema objects."""
		self.saved.append(schema)


@pytest.fixture
def settings(tmp_path: Path) -> SimpleNamespace:
	"""Return the minimal settings surface needed by cache commands."""
	return SimpleNamespace(schema_cache_directory=tmp_path / "schema-cache")


def test_cache_clear_requires_date_or_all() -> None:
	"""Fail when neither selection flag is provided."""
	result = runner.invoke(clear_command.app, [])

	assert result.exit_code == 1
	assert "provide --date DATE or --all" in result.stderr


def test_cache_clear_reports_deleted_count_for_all(
	monkeypatch: pytest.MonkeyPatch,
	settings: SimpleNamespace,
) -> None:
	"""Clear all cached schemas and report the number removed."""
	manager = _FakeCacheManager(clear_all_result=3)

	monkeypatch.setattr(
		clear_command,
		"get_eve_link_settings_from_context",
		lambda _ctx: settings,
	)
	monkeypatch.setattr(clear_command, "SchemaCacheManager", lambda **_kwargs: manager)

	result = runner.invoke(clear_command.app, ["--all"])

	assert result.exit_code == 0
	assert manager.clear_all_calls == 1
	assert "Cleared 3 cached schema(s)." in result.stderr


def test_cache_clear_reports_missing_date(
	monkeypatch: pytest.MonkeyPatch,
	settings: SimpleNamespace,
) -> None:
	"""Print a not-found message when a specific cache date is absent."""
	manager = _FakeCacheManager(clear_date_result=0)

	monkeypatch.setattr(
		clear_command,
		"get_eve_link_settings_from_context",
		lambda _ctx: settings,
	)
	monkeypatch.setattr(clear_command, "SchemaCacheManager", lambda **_kwargs: manager)

	result = runner.invoke(clear_command.app, ["--date", "2026-06-09"])

	assert result.exit_code == 0
	assert manager.clear_date_calls == ["2026-06-09"]
	assert "No cached schema found for 2026-06-09." in result.stderr


def test_cache_list_plain_outputs_markdown_table(
	monkeypatch: pytest.MonkeyPatch,
	settings: SimpleNamespace,
) -> None:
	"""Render cache entries as plain markdown when requested."""
	manager = _FakeCacheManager(
		entries=[
			SimpleNamespace(compatibility_date="2026-06-09", timestamp=1_700_000_000_000_000_000),
			SimpleNamespace(compatibility_date="2026-06-10", timestamp=None),
		]
	)

	monkeypatch.setattr(
		list_command,
		"get_eve_link_settings_from_context",
		lambda _ctx: settings,
	)
	monkeypatch.setattr(list_command, "SchemaCacheManager", lambda **_kwargs: manager)

	result = runner.invoke(list_command.app, ["--plain"])

	assert result.exit_code == 0
	assert "# Cached ESI schema entries" in result.stdout
	assert "Compatibility Date" in result.stdout
	assert "2026-06-09" in result.stdout
	assert "2026-06-10" in result.stdout


def test_cache_update_reports_compatibility_date_fetch_failure(
	monkeypatch: pytest.MonkeyPatch,
	settings: SimpleNamespace,
) -> None:
	"""Exit when fetching the compatibility date list fails."""
	manager = _FakeCacheManager()

	monkeypatch.setattr(
		update_command,
		"get_eve_link_settings_from_context",
		lambda _ctx: settings,
	)
	monkeypatch.setattr(update_command, "SchemaCacheManager", lambda **_kwargs: manager)
	monkeypatch.setattr(update_command, "client_manager", lambda: nullcontext(object()))
	monkeypatch.setattr(
		update_command,
		"fetch_compatibility_dates",
		lambda _session: (_ for _ in ()).throw(RuntimeError("dates boom")),
	)

	result = runner.invoke(update_command.app, ["--all"])

	assert result.exit_code == 1
	assert "Failed to fetch compatibility dates - dates boom" in result.stderr
	assert manager.saved == []


def test_cache_update_fetches_all_dates_and_continues_after_schema_errors(
	monkeypatch: pytest.MonkeyPatch,
	settings: SimpleNamespace,
) -> None:
	"""Save successful schemas, continue after per-date failures, and report totals."""
	manager = _FakeCacheManager()

	monkeypatch.setattr(
		update_command,
		"get_eve_link_settings_from_context",
		lambda _ctx: settings,
	)
	monkeypatch.setattr(update_command, "SchemaCacheManager", lambda **_kwargs: manager)
	monkeypatch.setattr(update_command, "client_manager", lambda: nullcontext(object()))
	monkeypatch.setattr(
		update_command,
		"fetch_compatibility_dates",
		lambda _session: SimpleNamespace(
			compatibility_dates=("2026-06-09", "2026-06-10")
		),
	)

	def fake_fetch_schema(_session, *, schema_as_of: str) -> SimpleNamespace:
		if schema_as_of == "2026-06-10":
			raise RuntimeError("schema boom")
		return SimpleNamespace(
			schema={"info": {"version": schema_as_of}},
			timestamp=123,
		)

	monkeypatch.setattr(update_command, "fetch_schema", fake_fetch_schema)
	monkeypatch.setattr(
		update_command.EsiSchema,
		"from_raw_schema",
		lambda *, raw_schema, timestamp: SimpleNamespace(
			compatibility_date=raw_schema["info"]["version"],
			timestamp=timestamp,
		),
	)

	result = runner.invoke(update_command.app, ["--all"])

	assert result.exit_code == 0
	assert len(manager.saved) == 1
	assert manager.saved[0].compatibility_date == "2026-06-09"
	assert "Cached schema for 2026-06-09." in result.stderr
	assert "Failed to fetch schema for 2026-06-10 - schema boom" in result.stderr
	assert "Done. Cached 1 schema(s)." in result.stderr
