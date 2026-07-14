"""Helpers for loading ESI schemas from files."""

from pathlib import Path
from typing import Any

from whenever import Instant

from eve_esi_link.helpers import json_io
from eve_esi_link.schema.helpers.schema_check import (
    is_esi_schema_td,
    is_open_api_schema,
    is_raw_schema,
    is_timestamped_schema,
)
from eve_esi_link.schema.models import EsiSchema, EsiSchemaRoot


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
        An instance of EsiSchema containing the loaded schema and its associated timestamp.
    """
    if is_open_api_schema(schema_dict):
        if timestamp is None:
            timestamp_int = None
        else:
            timestamp_int = timestamp.timestamp_nanos()
        if is_raw_schema(schema_dict):
            return EsiSchemaRoot.model_validate({
                "dereferenced_schema": schema_dict,
                "timestamp": timestamp_int,
            }).root
        else:
            return EsiSchemaRoot.model_validate({
                "dereferenced_schema": schema_dict,
                "timestamp": timestamp_int,
            }).root
    if is_esi_schema_td(schema_dict):
        return EsiSchemaRoot.model_validate(schema_dict).root
    if is_timestamped_schema(schema_dict):
        return EsiSchema.from_raw_schema(
            raw_schema=schema_dict["schema"],
            timestamp=schema_dict["timestamp"],
        )

    raise ValueError(
        "Invalid schema format. The loaded schema must be an OpenAPI schema or an EsiSchemaTD dictionary."
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
