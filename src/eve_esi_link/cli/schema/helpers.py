"""Helpers for schema CLI commands."""

import json
from enum import StrEnum
from typing import Any

from eve_esi_link.schema.models import (
    EsiSchema,
    TimestampedDereferencedSchema,
    TimestampedDereferencedSchemaRoot,
    TimestampedSchema,
    TimestampedSchemaRoot,
)


class SchemaIOFormat(StrEnum):
    """Enum for input/output format options."""

    BARE = "bare"
    TIMESTAMPED_BARE = "timestamped_bare"
    DEREFERENCED = "dereferenced"
    TIMESTAMPED_DEREFERENCED = "timestamped_dereferenced"


def serialize_schema(
    schema: TimestampedSchema | TimestampedDereferencedSchema | dict[str, Any],
) -> str:
    """Serialize the schema to a JSON string based on the specified format."""
    match schema:
        case TimestampedSchema():
            return TimestampedSchemaRoot(root=schema).model_dump_json(indent=2)
        case TimestampedDereferencedSchema():
            return TimestampedDereferencedSchemaRoot(root=schema).model_dump_json(
                indent=2
            )
        case dict():
            return json.dumps(schema, indent=2)


def deserialize_schema(
    json_str: str, format: SchemaIOFormat
) -> TimestampedSchema | TimestampedDereferencedSchema | dict[str, Any]:
    """Deserialize a JSON string into the appropriate schema object based on the specified format."""
    match format:
        case SchemaIOFormat.BARE:
            return json.loads(json_str)
        case SchemaIOFormat.TIMESTAMPED_BARE:
            return TimestampedSchemaRoot.model_validate_json(json_str).root
        case SchemaIOFormat.DEREFERENCED:
            return json.loads(json_str)
        case SchemaIOFormat.TIMESTAMPED_DEREFERENCED:
            return TimestampedDereferencedSchemaRoot.model_validate_json(json_str).root


def is_raw_schema(schema: dict[str, Any]) -> bool:
    """Check if the object is a raw schema dictionary."""

    # check to see if the is a $ref key in the schema sub dicts, if so it is a raw schema
    def has_ref(d: dict[str, Any]) -> bool:
        if "$ref" in d:
            return True
        for v in d.values():
            if isinstance(v, dict) and has_ref(v):
                return True
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict) and has_ref(item):
                        return True
        return False

    return has_ref(schema)


def get_esi_schema(
    input_schema: TimestampedSchema | TimestampedDereferencedSchema | dict[str, Any],
) -> EsiSchema:
    """Convert the input schema to an EsiSchema object."""
    match input_schema:
        case TimestampedSchema():
            return EsiSchema.from_raw_schema(
                raw_schema=input_schema.schema, timestamp=input_schema.timestamp
            )
        case TimestampedDereferencedSchema():
            return EsiSchema(
                dereferenced_schema=input_schema.dereferenced_schema,
                timestamp=input_schema.timestamp,
            )
        case dict():
            if is_raw_schema(input_schema):
                return EsiSchema.from_raw_schema(
                    raw_schema=input_schema, timestamp=None
                )
            if not is_raw_schema(input_schema):
                return EsiSchema(dereferenced_schema=input_schema, timestamp=None)
        case _:
            raise ValueError(
                "Invalid input schema type. Must be TimestampedSchema, TimestampedDereferencedSchema, or a raw schema dictionary."
            )
    raise ValueError(
        "Invalid input schema type. Must be TimestampedSchema, TimestampedDereferencedSchema, or a raw schema dictionary."
    )
