"""Fetch the ESI schema for a given date and save it to a file."""

import json
from dataclasses import asdict
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.json import JSON

from eve_esi_link.helpers.eve_dates import previous_downtime
from eve_esi_link.helpers.http_session_factory import client_manager
from eve_esi_link.helpers.save_text_file import save_text_file
from eve_esi_link.schema.fetch import fetch_schema
from eve_esi_link.schema.models import TimestampedDereferencedSchema

app = typer.Typer(no_args_is_help=True)


class OutputFormat(StrEnum):
    """Enum for output format options."""

    BARE = "bare"
    TIMESTAMPED_BARE = "timestamped_bare"
    DEREFERENCED = "dereferenced"
    TIMESTAMPED_DEREFERENCED = "timestamped_dereferenced"


@app.command(name="fetch-schema", help="Fetch the ESI schema for a given date.")
def fetch_esi_schema(
    ctx: typer.Context,
    date: Annotated[
        str,
        typer.Option(
            "--date",
            help="The date for which to fetch the ESI schema in YYYY-MM-DD format. "
            "Defaults to the previous downtime date, which will fetch the most recent schema.",
        ),
    ] = previous_downtime().format("YYYY-MM-DD"),
    file_out: Annotated[
        Path,
        typer.Option(
            "--to",
            help="Path to the output formatted JSON file. Defaults to `-` for stdout.",
        ),
    ] = Path("-"),
    indent: Annotated[
        int | None,
        typer.Option(
            "--indent",
            help="Number of spaces to use for indentation. Defaults to None for a "
            "compact representation.",
        ),
    ] = None,
    format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            help="The output format for the schema. Options are: bare, timestamped_bare, "
            "dereferenced, timestamped_dereferenced. Defaults to timestamped_bare.",
        ),
    ] = OutputFormat.TIMESTAMPED_BARE,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help="Suppress output messages.",
        ),
    ] = False,
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Display the output in plain text JSON instead of Rich JSON.",
        ),
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Whether to overwrite the output file if it already exists.",
        ),
    ] = False,
):
    """Fetch the ESI schema for a given date.

    Schemas are versioned by compatibility dates, a YYYY-MM-DD date string.
    Requesting a schema for a date will return the most recent schema available on that date.

    If no date is provided, the previous downtime date will be used, which will fetch
    the most recent schema.

    If the date is in the future, an error will be raised.
    """
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)
    with client_manager() as session:
        try:
            schema_data = fetch_schema(session, schema_as_of=date)
        except Exception as e:
            messenger.print(f"[red]Error: Failed to fetch schema - {e}[/red]")
            raise typer.Exit(code=1) from e
    match format:
        case OutputFormat.BARE:
            output_data = schema_data.schema
        case OutputFormat.TIMESTAMPED_BARE:
            output_data = asdict(schema_data)
        case OutputFormat.DEREFERENCED:
            dereferenced_schema = TimestampedDereferencedSchema.from_timestamped_schema(
                schema_data
            )
            output_data = dereferenced_schema.dereferenced_schema
        case OutputFormat.TIMESTAMPED_DEREFERENCED:
            dereferenced_schema = TimestampedDereferencedSchema.from_timestamped_schema(
                schema_data
            )
            output_data = asdict(dereferenced_schema)
    if file_out == Path("-"):
        if plain:
            print(json.dumps(output_data, indent=indent))
        else:
            messenger.print(JSON.from_data(output_data, indent=indent))
        raise typer.Exit()
    output_path = save_text_file(
        text=json.dumps(output_data, indent=indent),
        output_directory=file_out.parent,
        file_name=file_out.name,
        overwrite=overwrite,
    )
    messenger.print(f"[green]Schema saved to {output_path}[/green]")
