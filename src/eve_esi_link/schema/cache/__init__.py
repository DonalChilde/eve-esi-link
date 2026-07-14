"""Schema cache manager for local ESI schema JSON files.

This package provides a file-based cache for EsiSchema objects keyed by
compatibility date. It does not fetch schemas from ESI; callers are expected to
provide already fetched schemas.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from eve_esi_link.schema.helpers.schema_files import (
    default_file_name_for_cached_schema,
    load_esi_schema_from_file,
)
from eve_esi_link.schema.models import EsiSchema

_SCHEMA_FILE_RE = re.compile(
    r"^schema_(?P<compatibility_date>\d{4}-\d{2}-\d{2})_(?P<timestamp>\d+|None)_esi_schema\.json$"
)


@dataclass(slots=True, frozen=True, kw_only=True)
class _ParsedCacheFileName:
    """Structured representation of a recognized cache file name."""

    compatibility_date: str
    timestamp: int | None


@dataclass(slots=True, frozen=True, kw_only=True)
class SchemaCacheEntry:
    """Metadata describing a cached schema entry.

    Attributes:
        compatibility_date: Compatibility date for the schema in YYYY-MM-DD.
        timestamp: Fetch timestamp in nanoseconds when available.
    """

    compatibility_date: str
    timestamp: int | None


class SchemaCacheManager:
    """Manage persisted ESI schema cache files in a single directory.

    The cache enforces one canonical entry per compatibility date by replacing
    existing date-matching files on save.
    """

    def __init__(self, *, cache_directory: Path) -> None:
        """Initialize a cache manager.

        Args:
            cache_directory: Directory containing cached schema JSON files.
        """
        self._cache_directory = cache_directory

    @property
    def cache_directory(self) -> Path:
        """Return the configured cache directory path."""
        return self._cache_directory

    def save(self, *, schema: EsiSchema) -> SchemaCacheEntry:
        """Save a schema to cache, replacing any existing entry for its date.

        Args:
            schema: Schema to cache.

        Returns:
            Metadata for the saved cache entry.
        """
        self._cache_directory.mkdir(parents=True, exist_ok=True)

        for existing_path in self._files_for_compatibility_date(
            compatibility_date=schema.compatibility_date
        ):
            existing_path.unlink(missing_ok=True)

        output_name = default_file_name_for_cached_schema(schema)
        output_path = self._cache_directory / output_name
        output_path.write_text(schema.serialize(), encoding="utf-8")

        return SchemaCacheEntry(
            compatibility_date=schema.compatibility_date,
            timestamp=schema.timestamp,
        )

    def load(self, *, compatibility_date: str) -> EsiSchema:
        """Load a cached schema by compatibility date.

        Args:
            compatibility_date: Date key in YYYY-MM-DD format.

        Returns:
            Loaded EsiSchema.

        Raises:
            FileNotFoundError: If no cached schema exists for the date.
            ValueError: If multiple cached files exist for the same date.
        """
        matching_files = self._files_for_compatibility_date(
            compatibility_date=compatibility_date
        )
        if not matching_files:
            raise FileNotFoundError(
                f"No cached schema found for compatibility date {compatibility_date}."
            )
        if len(matching_files) > 1:
            raise ValueError(
                "Multiple cached schemas found for compatibility date "
                f"{compatibility_date}."
            )
        return load_esi_schema_from_file(matching_files[0])

    def list_entries(self) -> list[SchemaCacheEntry]:
        """List all cached schema entries.

        Returns:
            Sorted list of cache entries by compatibility_date then timestamp.
        """
        entries: list[SchemaCacheEntry] = []
        for cache_file in self._iter_cache_files():
            parsed = self._parse_cache_file_name(cache_file.name)
            if parsed is None:
                continue
            entries.append(
                SchemaCacheEntry(
                    compatibility_date=parsed.compatibility_date,
                    timestamp=parsed.timestamp,
                )
            )

        return sorted(
            entries,
            key=lambda item: (
                item.compatibility_date,
                item.timestamp is None,
                item.timestamp if item.timestamp is not None else -1,
            ),
        )

    def clear_date(self, *, compatibility_date: str) -> int:
        """Delete cached schema file(s) for one compatibility date.

        Args:
            compatibility_date: Date key in YYYY-MM-DD format.

        Returns:
            Number of deleted files.
        """
        deleted = 0
        for cache_file in self._files_for_compatibility_date(
            compatibility_date=compatibility_date
        ):
            cache_file.unlink(missing_ok=True)
            deleted += 1
        return deleted

    def clear_all(self) -> int:
        """Delete all recognized cached schema files.

        Returns:
            Number of deleted files.
        """
        deleted = 0
        for cache_file in self._iter_cache_files():
            if self._parse_cache_file_name(cache_file.name) is None:
                continue
            cache_file.unlink(missing_ok=True)
            deleted += 1
        return deleted

    def _iter_cache_files(self) -> list[Path]:
        """Return sorted files in the cache directory.

        Missing directories produce an empty list.
        """
        if not self._cache_directory.exists():
            return []
        return sorted(
            path for path in self._cache_directory.iterdir() if path.is_file()
        )

    def _files_for_compatibility_date(self, *, compatibility_date: str) -> list[Path]:
        """Return cache files matching one compatibility date."""
        matching_files: list[Path] = []
        for cache_file in self._iter_cache_files():
            parsed = self._parse_cache_file_name(cache_file.name)
            if parsed is None:
                continue
            if parsed.compatibility_date == compatibility_date:
                matching_files.append(cache_file)
        return matching_files

    def _parse_cache_file_name(self, file_name: str) -> _ParsedCacheFileName | None:
        """Parse cache file names that follow the schema cache naming convention."""
        match = _SCHEMA_FILE_RE.match(file_name)
        if match is None:
            return None
        timestamp_string = match.group("timestamp")
        timestamp: int | None
        if timestamp_string == "None":
            timestamp = None
        else:
            timestamp = int(timestamp_string)

        return _ParsedCacheFileName(
            compatibility_date=match.group("compatibility_date"),
            timestamp=timestamp,
        )


__all__ = ["SchemaCacheEntry", "SchemaCacheManager"]
