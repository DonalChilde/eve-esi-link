"""Tests for schema cache manager behavior."""

from pathlib import Path

import pytest

from pfmsoft.eve_link.schema.cache import SchemaCacheEntry, SchemaCacheManager
from pfmsoft.eve_link.schema.models import EsiSchema


def _make_raw_schema(*, compatibility_date: str = "2026-06-09") -> dict[str, object]:
    """Build a minimal valid OpenAPI schema fixture."""
    return {
        "openapi": "3.0.0",
        "info": {"version": compatibility_date, "title": "test-schema"},
        "servers": [{"url": "https://esi.evetech.net"}],
        "paths": {
            "/status/": {
                "get": {
                    "operationId": "GetStatus",
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }


def _make_schema(
    *, compatibility_date: str = "2026-06-09", timestamp: int
) -> EsiSchema:
    """Create a test EsiSchema with explicit compatibility date and timestamp."""
    return EsiSchema.from_raw_schema(
        _make_raw_schema(compatibility_date=compatibility_date),
        timestamp=timestamp,
    )


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    """Save and load a schema by compatibility date."""
    manager = SchemaCacheManager(cache_directory=tmp_path)
    schema = _make_schema(compatibility_date="2026-06-09", timestamp=123)

    entry = manager.save(schema=schema)
    loaded = manager.load(compatibility_date="2026-06-09")

    assert entry == SchemaCacheEntry(compatibility_date="2026-06-09", timestamp=123)
    assert loaded.compatibility_date == "2026-06-09"
    assert loaded.timestamp == 123


def test_save_overwrites_existing_date_entry(tmp_path: Path) -> None:
    """Replace existing cached entry when saving same compatibility date."""
    manager = SchemaCacheManager(cache_directory=tmp_path)

    manager.save(schema=_make_schema(compatibility_date="2026-06-09", timestamp=100))
    manager.save(schema=_make_schema(compatibility_date="2026-06-09", timestamp=200))

    entries = manager.list_entries()

    assert entries == [
        SchemaCacheEntry(compatibility_date="2026-06-09", timestamp=200),
    ]
    loaded = manager.load(compatibility_date="2026-06-09")
    assert loaded.timestamp == 200


def test_list_entries_sorted_and_path_free(tmp_path: Path) -> None:
    """Return sorted list entries containing only date and timestamp."""
    manager = SchemaCacheManager(cache_directory=tmp_path)

    manager.save(schema=_make_schema(compatibility_date="2026-06-10", timestamp=2))
    manager.save(schema=_make_schema(compatibility_date="2026-06-09", timestamp=3))
    manager.save(schema=_make_schema(compatibility_date="2026-06-11", timestamp=1))

    entries = manager.list_entries()

    assert entries == [
        SchemaCacheEntry(compatibility_date="2026-06-09", timestamp=3),
        SchemaCacheEntry(compatibility_date="2026-06-10", timestamp=2),
        SchemaCacheEntry(compatibility_date="2026-06-11", timestamp=1),
    ]


def test_load_missing_date_raises_file_not_found(tmp_path: Path) -> None:
    """Raise FileNotFoundError when no entry exists for a date."""
    manager = SchemaCacheManager(cache_directory=tmp_path)

    with pytest.raises(FileNotFoundError):
        manager.load(compatibility_date="2026-06-09")


def test_load_duplicate_date_files_raises_value_error(tmp_path: Path) -> None:
    """Raise ValueError when duplicate files exist for one date."""
    manager = SchemaCacheManager(cache_directory=tmp_path)

    file_a = tmp_path / "schema_2026-06-09_100_esi_schema.json"
    file_b = tmp_path / "schema_2026-06-09_101_esi_schema.json"
    schema = _make_schema(compatibility_date="2026-06-09", timestamp=100)
    file_a.write_text(schema.serialize(), encoding="utf-8")
    file_b.write_text(schema.serialize(), encoding="utf-8")

    with pytest.raises(ValueError):
        manager.load(compatibility_date="2026-06-09")


def test_clear_date_removes_only_target_date(tmp_path: Path) -> None:
    """Delete only files belonging to the requested compatibility date."""
    manager = SchemaCacheManager(cache_directory=tmp_path)

    manager.save(schema=_make_schema(compatibility_date="2026-06-09", timestamp=1))
    manager.save(schema=_make_schema(compatibility_date="2026-06-10", timestamp=2))

    deleted = manager.clear_date(compatibility_date="2026-06-09")

    assert deleted == 1
    assert manager.list_entries() == [
        SchemaCacheEntry(compatibility_date="2026-06-10", timestamp=2)
    ]


def test_clear_all_ignores_unrelated_files(tmp_path: Path) -> None:
    """Delete only recognized cache files and keep unrelated files."""
    manager = SchemaCacheManager(cache_directory=tmp_path)

    manager.save(schema=_make_schema(compatibility_date="2026-06-09", timestamp=1))
    manager.save(schema=_make_schema(compatibility_date="2026-06-10", timestamp=2))
    unrelated = tmp_path / "note.txt"
    unrelated.write_text("keep me", encoding="utf-8")

    deleted = manager.clear_all()

    assert deleted == 2
    assert manager.list_entries() == []
    assert unrelated.exists()
