"""Helpers for checking if a schema is a raw schema or not."""

from typing import Any


def is_raw_schema(schema: dict[str, Any]) -> bool:
    """Check if the object is a raw schema dictionary.

    Looks for the presence of a "$ref" key in the schema or its nested dictionaries,
    which indicates that it is a raw schema.
    """

    # check to see if the is a $ref key in the schema sub dicts, if so it is a raw schema
    def has_ref(d: dict[str, Any]) -> bool:
        if "$ref" in d:
            return True
        for v in d.values():
            if isinstance(v, dict) and has_ref(v):  # type: ignore
                return True
            elif isinstance(v, list):
                for item in v:  # type: ignore
                    if isinstance(item, dict) and has_ref(item):  # type: ignore
                        return True
        return False

    return has_ref(schema)


def is_open_api_schema(schema: dict[str, Any]) -> bool:
    """Check if the object is an OpenAPI schema dictionary.

    Looks for the presence of the keys "openapi", "info", "paths", and "components" in the schema,
    which indicates that it is an OpenAPI schema.
    """
    # check for a number of keys in the top level of the dictionary to determine if it is an OpenAPI schema
    openapi_keys = {"openapi", "info", "paths", "components"}
    return openapi_keys.issubset(schema.keys())


def is_esi_schema_td(schema: dict[str, Any]) -> bool:
    """Check if the object is an EsiSchemaTD dictionary.

    Looks for the presence of the keys "dereferenced_schema" and "timestamp" in the schema,
    which indicates that it is an EsiSchemaTD dictionary.
    """
    esi_schema_td_keys = {"dereferenced_schema", "timestamp"}
    return esi_schema_td_keys == set(schema.keys())


def is_timestamped_schema(schema: dict[str, Any]) -> bool:
    """Check if the object is a TimestampedSchema dictionary.

    Looks for the presence of the keys "schema" and "timestamp" in the schema,
    which indicates that it is a TimestampedSchema dictionary.
    """
    timestamped_schema_keys = {"schema", "timestamp"}
    return timestamped_schema_keys == set(schema.keys())
