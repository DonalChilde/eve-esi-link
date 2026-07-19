"""Tests for small pure helper modules."""

from pathlib import Path

import pytest
from whenever import Instant

from pfmsoft.eve_link.helpers import eve_dates
from pfmsoft.eve_link.helpers.file_safe_string import (
    file_safe_string,
    is_alphanum_or_dash,
    is_alphanum_or_dash_character,
)
from pfmsoft.eve_link.helpers.resolve_json_ref import resolve_internal_refs
from pfmsoft.eve_link.helpers.save_text_file import save_text_file


def test_file_safe_string_normalizes_separator_runs() -> None:
    """Replace unsafe characters, collapse separators, and trim edges."""
    assert file_safe_string("  hello,/world__test!!  ") == "hello_world_test"


def test_is_alphanum_or_dash_checks_strings_and_characters() -> None:
    """Accept only ASCII letters, digits, dashes, and underscores."""
    assert is_alphanum_or_dash("abc-123_name") is True
    assert is_alphanum_or_dash("abc 123") is False
    assert is_alphanum_or_dash_character("-") is True
    assert is_alphanum_or_dash_character("!") is False


def test_resolve_internal_refs_recursively_resolves_nested_objects() -> None:
    """Resolve referenced objects inside dict and list structures."""
    parent = {
        "components": {
            "schemas": {
                "Address": {
                    "type": "object",
                    "properties": {"system": {"type": "string"}},
                },
                "Character": {
                    "type": "object",
                    "properties": {
                        "home": {"$ref": "#/components/schemas/Address"},
                        "aliases": [{"$ref": "#/components/schemas/Address"}],
                    },
                },
            }
        }
    }

    resolved = resolve_internal_refs(
        parent,
        {"$ref": "#/components/schemas/Character"},
    )

    assert resolved["properties"]["home"]["properties"]["system"] == {"type": "string"}
    assert resolved["properties"]["aliases"][0]["properties"]["system"] == {
        "type": "string"
    }


def test_resolve_internal_refs_rejects_external_refs() -> None:
    """Reject references outside the current document."""
    with pytest.raises(ValueError, match="Only internal refs supported"):
        resolve_internal_refs({}, {"$ref": "https://example.com/schema.json"})


def test_save_text_file_creates_parent_directory_and_appends_newline(
    tmp_path: Path,
) -> None:
    """Create missing directories and append a trailing newline by default."""
    output = save_text_file(
        text="hello",
        directory=tmp_path / "nested",
        filename="greeting.txt",
    )

    assert output == tmp_path / "nested" / "greeting.txt"
    assert output.read_text(encoding="utf-8") == "hello\n"


def test_save_text_file_honors_overwrite_and_newline_options(tmp_path: Path) -> None:
    """Allow overwrite explicitly and skip the trailing newline when requested."""
    output = save_text_file(
        text="first",
        directory=tmp_path,
        filename="note.txt",
    )

    with pytest.raises(FileExistsError):
        save_text_file(text="second", directory=tmp_path, filename="note.txt")

    replaced = save_text_file(
        text="second",
        directory=tmp_path,
        filename="note.txt",
        overwrite=True,
        add_newline=False,
    )

    assert replaced == output
    assert output.read_text(encoding="utf-8") == "second"


@pytest.mark.parametrize(
    ("value", "expected_previous", "expected_next"),
    [
        (
            Instant("2026-07-15T10:59:59Z"),
            Instant("2026-07-14T11:00:00Z"),
            Instant("2026-07-15T11:00:00Z"),
        ),
        (
            Instant("2026-07-15T11:00:00Z"),
            Instant("2026-07-15T11:00:00Z"),
            Instant("2026-07-16T11:00:00Z"),
        ),
        (
            Instant("2026-07-15T11:00:01Z"),
            Instant("2026-07-15T11:00:00Z"),
            Instant("2026-07-16T11:00:00Z"),
        ),
    ],
)
def test_downtime_bracket_covers_before_at_and_after_cases(
    value: Instant,
    expected_previous: Instant,
    expected_next: Instant,
) -> None:
    """Bracket downtime around instants on both sides of the cutoff."""
    assert eve_dates.downtime_bracket(value) == (expected_previous, expected_next)


def test_previous_and_next_downtime_delegate_to_bracket() -> None:
    """Expose the previous and next downtime from the shared bracket logic."""
    instant = Instant("2026-07-15T09:00:00Z")

    assert eve_dates.previous_downtime(instant) == Instant("2026-07-14T11:00:00Z")
    assert eve_dates.next_downtime(instant) == Instant("2026-07-15T11:00:00Z")


def test_latest_schema_date_uses_previous_eve_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return the day before the previous downtime date."""
    monkeypatch.setattr(
        eve_dates,
        "previous_downtime",
        lambda _instant: Instant("2026-07-15T11:00:00Z"),
    )

    assert eve_dates.latest_schema_date() == "2026-07-14"
