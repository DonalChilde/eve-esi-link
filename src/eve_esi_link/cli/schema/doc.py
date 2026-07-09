"""Generate markdown documentation from ESI schema JSON."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from eve_esi_link.cli.schema.helpers import (
    SchemaIOFormat,
    deserialize_schema,
    get_esi_schema,
)
from eve_esi_link.helpers.save_text_file import save_text_file
from eve_esi_link.schema.schema_doc_2 import (
    FencedDataFormat,
    generate_esi_schema_markdown_doc,
)

from ..helpers import get_stdin

app = typer.Typer(no_args_is_help=True)


@app.command(
    name="generate-doc",
    help="Generate operation-focused markdown documentation from a schema JSON file.",
)
def generate_schema_doc(
    file_in: Annotated[
        Path,
        typer.Option(
            "--from",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            allow_dash=True,
            help="Path to schema JSON. Defaults to `-` for stdin.",
        ),
    ] = Path("-"),
    file_out: Annotated[
        Path,
        typer.Option(
            "--to",
            help="Output markdown file path. Defaults to `-` for stdout.",
            allow_dash=True,
            dir_okay=False,
        ),
    ] = Path("-"),
    input_format: Annotated[
        SchemaIOFormat,
        typer.Option(
            "--input-format",
            help="Input format for the schema JSON. Options are: bare, timestamped_bare, "
            "dereferenced, timestamped_dereferenced. Defaults to timestamped_bare.",
        ),
    ] = SchemaIOFormat.TIMESTAMPED_BARE,
    fenced_format: Annotated[
        FencedDataFormat,
        typer.Option(
            "--fenced-format",
            help="Serialization format for fenced request/response blocks. Defaults to json.",
        ),
    ] = FencedDataFormat.JSON,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Overwrite output file if it already exists.",
        ),
    ] = False,
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Display the output in plain text instead of Rich Markdown.",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help="Suppress status output.",
        ),
    ] = False,
) -> None:
    """Generate markdown documentation from ESI schema JSON.

    The generated markdown includes version metadata, TOC grouped by tag, and a
    per-operation section that covers summary, parameters, request body, response schema,
    and extension fields.
    """
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)
    if file_in == Path("-"):
        input_data = get_stdin()
    else:
        try:
            input_data = file_in.read_text(encoding="utf-8")
        except Exception as e:
            messenger.print(f"[red]Error: Failed to read input file - {e}[/red]")
            raise typer.Exit(code=1) from e
    try:
        schema = deserialize_schema(input_data, format=input_format)
    except Exception as e:
        messenger.print(f"[red]Error: Failed to deserialize schema - {e}[/red]")
        raise typer.Exit(code=1) from e

    esi_schema = get_esi_schema(schema)
    markdown_doc = generate_esi_schema_markdown_doc(
        schema=esi_schema,
        fenced_format=fenced_format,
    )
    if file_out == Path("-"):
        if plain:
            print(markdown_doc)
        else:
            messenger.print(Markdown(markdown_doc))
        raise typer.Exit()
    try:
        output_path = save_text_file(
            text=markdown_doc,
            output_directory=file_out.parent,
            file_name=file_out.name,
            overwrite=overwrite,
        )
    except Exception as e:
        messenger.print(f"[red]Error: Failed to save output file - {e}[/red]")
        raise typer.Exit(code=1) from e
    messenger.print(f"[green]Markdown documentation saved to {output_path}[/green]")
