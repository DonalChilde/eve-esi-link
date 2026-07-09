"""Module for representing the ESI OpenAPI schema and its operations in a structured way."""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Self, cast

from ..helpers.resolve_json_ref import resolve_internal_refs


@dataclass(slots=True, kw_only=True, frozen=True)
class TimestampedSchema:
    """Represents a schema with an associated timestamp."""

    schema: dict[str, Any]
    """The downloaded schema data as a dictionary, typically representing the OpenAPI 
        schema fetched from the ESI API."""
    timestamp: int
    """The timestamp associated with the schema, representing the timestamp when the 
        schema was fetched in nanoseconds."""


@dataclass(slots=True, kw_only=True, frozen=True)
class TimestampedDereferencedSchema:
    """Represents a dereferenced schema with an associated timestamp."""

    dereferenced_schema: dict[str, Any]
    """The dereferenced schema data as a dictionary, typically representing the 
        OpenAPI schema fetched from the ESI API."""
    timestamp: int
    """The timestamp associated with the dereferenced schema, representing the 
        timestamp when the schema was fetched in nanoseconds."""

    @classmethod
    def from_timestamped_schema(cls, timestamped_schema: TimestampedSchema) -> Self:
        """Create a TimestampedDereferencedSchema from a TimestampedSchema.

        This method dereferences the schema contained in the TimestampedSchema and
        returns a new instance of TimestampedDereferencedSchema with the dereferenced
        schema and the same timestamp.

        Args:
            timestamped_schema (TimestampedSchema): The input TimestampedSchema to be
                dereferenced.

        Returns:
            TimestampedDereferencedSchema: A new instance containing the dereferenced
                schema and the original timestamp.
        """
        dereferenced_schema = resolve_internal_refs(
            timestamped_schema.schema, timestamped_schema.schema
        )
        return cls(
            dereferenced_schema=dereferenced_schema,
            timestamp=timestamped_schema.timestamp,
        )


@dataclass(slots=True, kw_only=True, frozen=True)
class TimestampedCompatibilityDates:
    """Represents a list of compatibility dates with an associated timestamp."""

    dates: tuple[str, ...]
    """The tuple of compatibility dates, typically fetched from the ESI API."""
    timestamp: int
    """The timestamp associated with the compatibility dates, representing the 
        timestamp when the dates were fetched in nanoseconds."""


