"""Validate user-supplied ESI requests against schema-defined operation rules."""

# pyright: standard
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from ..language import LangEnum
from ..schema.models import EsiSchema, SchemaOperation
from .models import EsiRequest

logger = logging.getLogger(__name__)


class EsiRequestValidationError(Exception):
    """Base class for ESI request validation errors."""


@dataclass(slots=True)
class _ParameterSpec:
    """Normalized OpenAPI parameter details used by request validation."""

    location: str
    required: bool
    schema: dict[str, Any]


class EsiRequestValidationErrors(EsiRequestValidationError):
    """Aggregate ESI request validation errors into a single exception."""

    def __init__(self, errors: list[str]) -> None:
        """Create an aggregate validation error from collected messages.

        Args:
            errors: Collected validation error messages.
        """
        self.errors = errors
        message = "\n".join(f"- {error}" for error in errors)
        super().__init__(
            f"ESI request validation failed with {len(errors)} error(s):\n{message}"
        )


_RUNTIME_FORBIDDEN_HEADERS = frozenset({"If-None-Match", "If-Modified-Since"})
_VALID_ACCEPT_LANGUAGES = frozenset(lang.value for lang in LangEnum)


def _add_error(errors: list[str], operation_id: str, message: str) -> None:
    """Append a consistently formatted validation message."""
    errors.append(f"operation_id={operation_id}: {message}")


def _resolve_operation(
    esi_request: EsiRequest,
    esi_schema: EsiSchema,
    errors: list[str],
) -> SchemaOperation | None:
    """Resolve the request operation from the schema."""
    operation = esi_schema.operations.get(esi_request.operation_id)
    if operation is None:
        _add_error(
            errors,
            esi_request.operation_id,
            "Unknown operation_id for provided schema.",
        )
    return operation


def _normalize_parameter_specs(
    parameters: list[dict[str, Any]],
) -> dict[str, _ParameterSpec]:
    """Convert OpenAPI parameter definitions into a name-keyed map."""
    result: dict[str, _ParameterSpec] = {}
    for parameter in parameters:
        name = parameter.get("name")
        if not isinstance(name, str) or not name:
            continue
        schema = parameter.get("schema", {})
        result[name] = _ParameterSpec(
            location=str(parameter.get("in", "")),
            required=bool(parameter.get("required", False)),
            schema=schema if isinstance(schema, dict) else {},
        )
    return result


def _is_openapi_type(value: Any, schema_type: str) -> bool:
    """Return whether a runtime value matches an OpenAPI primitive/container type."""
    match schema_type:
        case "string":
            return isinstance(value, str)
        case "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        case "number":
            return (isinstance(value, int | float)) and not isinstance(value, bool)
        case "boolean":
            return isinstance(value, bool)
        case "object":
            return isinstance(value, dict)
        case "array":
            return isinstance(value, list)
        case "null":
            return value is None
        case _:
            return False


def _validate_primitive_value(
    value: Any,
    schema: dict[str, Any],
    *,
    field_label: str,
    operation_id: str,
    errors: list[str],
) -> None:
    """Validate a value against simple schema constraints used for request params."""
    schema_type = schema.get("type")
    nullable = bool(schema.get("nullable", False))
    if value is None:
        if nullable:
            return
        _add_error(errors, operation_id, f"{field_label} cannot be null.")
        return
    if not isinstance(schema_type, str):
        _add_error(
            errors, operation_id, f"{field_label} has unsupported schema type metadata."
        )
        return
    if not _is_openapi_type(value, schema_type):
        _add_error(
            errors,
            operation_id,
            f"{field_label} expected type '{schema_type}', got '{type(value).__name__}'.",
        )
        return
    allowed_values = schema.get("enum")
    if isinstance(allowed_values, list) and value not in allowed_values:
        _add_error(
            errors,
            operation_id,
            f"{field_label} value '{value}' is not in allowed enum values.",
        )


def _validate_parameters_by_location(
    values: dict[str, Any],
    specs: dict[str, _ParameterSpec],
    *,
    location: str,
    operation_id: str,
    errors: list[str],
) -> None:
    """Validate path or query parameters using normalized specs."""
    supplied_names = set(values)
    allowed_names = set(specs)
    for unknown_name in sorted(supplied_names - allowed_names):
        _add_error(
            errors,
            operation_id,
            f"Unknown {location} parameter '{unknown_name}'.",
        )

    required_names = {name for name, spec in specs.items() if spec.required}
    for missing_name in sorted(required_names - supplied_names):
        _add_error(
            errors,
            operation_id,
            f"Missing required {location} parameter '{missing_name}'.",
        )

    for name, value in values.items():
        spec = specs.get(name)
        if spec is None:
            continue
        _validate_primitive_value(
            value,
            spec.schema,
            field_label=f"{location} parameter '{name}'",
            operation_id=operation_id,
            errors=errors,
        )


