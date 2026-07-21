"""Generate markdown documentation for ESI schemas.

The renderer focuses on operations and produces a structured markdown document with:
- metadata header
- table of contents grouped by tag
- per-tag and per-operation sections
- summary and parameter tables
- fenced JSON or YAML blocks for request/response/extension schemas
"""

import json
import re
from collections import defaultdict
from enum import StrEnum
from typing import Any

from mdformat import text as mdformat_text  # type: ignore
from pfmsoft.eve_snippets.markdown.markdown_table import Align, MarkdownTable
from whenever import Instant
from yaml import safe_dump

from .models import EsiSchema, SchemaOperation


class FencedDataFormat(StrEnum):
    """Supported fenced data serialization formats."""

    JSON = "json"
    YAML = "yaml"


def _resolve_download_date(
    schema: EsiSchema,
    explicit_download_date: Instant | None,
) -> Instant | None:
    """Resolve download date from explicit argument or schema timestamp."""
    if explicit_download_date is not None:
        return explicit_download_date
    if schema.timestamp is None:
        return None
    return Instant.from_timestamp_nanos(schema.timestamp)


def _slugify_heading(value: str) -> str:
    """Create predictable markdown heading anchors.

    Args:
            value: Heading content.

    Returns:
            A slug suitable for markdown anchor links.
    """
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9\s-]", "", normalized)
    normalized = re.sub(r"[\s-]+", "-", normalized)
    return normalized.strip("-")


def _render_fenced_block(data: Any, *, format: FencedDataFormat) -> str:
    """Render a value inside a markdown fenced code block."""
    if format is FencedDataFormat.JSON:
        body = json.dumps(data, indent=2, sort_keys=False)
        return f"```json\n{body}\n```"
    body = safe_dump(data, sort_keys=False, indent=2).rstrip()
    return f"```yaml\n{body}\n```"


def _group_operations_by_tag(
    operations: dict[str, SchemaOperation],
) -> dict[str, list[SchemaOperation]]:
    """Group operations by tag, preserving deterministic sorting.

    Operations without tags are grouped under "untagged".
    """
    grouped: dict[str, list[SchemaOperation]] = defaultdict(list)
    for operation in operations.values():
        tags = operation.tags or ["untagged"]
        for tag in tags:
            grouped[tag].append(operation)
    return {
        tag: sorted(ops, key=lambda item: item.operation_id)
        for tag, ops in sorted(grouped.items(), key=lambda item: item[0])
    }


def _render_summary_table(operation: SchemaOperation) -> str:
    """Render a compact summary table for a single operation."""
    response_keys = (
        ", ".join(operation.response_keys) if operation.response_keys else "-"
    )
    try:
        compatibility_date = operation.compatibility_date
    except ValueError:
        compatibility_date = "-"
    table = MarkdownTable(
        headers=["Field", "Value"],
        align=[Align.LEFT, Align.LEFT],
    )
    table.add_row(["Operation ID", operation.operation_id])
    table.add_row(["Method", str(operation.method)])
    table.add_row(["Path", operation.path])
    table.add_row([
        "Authorization Required",
        "Yes" if operation.is_authentication_required else "No",
    ])
    table.add_row(["Compatibility Date", compatibility_date])
    table.add_row(["Response Keys", response_keys])
    table.add_row(["Summary", operation.summary or "-"])
    return table.render()


def _parameter_type(parameter: dict[str, Any]) -> str:
    """Extract parameter type for table display."""
    schema = parameter.get("schema", {})
    return str(schema.get("type", "-"))


def _render_parameters_table(operation: SchemaOperation) -> str:
    """Render path/query/header parameter documentation table."""
    parameters = [
        *operation.path_and_query_parameters,
        *operation.header_params,
    ]
    if not parameters:
        return "No path/query/header parameters."

    table = MarkdownTable(
        headers=["Name", "In", "Required", "Type", "Description"],
        align=[Align.LEFT, Align.LEFT, Align.LEFT, Align.LEFT, Align.LEFT],
    )
    for parameter in parameters:
        table.add_row([
            parameter.get("name", "-"),
            parameter.get("in", "-"),
            "Yes" if parameter.get("required", False) else "No",
            _parameter_type(parameter),
            parameter.get("description", "-").replace("\n", " "),
        ])
    return table.render()


def _render_operation_section(
    operation: SchemaOperation,
    *,
    fenced_format: FencedDataFormat,
) -> str:
    """Render markdown for a single operation."""
    lines: list[str] = [
        f"### {operation.operation_id}",
        "",
        "#### Summary",
        "",
        _render_summary_table(operation),
        "",
        "#### Description",
        "",
        operation.description.replace("\n", " ") or "No description.",
        "",
        "#### Parameters",
        "",
        _render_parameters_table(operation),
        "",
        "#### Request Body (json_payload) Schema",
        "",
    ]
    if operation.request_body is None:
        lines.append("No Request Body Schema.")
    else:
        lines.append(_render_fenced_block(operation.request_body, format=fenced_format))
    lines.extend(["", "#### Response Schema", ""])
    if operation.responses_200:
        lines.append(
            _render_fenced_block(operation.responses_200, format=fenced_format)
        )
    else:
        lines.append("No 200 application/json response schema.")

    if operation.x_values:
        lines.extend(["", "#### Extensions", ""])
        extension_dict: dict[str, Any] = {}
        for entry in operation.x_values:
            extension_dict.update(entry)
        lines.append(_render_fenced_block(extension_dict, format=fenced_format))
    lines.append("")
    return "\n".join(lines)


def _render_toc(grouped_operations: dict[str, list[SchemaOperation]]) -> str:
    """Render table of contents with tag and operation links."""
    lines = ["## Table of Contents", ""]
    for tag, operations in grouped_operations.items():
        lines.append(f"- [{tag}](#{_slugify_heading(f'Tag: {tag}')})")
        for operation in operations:
            lines.append(
                f"  - [{operation.operation_id}](#{_slugify_heading(operation.operation_id)})"
            )
    lines.append("")
    return "\n".join(lines)


def generate_esi_schema_markdown_doc(
    schema: EsiSchema,
    *,
    download_date: Instant | None = None,
    fenced_format: FencedDataFormat = FencedDataFormat.JSON,
) -> str:
    """Generate operation-focused markdown documentation for an ESI schema.

    Args:
        schema: ESI schema model.
        download_date: Optional explicit date when schema was downloaded.
            If omitted, schema.timestamp is used when available.
        fenced_format: Serialization format for fenced blocks.

    Returns:
            Rendered and mdformat-normalized markdown document.
    """
    grouped_operations = _group_operations_by_tag(schema.operations)
    resolved_download_date = _resolve_download_date(schema, download_date)

    lines: list[str] = [
        "# ESI Schema Documentation",
        "",
        "Version",
        f": {schema.version}",
        "",
        "Download Date",
        f": {resolved_download_date.format_iso() if resolved_download_date else 'Unknown'}",
        "",
        f"Server URL: {schema.base_url}",
        "",
        _render_toc(grouped_operations),
    ]

    for tag, operations in grouped_operations.items():
        lines.extend([f"## Tag: {tag}", ""])
        for operation in operations:
            lines.append(
                _render_operation_section(operation, fenced_format=fenced_format)
            )

    return mdformat_text("\n".join(lines), extensions=["tables"])
