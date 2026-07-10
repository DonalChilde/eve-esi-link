"""Module for fetching the ESI OpenAPI schema and compatibility dates."""

import logging
from datetime import datetime

from httpx2 import Client
from whenever import Instant

from eve_esi_link.schema.models import TimestampedCompatibilityDates, TimestampedSchema
from eve_esi_link.settings import ESI_SCHEMA_URL

logger = logging.getLogger(__name__)


def fetch_schema(
    session: Client, *, schema_as_of: str, url: str = ESI_SCHEMA_URL
) -> TimestampedSchema:
    """Fetch the ESI OpenAPI schema for a given date.

    Dates cannot be in the future. And the most recent available is
    the date of the last downtime, since the schema is updated at downtime (currently
    11:00 UTC).

    The returned schema will be for the most current schema on the schema_as_of
    date. The schema is returned as a dictionary, and the timestamp is returned as an
    integer representing the timestamp when the schema was fetched in nanoseconds.

    Args:
        session (Client): An instance of httpx2.Client to make the HTTP request.
        schema_as_of (str): The date for which to fetch the schema,
            in the format YYYY-MM-DD.
        url (str): The URL to fetch the schema from. Defaults to ESI_SCHEMA_URL.

    Returns:
        TimestampedSchema: An object containing the fetched schema and its associated
            timestamp.

    Raises:
        httpx2.HTTPError: If the HTTP request fails or returns a non-success status code.
        ValueError: If the response cannot be parsed as JSON or if the compatibility
            date is invalid.
    """
    try:
        params = {"compatibility_date": schema_as_of}
        response = session.get(url, params=params)
        response.raise_for_status()
        schema_data = response.json()
        timestamp = Instant.now().timestamp_nanos()
        logger.info(
            "Fetched schema for date %s with timestamp %d",
            schema_as_of,
            timestamp,
        )
        return TimestampedSchema(schema=schema_data, timestamp=timestamp)
    except Exception as e:
        logger.error("Error fetching schema: %s, with date %s", e, schema_as_of)
        raise


def fetch_compatibility_dates(session: Client) -> TimestampedCompatibilityDates:
    """Fetch the list of compatibility dates from the ESI API.

    Args:
        session (Client): An instance of httpx2.Client to make the HTTP request.

    Returns:
        TimestampedCompatibilityDates: An object containing the fetched compatibility
            dates and their associated timestamp.

    Raises:
        httpx2.HTTPError: If the HTTP request fails or returns a non-success status code.
        ValueError: If the response cannot be parsed as JSON or if the compatibility
            dates are invalid.
    """
    try:
        response = session.get(f"{ESI_SCHEMA_URL}/compatibility-dates")
        response.raise_for_status()
        dates: list[str] = response.json()
        if not isinstance(dates, list):  # type: ignore
            raise ValueError("Invalid response format for compatibility dates")
        # Check that all items in the list are dates in string format (YYYY-MM-DD)
        for date_str in dates:
            try:
                datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValueError(
                    f"Invalid date format in compatibility dates: {date_str}"
                ) from e
        return TimestampedCompatibilityDates(
            dates=tuple(dates), timestamp=Instant.now().timestamp_nanos()
        )
    except Exception as e:
        logger.error("Error fetching compatibility dates: %s", e)
        raise


def fetch_schema_changelog(
    session: Client, *, compatibility_date: str, url: str = ""
) -> dict[str, list[str]]:
    """Fetch the ESI OpenAPI schema changelog for a given compatibility date."""
    ...