def _validate_query_parameters(
    esi_request: EsiRequest,
    operation: SchemaOperation,
    errors: list[str],
) -> None:
    """Validate query parameters including pagination constraints."""
    if "page" in esi_request.query_parameters:
        _add_error(
            errors,
            operation.operation_id,
            "Query parameter 'page' must not be set; pagination is handled at runtime.",
        )
    query_specs = _normalize_parameter_specs(operation.query_parameters)
    _validate_parameters_by_location(
        esi_request.query_parameters,
        query_specs,
        location="query",
        operation_id=operation.operation_id,
        errors=errors,
    )


def _validate_headers(
    esi_request: EsiRequest,
    operation: SchemaOperation,
    errors: list[str],
) -> None:
    """Validate user-supplied headers against operation and runtime policy."""
    header_specs = _normalize_parameter_specs(operation.header_params)
    allowed_header_names = set(header_specs)

    for name, value in esi_request.header_parameters.items():
        if name in _RUNTIME_FORBIDDEN_HEADERS:
            _add_error(
                errors,
                operation.operation_id,
                f"Header '{name}' is runtime-managed and must not be user-supplied.",
            )
            continue
        if name not in allowed_header_names:
            _add_error(
                errors,
                operation.operation_id,
                f"Header '{name}' is not allowed for this operation.",
            )
            continue
        if not isinstance(value, str):
            _add_error(
                errors,
                operation.operation_id,
                f"Header '{name}' must be a string.",
            )

    accept_language = esi_request.header_parameters.get("Accept-Language")
    if accept_language is not None and accept_language not in _VALID_ACCEPT_LANGUAGES:
        _add_error(
            errors,
            operation.operation_id,
            "Header 'Accept-Language' must be one of the supported language codes.",
        )


def _validate_authorization(
    esi_request: EsiRequest,
    operation: SchemaOperation,
    *,
    errors: list[str],
) -> None:
    """Validate authorization presence."""
    if not operation.is_authentication_required:
        if esi_request.character_id is not None:
            _add_error(
                errors,
                operation.operation_id,
                "Authorization must be None for operations that do not require authentication.",
            )
            return
        if esi_request.credential_id is not None:
            _add_error(
                errors,
                operation.operation_id,
                "Authorization must be None for operations that do not require authentication.",
            )
            return

    if not isinstance(esi_request.character_id, int) or isinstance(
        esi_request.character_id, bool
    ):
        _add_error(
            errors,
            operation.operation_id,
            "Authorization.character_id must be an integer.",
        )
    if not isinstance(esi_request.credential_id, UUID):
        _add_error(
            errors,
            operation.operation_id,
            "Authorization.credential_id must be a UUID.",
        )