class HttpMethod(StrEnum):
    """Enumeration of HTTP methods used in the ESI OpenAPI schema."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass(slots=True, kw_only=True, frozen=True)
class SchemaOperation:
    """Represents an operation defined in the ESI OpenAPI schema.

    This class is used to store the details of an operation, including the path, method,
    operation ID, and the full operation schema. This allows for easy access to the
    details of each operation when generating documentation or validating requests.

    A flattened version of the path, method, and operation object from the OpenAPI schema.
    "paths":<path>:<method>:<operation_schema> from the OpenAPI schema.
    """

    path: str
    method: HttpMethod
    operation_schema: dict[str, Any]

    @property
    def operation_id(self) -> str:
        """Extract the operation ID from the operation object."""
        return self.operation_schema.get("operationId", "")

    @property
    def tags(self) -> list[str]:
        """Extract the tags from the operation object, if present."""
        return [tag for tag in self.operation_schema.get("tags", [])]

    @property
    def description(self) -> str:
        """Extract the description from the operation object, if present."""
        return self.operation_schema.get("description", "")

    @property
    def path_and_query_parameters(self) -> list[dict[str, Any]]:
        """Extract all parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") in {"path", "query"}
        ]

    @property
    def path_parameters(self) -> list[dict[str, Any]]:
        """Extract the path parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") == "path"
        ]

    @property
    def query_parameters(self) -> list[dict[str, Any]]:
        """Extract the query parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") == "query"
        ]

    @property
    def header_params(self) -> list[dict[str, Any]]:
        """Extract the header parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") == "header"
        ]

    @property
    def responses_200(self) -> dict[str, Any]:
        """Extract the response schema from the operation object, if present."""
        success_responses = (
            self.operation_schema
            .get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        return deepcopy(success_responses)

    @property
    def request_body(self) -> dict[str, Any] | None:
        """Extract the request body from the operation object, if present."""
        return deepcopy(self.operation_schema.get("requestBody"))

    @property
    def is_authentication_required(self) -> bool:
        """Determine if the operation requires authentication based on the presence of security requirements."""
        return "security" in self.operation_schema and bool(
            self.operation_schema["security"]
        )

    @property
    def is_paged(self) -> bool:
        """Determine if the operation is paged based on the presence of pagination-related parameters."""
        for param in self.query_parameters:
            if param.get("name") in {"page"}:
                return True
        return False

    @property
    def is_cached(self) -> bool:
        """Determine if the operation is cacheable."""
        if self.method in {"GET", "get"}:
            return True
        return False

    @property
    def summary(self) -> str | None:
        """Extract the summary from the operation object, if present."""
        return self.operation_schema.get("summary")

    @property
    def x_compatibility_date(self) -> str:
        """Extract the x-compatibility-date from the operation object, if present."""
        value = self.operation_schema.get("x-compatibility-date")
        if value is None:
            raise ValueError(
                f"Operation {self.operation_id} is missing required x-compatibility-date field."
            )
        return value

    @property
    def x_values(self) -> list[dict[str, Any]]:
        """Extract the x-values from the operation object, if present."""
        x_list: list[dict[str, Any]] = []
        for key, value in self.operation_schema.items():
            if key.startswith("x-"):
                x_list.append({key: deepcopy(value)})
        return x_list


@dataclass(slots=True, kw_only=True)
class EsiSchema:
    """Represents the ESI OpenAPI schema and its associated metadata.

    For ease of access to the details of the schema.
    """

    dereferenced_schema: dict[str, Any]
    _schema_operations: dict[str, SchemaOperation] = field(
        default_factory=dict[str, SchemaOperation], init=False, repr=False
    )
    _operations_id_by_tag: dict[str, list[str]] = field(
        default_factory=dict[str, list[str]], init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Ensure that the schema is valid."""
        if "openapi" not in self.dereferenced_schema:
            raise ValueError("Invalid schema: missing 'openapi' field")
        # fill the schema operations dictionary
        self._build_schema_operations()
        self._build_operation_id_by_tag()

    def _build_schema_operations(self) -> None:
        """Build the schema operations dictionary from the dereferenced schema."""
        paths = self.dereferenced_schema.get("paths", {})
        for path, methods in paths.items():
            for method, operation in methods.items():
                operation_id = operation.get("operationId")
                if operation_id:
                    self._schema_operations[operation_id] = SchemaOperation(
                        path=path,
                        method=HttpMethod(method.upper()),
                        operation_schema=deepcopy(operation),
                    )

    def _build_operation_id_by_tag(self) -> None:
        """Build the operation ID by tag mapping from the schema operations."""
        if not self._schema_operations:
            raise ValueError(
                "Schema operations must be built before building operation ID by tag mapping."
            )
        tag_mapping: dict[str, list[str]] = {}
        for operation in self._schema_operations.values():
            for tag in operation.tags:
                if tag not in tag_mapping:
                    tag_mapping[tag] = []
                tag_mapping[tag].append(operation.operation_id)
        # sort the tags alphabetically, and the operation IDs within each tag alphabetically as well
        self._operations_id_by_tag = {
            tag: sorted(operation_ids)
            for tag, operation_ids in sorted(tag_mapping.items())
        }

    @classmethod
    def from_raw_schema(cls, raw_schema: dict[str, Any]) -> Self:
        """Factory method to create an EsiSchema instance from a raw OpenAPI schema.

        This method will resolve all internal JSON references in the schema, so that
        the resulting EsiSchema instance contains a fully dereferenced schema for easy
        access to all the details of the operations defined in the schema.

        Args:
            raw_schema: The raw OpenAPI schema as a dictionary.

        Returns:
            An instance of EsiSchema with the dereferenced schema.
        """
        dereferenced_schema = resolve_internal_refs(raw_schema, raw_schema)
        return cls(dereferenced_schema=dereferenced_schema)

    @property
    def operations(self) -> dict[str, SchemaOperation]:
        """Get a dictionary of all operations in the schema, keyed by operation ID."""
        return self._schema_operations

    @property
    def operations_id_by_tag(self) -> dict[str, list[str]]:
        """Get a dictionary mapping tags to lists of operation IDs."""
        return self._operations_id_by_tag

    @property
    def compatibility_date(self) -> str:
        """Get the compatibility date of the ESI schema from the info section."""
        return self.version

    @property
    def version(self) -> str:
        """Get the version of the ESI schema based on the compatibility date."""
        version = cast(str, self.dereferenced_schema["info"]["version"])
        return version

    @property
    def base_url(self) -> str:
        """Get the base URL for the ESI API from the servers section of the schema."""
        return self.dereferenced_schema["servers"][0]["url"]

    @property
    def content_languages(self) -> set[str]:
        """Get the content languages supported by the ESI API from the schema."""
        return set(
            self.dereferenced_schema
            .get("components", {})
            .get("headers", {})
            .get("ContentLanguage", {})
            .get("schema", {})
            .get("enum", [])
        )
