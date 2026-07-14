"""Validate ESI request collections against an ESI schema."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.json import JSON

from eve_esi_link.cli.helpers import get_eve_link_settings_from_context, get_stdin
from eve_esi_link.esi_request.models import (
    EsiRequestGroupRoot,
    EsiResponseGroupRoot,
)
from eve_esi_link.esi_request.validate import (
    EsiRequestValidationErrors,
)
from eve_esi_link.helpers.esi_link_factory import esi_link_factory
from eve_esi_link.helpers.save_text_file import save_text_file
from eve_esi_link.schema.helpers.io_format import SchemaIOFormat
from eve_esi_link.schema.helpers.schema_files import load_esi_schema_from_file

app = typer.Typer(no_args_is_help=True)


@app.command(
    name="run",
    help="Run ESI requests from JSON input against a schema JSON file.",
)
def make_requests(
    ctx: typer.Context,
    schema_file: Annotated[
        Path,
        typer.Option(
            "--schema",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to schema JSON file.",
        ),
    ],
    input_format: Annotated[
        SchemaIOFormat,
        typer.Option(
            "--input-format",
            help="Input format for the schema JSON. Options are: unaltered, timestamped, "
            "and esi_schema. Defaults to esi_schema.",
        ),
    ] = SchemaIOFormat.ESI_SCHEMA,
    file_in: Annotated[
        Path,
        typer.Option(
            "--from",
            file_okay=True,
            dir_okay=False,
            allow_dash=True,
            help="Path to ESI requests JSON. Defaults to `-` for stdin.",
        ),
    ] = Path("-"),
    file_out: Annotated[
        Path,
        typer.Option(
            "--to",
            file_okay=True,
            dir_okay=False,
            writable=True,
            allow_dash=True,
            help="Path to write ESI responses JSON. Defaults to `-` for stdout.",
        ),
    ] = Path("-"),
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Output plain JSON without rich formatting.",
        ),
    ] = False,
    indent: Annotated[
        int | None,
        typer.Option(
            "--indent",
            help="Number of spaces to use for JSON indentation. Defaults to None.",
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Overwrite the output file if it already exists.",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help="Suppress success output.",
        ),
    ] = False,
) -> None:
    """Make requests to the ESI API based on the provided ESI requests JSON and schema JSON."""
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)
    settings = get_eve_link_settings_from_context(ctx)
    esi_link = esi_link_factory(settings)

    # Load and parse the ESI requests JSON from the input file or stdin
    if file_in == Path("-"):
        requests_data = get_stdin()
    else:
        try:
            requests_data = file_in.read_text(encoding="utf-8")
        except Exception as e:
            messenger.print(f"[red]Error: Failed to read requests input - {e}[/red]")
            raise typer.Exit(code=1) from e
    try:
        esi_requests = EsiRequestGroupRoot.model_validate_json(requests_data).root
    except Exception as e:
        messenger.print(f"[red]Error: Failed to parse ESI requests JSON - {e}[/red]")
        raise typer.Exit(code=1) from e

    # Load and parse the ESI schema JSON from the schema file
    try:
        esi_schema = load_esi_schema_from_file(schema_file)
    except Exception as e:
        messenger.print(f"[red]Error: Failed to load schema from file - {e}[/red]")
        raise typer.Exit(code=1) from e

    async def run_requests():
        async with esi_link:
            try:
                responses = await esi_link.make_requests(
                    esi_requests=esi_requests,
                    schema=esi_schema,
                )
            except EsiRequestValidationErrors as e:
                messenger.print(
                    f"[red]Error: Requests failed due to validation errors[/red]"
                )
                for error in e.errors:
                    messenger.print(f"[red] - {error}[/red]")
                raise typer.Exit(code=1) from e
            return responses

    responses = asyncio.run(run_requests())
    output_text = EsiResponseGroupRoot(root=responses).model_dump_json(indent=indent)
    if file_out == Path("-"):
        if plain:
            print(output_text)
        else:
            messenger.print(JSON(output_text))
        raise typer.Exit(code=0)

    output_path = save_text_file(
        text=output_text,
        output_directory=file_out.parent,
        file_name=file_out.name,
        overwrite=overwrite,
    )
    messenger.print(f"[green]ESI responses written to {output_path}[/green]")
