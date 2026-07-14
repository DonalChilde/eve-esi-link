"""Generate markdown documentation from ESI schema JSON."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from eve_esi_link.helpers import json_io
from eve_esi_link.helpers.save_text_file import save_text_file
from eve_esi_link.schema.helpers.io_format import SchemaIOFormat
from eve_esi_link.schema.helpers.schema_files import (
    load_esi_schema,
    load_esi_schema_from_file,
)
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
            help="Input format for the schema JSON. Options are: unaltered, timestamped, "
            "and esi_schema. Defaults to esi_schema.",
        ),
    ] = SchemaIOFormat.ESI_SCHEMA,
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
    # Get the EsiSchema from the input file or stdin
    if file_in == Path("-"):
        input_data = get_stdin()
        try:
            schema_dict = json_io.json_loads(input_data)
        except Exception as e:
            messenger.print(f"[red]Error: Failed to parse JSON input - {e}[/red]")
            raise typer.Exit(code=1) from e
        esi_schema = load_esi_schema(schema_dict)
    else:
        try:
            esi_schema = load_esi_schema_from_file(file_path=file_in)
        except Exception as e:
            messenger.print(f"[red]Error: Failed to read input file - {e}[/red]")
            raise typer.Exit(code=1) from e

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

    if file_out.suffix == ".md":
        file_path = file_out
    else:
        schema_compat_date = esi_schema.compatibility_date
        default_file_name = f"schema_docs_{schema_compat_date}.md"
        file_path = file_out / default_file_name
    try:
        output_path = save_text_file(
            text=markdown_doc,
            output_directory=file_path.parent,
            file_name=file_path.name,
            overwrite=overwrite,
        )
    except Exception as e:
        messenger.print(f"[red]Error: Failed to save output file - {e}[/red]")
        raise typer.Exit(code=1) from e
    messenger.print(f"[green]Markdown documentation saved to {output_path}[/green]")