def _validate_json_schema_subset(
    value: Any,
    schema: dict[str, Any],
    *,
    path: str,
    operation_id: str,
    errors: list[str],
) -> None:
    """Validate JSON data with a supported subset of OpenAPI schema keywords."""
    unsupported_keywords = [
        keyword
        for keyword in ("$ref", "oneOf", "allOf", "anyOf", "not")
        if keyword in schema
    ]
    if unsupported_keywords:
        _add_error(
            errors,
            operation_id,
            f"{path} schema uses unsupported keyword(s): {', '.join(unsupported_keywords)}.",
        )
        return

    schema_type = schema.get("type")
    nullable = bool(schema.get("nullable", False))
    if value is None:
        if nullable:
            return
        _add_error(errors, operation_id, f"{path} cannot be null.")
        return

    if not isinstance(schema_type, str):
        _add_error(
            errors, operation_id, f"{path} schema is missing supported 'type' metadata."
        )
        return
    if not _is_openapi_type(value, schema_type):
        _add_error(
            errors,
            operation_id,
            f"{path} expected type '{schema_type}', got '{type(value).__name__}'.",
        )
        return

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        _add_error(
            errors,
            operation_id,
            f"{path} value '{value}' is not in allowed enum values.",
        )
        return

    if schema_type == "object":
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            _add_error(
                errors, operation_id, f"{path} object schema has invalid 'properties'."
            )
            return
        required_keys = schema.get("required", [])
        if not isinstance(required_keys, list):
            _add_error(
                errors, operation_id, f"{path} object schema has invalid 'required'."
            )
            return

        assert isinstance(value, dict)
        for required_key in required_keys:
            if isinstance(required_key, str) and required_key not in value:
                _add_error(errors, operation_id, f"{path}.{required_key} is required.")

        for key, item_value in value.items():
            if key in properties:
                item_schema = properties[key]
                if not isinstance(item_schema, dict):
                    _add_error(
                        errors,
                        operation_id,
                        f"{path}.{key} schema metadata is invalid.",
                    )
                    continue
                _validate_json_schema_subset(
                    item_value,
                    item_schema,
                    path=f"{path}.{key}",
                    operation_id=operation_id,
                    errors=errors,
                )
                continue

            additional = schema.get("additionalProperties", True)
            if additional is False:
                _add_error(
                    errors, operation_id, f"{path}.{key} is not an allowed property."
                )
            elif isinstance(additional, dict):
                _validate_json_schema_subset(
                    item_value,
                    additional,
                    path=f"{path}.{key}",
                    operation_id=operation_id,
                    errors=errors,
                )
        return

    if schema_type == "array":
        items_schema = schema.get("items")
        if not isinstance(items_schema, dict):
            _add_error(
                errors, operation_id, f"{path} array schema has invalid 'items'."
            )
            return
        assert isinstance(value, list)
        for index, item in enumerate(value):
            _validate_json_schema_subset(
                item,
                items_schema,
                path=f"{path}[{index}]",
                operation_id=operation_id,
                errors=errors,
            )


def _validate_request_body(
    esi_request: EsiRequest,
    operation: SchemaOperation,
    errors: list[str],
) -> None:
    """Validate json_body against the operation requestBody schema."""
    request_body_schema = operation.request_body
    if request_body_schema is None:
        if esi_request.json_payload is not None:
            _add_error(
                errors,
                operation.operation_id,
                "json_body is not allowed for this operation.",
            )
        return

    required = bool(request_body_schema.get("required", False))
    if required and esi_request.json_payload is None:
        _add_error(
            errors,
            operation.operation_id,
            "json_body is required for this operation.",
        )
        return
    if esi_request.json_payload is None:
        return

    content = request_body_schema.get("content", {})
    if not isinstance(content, dict):
        _add_error(
            errors,
            operation.operation_id,
            "requestBody schema content metadata is invalid.",
        )
        return
    application_json = content.get("application/json")
    if not isinstance(application_json, dict):
        _add_error(
            errors,
            operation.operation_id,
            "Only application/json request bodies are currently supported for validation.",
        )
        return
    body_schema = application_json.get("schema")
    if not isinstance(body_schema, dict):
        _add_error(
            errors,
            operation.operation_id,
            "requestBody application/json schema metadata is invalid.",
        )
        return

    _validate_json_schema_subset(
        esi_request.json_payload,
        body_schema,
        path="json_body",
        operation_id=operation.operation_id,
        errors=errors,
    )


def validate_esi_request(
    esi_request: EsiRequest,
    esi_schema: EsiSchema,
) -> None:
    """Validate an ESI request against schema constraints.

    Args:
        esi_request: User-supplied request object to validate.
        esi_schema: Resolved ESI schema used for validation rules.

    Raises:
        EsiRequestValidationErrors: If one or more validation checks fail.
    """
    logger.debug(
        "Validating ESI request operation_id=%s",
        esi_request.operation_id,
    )
    errors: list[str] = []
    operation = _resolve_operation(esi_request, esi_schema, errors)
    if operation is None:
        logger.warning("ESI request validation failed: %s", errors)
        raise EsiRequestValidationErrors(errors)

    path_specs = _normalize_parameter_specs(operation.path_parameters)
    _validate_parameters_by_location(
        esi_request.path_parameters,
        path_specs,
        location="path",
        operation_id=operation.operation_id,
        errors=errors,
    )
    _validate_query_parameters(esi_request, operation, errors)
    _validate_headers(esi_request, operation, errors)
    _validate_authorization(
        esi_request,
        operation,
        errors=errors,
    )
    _validate_request_body(esi_request, operation, errors)

    if errors:
        logger.warning(
            "ESI request validation failed operation_id=%s error_count=%d",
            operation.operation_id,
            len(errors),
        )
        raise EsiRequestValidationErrors(errors)
    logger.debug(
        "ESI request validation succeeded operation_id=%s", operation.operation_id
    )
