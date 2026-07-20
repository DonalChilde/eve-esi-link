"""Tests for small pure helper modules."""

import pytest

from pfmsoft.eve_link.helpers.file_safe_string import (
    file_safe_string,
    is_alphanum_or_dash,
    is_alphanum_or_dash_character,
)
from pfmsoft.eve_link.helpers.resolve_json_ref import resolve_internal_refs


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
