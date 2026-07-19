"""Helpers for building GitHub-Flavored Markdown tables.

Provides MarkdownTable, a small dataclass-based builder that handles
column alignment, width padding, pipe escaping, configurable newline
replacement, and rendering rows supplied either positionally or as
mappings keyed by header name.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Align(Enum):
    """Supported column alignments for rendered markdown tables."""

    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"


def _escape(text: str, newline_replacement: str) -> str:
    """Escape characters that would break markdown table syntax.

    Args:
        text: Raw cell text to escape.
        newline_replacement: String substituted for any newline character,
            since a literal newline cannot appear inside a table cell.

    Returns:
        The escaped text, safe to place inside a single table cell.
    """
    return text.replace("|", "\\|").replace("\n", newline_replacement)


def _format_cell(value: Any, newline_replacement: str) -> str:
    """Convert an arbitrary cell value into an escaped display string.

    Args:
        value: The raw cell value. None renders as an empty string;
            any other value is converted via str().
        newline_replacement: String substituted for any newline character
            in the stringified value.

    Returns:
        The escaped, display-ready string for the cell.
    """
    if value is None:
        return ""
    return _escape(str(value), newline_replacement)


def _separator_cell(width: int, align: Align) -> str:
    """Build a single cell of the header/body separator row.

    Args:
        width: The column's rendered width in characters.
        align: The column's alignment, which determines colon placement.

    Returns:
        A dash-and-colon string per markdown alignment syntax (e.g.
        ":---:" for center), at least 3 characters wide to satisfy
        markdown table conventions.
    """
    # width is the number of visible dashes/colons in the cell, min 3 per markdown convention
    width = max(width, 3)
    if align is Align.CENTER:
        return ":" + "-" * (width - 2) + ":"
    if align is Align.RIGHT:
        return "-" * (width - 1) + ":"
    return "-" * width


def _pad(cell: str, width: int, align: Align) -> str:
    """Pad a cell's text to a fixed width according to its alignment.

    Args:
        cell: The already-escaped cell text.
        width: The target width in characters.
        align: The alignment to apply when padding.

    Returns:
        The padded cell text.
    """
    if align is Align.RIGHT:
        return cell.rjust(width)
    if align is Align.CENTER:
        return cell.center(width)
    return cell.ljust(width)


@dataclass
class MarkdownTable:
    """A builder for GitHub-Flavored Markdown tables.

    Rows can be added positionally via add_row or as dicts keyed by
    header name via add_row_dict. Cell values are converted with
    str() and escaped for markdown safety; any formatting beyond that
    (e.g. numeric precision) is the caller's responsibility.

    Attributes:
        headers: Column header labels, in display order.
        align: Per-column alignment, in the same order as headers.
            Defaults to left-alignment for every column if not given.
        rows: The table's row data, appended to via add_row /
            add_row_dict rather than set directly.
        newline_replacement: String substituted for newline characters
            found inside cell values, since markdown table cells cannot
            contain literal line breaks. Defaults to a single space;
            pass "<br>" for renderers that support inline HTML.
    """

    headers: Sequence[str]
    align: Sequence[Align] = field(default_factory=tuple)
    rows: list[Sequence[Any]] = field(default_factory=list[Sequence[Any]])
    newline_replacement: str = " "

    def __post_init__(self) -> None:
        """Fill in default alignment and validate its length.

        Raises:
            ValueError: If align is provided but its length does not match
                headers.
        """
        if not self.align:
            self.align = tuple(Align.LEFT for _ in self.headers)
        if len(self.align) != len(self.headers):
            raise ValueError(
                f"align length {len(self.align)} != headers length {len(self.headers)}"
            )

    def add_row(self, row: Sequence[Any]) -> None:
        """Append a row supplied as positional values.

        Args:
            row: Cell values in the same order as headers. Values are
                stringified and escaped at render time, not here.

        Raises:
            ValueError: If len(row) does not match len(headers).
        """
        if len(row) != len(self.headers):
            raise ValueError(
                f"row length {len(row)} != headers length {len(self.headers)}"
            )
        self.rows.append(row)

    def add_row_dict(self, row: Mapping[str, Any], default: str | None = None) -> None:
        """Append a row supplied as a dict keyed by header name.

        Values are pulled out in header order regardless of the dict's
        iteration order, so key order in row does not matter.

        Args:
            row: Mapping from header name to cell value. Keys not present
                in headers always raise, regardless of default.
            default: Fill value used for headers missing from row. If
                None (the default), missing headers are treated as
                errors instead of being filled in.

        Raises:
            ValueError: If row contains a key not in headers, or if default
                is None and row is missing a key that is in headers.
        """
        extra = row.keys() - set(self.headers)
        if extra:
            raise ValueError(f"row has unexpected keys: {sorted(extra)}")

        if default is None:
            missing = set(self.headers) - row.keys()
            if missing:
                raise ValueError(f"row missing keys: {sorted(missing)}")
            self.rows.append([row[h] for h in self.headers])
        else:
            self.rows.append([row.get(h, default) for h in self.headers])

    def render(self) -> str:
        """Render the table as a GitHub-Flavored Markdown string.

        Column widths are computed from the widest cell (including the
        header) in each column, then every row is padded to match.

        Returns:
            The complete markdown table, including header and separator
            rows, as a single newline-joined string with no trailing
            newline. If no data rows were added, the output still contains
            a valid header-only table.
        """
        header_cells = [_format_cell(h, self.newline_replacement) for h in self.headers]
        row_cells = [
            [_format_cell(c, self.newline_replacement) for c in row]
            for row in self.rows
        ]

        widths = [max(len(h), 3) for h in header_cells]
        for row in row_cells:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))

        header_cell_strs = (
            _pad(h, widths[i], self.align[i]) for i, h in enumerate(header_cells)
        )
        header_line = f"| {' | '.join(header_cell_strs)} |"

        separator_cell_strs = (
            _separator_cell(widths[i], self.align[i]) for i in range(len(widths))
        )
        separator_line = f"| {' | '.join(separator_cell_strs)} |"

        lines = [header_line, separator_line]
        for row in row_cells:
            row_cell_strs = (
                _pad(c, widths[i], self.align[i]) for i, c in enumerate(row)
            )
            lines.append(f"| {' | '.join(row_cell_strs)} |")
        return "\n".join(lines)


if __name__ == "__main__":
    table = MarkdownTable(
        headers=["Name", "Qty", "Notes"],
        align=[Align.LEFT, Align.RIGHT, Align.LEFT],
    )
    table.add_row(["Widget", 12, "in stock"])
    table.add_row(["Gadget | Deluxe", 3, "backordered\nships in 2wks"])
    print("-- default (space) --")
    print(table.render())

    html_table = MarkdownTable(
        headers=["Name", "Qty", "Notes"],
        align=[Align.LEFT, Align.RIGHT, Align.LEFT],
        newline_replacement="<br>",
    )
    html_table.add_row(["Widget", 12, "in stock"])
    html_table.add_row(["Gadget | Deluxe", 3, "backordered\nships in 2wks"])
    print("\n-- html <br> --")
    print(html_table.render())

    dict_table = MarkdownTable(
        headers=["Name", "Qty", "Notes"],
        align=[Align.LEFT, Align.RIGHT, Align.LEFT],
    )
    dict_table.add_row_dict({"Qty": 12, "Name": "Widget", "Notes": "in stock"})
    dict_table.add_row_dict({"Name": "Gadget", "Qty": 3}, default="-")
    print("\n-- dict-based rows --")
    print(dict_table.render())
