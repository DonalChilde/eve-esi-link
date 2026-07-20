"""Schema file loading helpers and cache filename conventions.

Accepted top-level shapes:

- OpenAPI dict (openapi/info/paths/components)
- EsiSchemaTD envelope ({"dereferenced_schema", "timestamp"})
- Timestamped schema envelope ({"schema", "timestamp"})
"""

from pathlib import Path
from typing import Any

from pfmsoft.eve_snippets import json_io
from whenever import Instant

from pfmsoft.eve_link.schema.helpers.schema_check import (
    is_esi_schema_td,
    is_open_api_schema,
    is_raw_schema,
    is_timestamped_schema,
)
from pfmsoft.eve_link.schema.models import EsiSchema, EsiSchemaRoot


def load_esi_schema(
    schema_dict: dict[str, Any], timestamp: Instant | None = None
) -> EsiSchema:
    """Load the ESI schema from a dictionary.

    Args:
        schema_dict: The dictionary containing the ESI schema.
        timestamp: The timestamp associated with the schema, representing the timestamp when the
            schema was fetched as an Instant. This field is optional and can be None if the
            timestamp is not available or not applicable.

    Returns:
        An instance of EsiSchema containing the loaded schema and its associated
        timestamp.

    Notes:
        For OpenAPI-shaped input, the loader detects whether ``$ref`` keys are
        present. Raw schemas are dereferenced via ``EsiSchema.from_raw_schema``.
        Already-dereferenced schemas are validated as ``EsiSchemaTD`` payloads.
    """
    if is_open_api_schema(schema_dict):
        # dict is an openapi schema, it may or may not be dereferenced.
        if timestamp is None:
            timestamp_int = None
        else:
            timestamp_int = timestamp.timestamp_nanos()
        if is_raw_schema(schema_dict):
            return EsiSchema.from_raw_schema(
                raw_schema=schema_dict,
                timestamp=timestamp_int,
            )
        else:
            return EsiSchemaRoot.model_validate({
                "dereferenced_schema": schema_dict,
                "timestamp": timestamp_int,
            }).root
    if is_esi_schema_td(schema_dict):
        # EsiSchemaTD is expected to be dereferenced, so we can just pass it through.
        return EsiSchemaRoot.model_validate(schema_dict).root
    if is_timestamped_schema(schema_dict):
        # TimestampedSchema is expected not to be dereferenced.
        return EsiSchema.from_raw_schema(
            raw_schema=schema_dict["schema"],
            timestamp=schema_dict["timestamp"],
        )

    raise ValueError(
        f"Invalid schema format. The loaded schema must be an OpenAPI schema, an EsiSchemaTD dictionary, or a timestamped schema. top-level keys were {', '.join(schema_dict.keys())}"
    )


def load_esi_schema_from_file(
    file_path: Path, timestamp: Instant | None = None
) -> EsiSchema:
    """Load the ESI schema from a JSON file.

    Args:
        file_path: The path to the JSON file containing the ESI schema.
        timestamp: The timestamp associated with the schema, representing the timestamp when the
            schema was fetched as an Instant. This field is optional and can be None if the
            timestamp is not available or not applicable.

    Returns:
        An instance of EsiSchema containing the loaded schema and its associated timestamp.
    """
    loaded_schema = json_io.json_load_path(file_path)

    return load_esi_schema(loaded_schema, timestamp=timestamp)


def default_file_name_for_cached_schema(schema: EsiSchema) -> str:
    """Generate a default file name for the given ESI schema.

    Args:
        schema: An instance of EsiSchema.

    Returns:
        Canonical filename in the form
        ``schema_<compatibility_date>_<timestamp>_esi_schema.json``.
    """
    return f"schema_{schema.compatibility_date}_{schema.timestamp}_esi_schema.json"
