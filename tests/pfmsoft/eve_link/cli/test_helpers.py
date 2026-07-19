"""Tests for CLI helper utilities."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import typer
from pfmsoft.api_request.settings import ApiRequestSettings
from pfmsoft.eve_auth_manager.settings import EveAuthManagerSettings

from pfmsoft.eve_link.cli import helpers
from pfmsoft.eve_link.settings import SETTINGS_KEY, EsiLinkSettings


class _FakeStdin:
    """Simple stdin stub with controllable TTY behavior."""

    def __init__(self, text: str, *, is_tty: bool) -> None:
        self._text = text
        self._is_tty = is_tty

    def isatty(self) -> bool:
        """Report whether stdin is interactive."""
        return self._is_tty

    def read(self) -> str:
        """Return the prepared stdin payload."""
        return self._text


class _FakeConsole:
    """Collect console messages for assertions."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def print(self, message: str) -> None:
        """Store printed messages."""
        self.messages.append(message)


class _FakeSchemaManager:
    """Minimal schema cache manager stub for get_schema tests."""

    def __init__(
        self,
        *,
        entries: list[SimpleNamespace] | None = None,
        loaded: dict[str, object] | None = None,
        load_error: Exception | None = None,
    ) -> None:
        self._entries = entries or []
        self._loaded = loaded or {}
        self._load_error = load_error
        self.load_calls: list[str] = []

    def list_entries(self) -> list[SimpleNamespace]:
        """Return configured cache entries."""
        return self._entries

    def load(self, *, compatibility_date: str) -> object:
        """Load a schema or raise the configured error."""
        self.load_calls.append(compatibility_date)
        if self._load_error is not None:
            raise self._load_error
        return self._loaded[compatibility_date]


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


def test_get_stdin_reads_non_interactive_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return piped stdin content when stdin is not a TTY."""
    monkeypatch.setattr(helpers.sys, "stdin", _FakeStdin("payload", is_tty=False))

    assert helpers.get_stdin() == "payload"


def test_get_stdin_rejects_interactive_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require a file or pipe instead of interactive stdin."""
    monkeypatch.setattr(helpers.sys, "stdin", _FakeStdin("", is_tty=True))

    with pytest.raises(ValueError, match="pipe data via stdin"):
        helpers.get_stdin()


def test_get_eve_link_settings_from_context_returns_stored_settings(
    settings: EsiLinkSettings,
) -> None:
    """Read the app settings from the Typer context object."""
    ctx = SimpleNamespace(obj={SETTINGS_KEY: settings})

    assert helpers.get_eve_link_settings_from_context(ctx) is settings


def test_construct_settings_for_subsystems(settings: EsiLinkSettings) -> None:
    """Map app settings into dependent subsystem settings objects."""
    auth_settings = helpers.construct_eve_auth_manager_settings(settings)
    api_settings = helpers.construct_api_request_settings(settings)

    assert isinstance(auth_settings, EveAuthManagerSettings)
    assert auth_settings.application_directory == settings.application_directory
    assert auth_settings.logging_directory == settings.logging_directory
    assert auth_settings.authorization_database_path == settings.auth_manager_db_file

    assert isinstance(api_settings, ApiRequestSettings)
    assert api_settings.application_directory == settings.application_directory
    assert api_settings.logging_directory == settings.logging_directory
    assert api_settings.web_cache_path == settings.api_request_cache_file


def test_get_schema_loads_requested_compatibility_date() -> None:
    """Load the explicitly requested cached schema date."""
    console = _FakeConsole()
    expected_schema = object()
    manager = _FakeSchemaManager(loaded={"2026-06-09": expected_schema})

    loaded = helpers.get_schema(console, manager, "2026-06-09")

    assert loaded is expected_schema
    assert manager.load_calls == ["2026-06-09"]
    assert console.messages == []


def test_get_schema_uses_most_recent_cached_date_when_unspecified() -> None:
    """Pick the max compatibility date from available cache entries."""
    console = _FakeConsole()
    expected_schema = object()
    manager = _FakeSchemaManager(
        entries=[
            SimpleNamespace(compatibility_date="2026-06-08"),
            SimpleNamespace(compatibility_date="2026-06-09"),
        ],
        loaded={"2026-06-09": expected_schema},
    )

    loaded = helpers.get_schema(console, manager, None)

    assert loaded is expected_schema
    assert manager.load_calls == ["2026-06-09"]
    assert console.messages == ["Using most recent cached schema: 2026-06-09"]


def test_get_schema_exits_when_cache_is_empty() -> None:
    """Exit with a user-facing error when no cached schemas exist."""
    console = _FakeConsole()
    manager = _FakeSchemaManager(entries=[])

    with pytest.raises(typer.Exit) as exc_info:
        helpers.get_schema(console, manager, None)

    assert exc_info.value.exit_code == 1
    assert console.messages == [
        "[red]Error: No cached schemas found. Use --schema or update the cache.[/red]"
    ]


def test_get_schema_exits_when_requested_date_is_missing() -> None:
    """Translate missing cache entries into a Typer exit."""
    console = _FakeConsole()
    manager = _FakeSchemaManager(load_error=FileNotFoundError("missing"))

    with pytest.raises(typer.Exit) as exc_info:
        helpers.get_schema(console, manager, "2026-06-09")

    assert exc_info.value.exit_code == 1
    assert console.messages == [
        "[red]Error: No cached schema found for 2026-06-09.[/red]"
    ]


def test_get_schema_exits_on_unexpected_load_error() -> None:
    """Report unexpected cache load failures to the caller."""
    console = _FakeConsole()
    manager = _FakeSchemaManager(load_error=RuntimeError("boom"))

    with pytest.raises(typer.Exit) as exc_info:
        helpers.get_schema(console, manager, "2026-06-09")

    assert exc_info.value.exit_code == 1
    assert console.messages == ["[red]Error: Failed to load cached schema - boom[/red]"]
