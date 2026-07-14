"""Helpers for schema CLI commands."""

from enum import StrEnum


class SchemaIOFormat(StrEnum):
    """Enum for input/output format options."""

    UNALTERED = "unaltered"
    """The schema is in its original format."""
    TIMESTAMPED = "timestamped"
    """The schema is in a timestamped format."""
    ESI_SCHEMA = "esi_schema"
    """The schema is in the eve-link ESI schema format."""
