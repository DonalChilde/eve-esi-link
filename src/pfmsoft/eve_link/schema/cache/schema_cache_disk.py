"""Schema cache manager for local ESI schema JSON files.

This package provides a file-based cache for EsiSchema objects keyed by
compatibility date. It does not fetch schemas from ESI; callers are expected to
provide already fetched schemas.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from httpx2 import Client
from pfmsoft.eve_snippets.eve.eve_dates import previous_downtime

from pfmsoft.eve_link.schema.helpers.fetch import (
    TimestampedCompatibilityDates,
    fetch_compatibility_dates,
    fetch_schema,
)
from pfmsoft.eve_link.schema.helpers.schema_files import (
    default_file_name_for_cached_schema,
    load_esi_schema_from_file,
)
from pfmsoft.eve_link.schema.models import EsiSchema

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

    The cache manager handles reading and writing schema files, as well as
    maintaining a list of valid compatibility dates. It provides methods to fetch
    and cache schemas for all known compatibility dates.
    """

    def __init__(self, *, cache_directory: Path) -> None:
        """Initialize a cache manager.

        Args:
            cache_directory: Directory containing cached schema JSON files.
        """
        self._cache_directory = cache_directory
        self._compatibility_dates: TimestampedCompatibilityDates | None = None
        self._load_compatibility_dates()

    def _compatibility_dates_path(self) -> Path:
        """Return the path to the cached compatibility dates file."""
        return self._cache_directory / "compatibility_dates.json"

    def _fetch_compatibility_dates(self, session: Client) -> None:
        """Fetch the list of compatibility dates from ESI.

        Args:
            session: An instance of httpx2.Client for making HTTP requests.
        """
        compatibility_dates = fetch_compatibility_dates(session=session)
        self._compatibility_dates_path().write_text(
            compatibility_dates.serialize(indent=2), encoding="utf-8"
        )
        self._compatibility_dates = compatibility_dates

    def _load_compatibility_dates(self) -> None:
        """Load and cache the list of compatibility dates from disk."""
        if self._compatibility_dates_path().exists():
            self._compatibility_dates = TimestampedCompatibilityDates.deserialize(
                self._compatibility_dates_path().read_text(encoding="utf-8")
            )
        else:
            self._compatibility_dates = None

    def _ensure_compatibility_dates(self, session: Client) -> None:
        """Ensure that compatibility dates are loaded and current, fetching from ESI if necessary.

        Args:
            session: An instance of httpx2.Client for making HTTP requests.
        """
        if self._compatibility_dates is None:
            self._fetch_compatibility_dates(session=session)
            return
        if self._compatibility_dates.timestamp_instant() < previous_downtime():
            self._fetch_compatibility_dates(session=session)

    @property
    def valid_compatibility_dates(self) -> tuple[str, ...]:
        """Return the list of valid compatibility dates.

        Returns:
            Tuple of compatibility dates in YYYY-MM-DD format.
        """
        if self._compatibility_dates is None:
            raise RuntimeError(
                "Compatibility dates have not been loaded. Call "
                "fetch_updates(session) first."
            )
        return self._compatibility_dates.compatibility_dates

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

    def latest_entry(self) -> SchemaCacheEntry | None:
        """Return the latest cached schema entry by compatibility date.

        Returns:
            The latest SchemaCacheEntry or None if no entries exist.
        """
        entries = self.list_entries()
        if not entries:
            return None
        return max(entries, key=lambda entry: entry.compatibility_date)

    def latest_schema(self) -> EsiSchema | None:
        """Return the latest cached schema by compatibility date.

        Returns:
            The latest EsiSchema or None if no entries exist.
        """
        latest_entry = self.latest_entry()
        if latest_entry is None:
            return None
        return self.load(compatibility_date=latest_entry.compatibility_date)

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

    def fetch_updates(
        self,
        session: Client,
    ) -> None:
        """Fetch and cache schemas by compatibility date, replacing existing cached files.

        This method ensures the latest available compatibility dates are fetched and
        cached, and then fetches and caches any missing schemas from the EVE Online API
        for those dates.

        Args:
            session: An instance of httpx2.Client for making HTTP requests.

        Raises:
            httpx2.HTTPError: If any HTTP request fails.
        """
        self._ensure_compatibility_dates(session=session)
        entries = self.list_entries()
        cached_dates = {entry.compatibility_date for entry in entries}

        for compatibility_date in self.valid_compatibility_dates:
            if compatibility_date in cached_dates:
                continue  # Skip already cached dates
            # Fetch the latest schema for the compatibility date
            timestamped_schema = fetch_schema(
                session=session, schema_as_of=compatibility_date
            )
            # Save the fetched schema to the cache
            self.save(
                schema=EsiSchema.from_raw_schema(
                    raw_schema=timestamped_schema.schema,
                    timestamp=timestamped_schema.timestamp,
                )
            )

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
