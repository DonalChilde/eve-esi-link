"""Fetch the ESI schema for a given date and save it to a file."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.json import JSON

from eve_esi_link.helpers import json_io
from eve_esi_link.helpers.eve_dates import previous_downtime
from eve_esi_link.helpers.http_session_factory import client_manager
from eve_esi_link.helpers.save_text_file import save_text_file
from eve_esi_link.schema.helpers.fetch import TimestampedSchemaRoot, fetch_schema
from eve_esi_link.schema.helpers.io_format import SchemaIOFormat
from eve_esi_link.schema.models import EsiSchema

app = typer.Typer(no_args_is_help=True)


@app.command(name="fetch", help="Fetch the ESI schema for a given date.")
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
            help="Path to output JSON file. Use - for stdout.",
            allow_dash=True,
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
        SchemaIOFormat,
        typer.Option(
            "--format",
            help="The output format for the schema. Options are: unaltered, timestamped,"
            " and esi_schema.",
        ),
    ] = SchemaIOFormat.ESI_SCHEMA,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help="Suppress status output.",
        ),
    ] = False,
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Display JSON as plain text instead of Rich JSON.",
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
        case SchemaIOFormat.UNALTERED:
            output_data = json_io.json_dumps(schema_data.schema, indent=indent)
        case SchemaIOFormat.TIMESTAMPED:
            output_data = TimestampedSchemaRoot(root=schema_data).model_dump_json(
                indent=indent
            )
        case SchemaIOFormat.ESI_SCHEMA:
            esi_echema = EsiSchema.from_raw_schema(
                raw_schema=schema_data.schema, timestamp=schema_data.timestamp
            )
            output_data = esi_echema.serialize(indent=indent)
    if file_out == Path("-"):
        if plain:
            print(output_data)
        else:
            messenger.print(JSON(output_data, indent=indent))
        raise typer.Exit()
    # If file_out ends in .json, use file_out for file_path.
    # If file_out is a directory, use a default file name that includes the schema
    # date and SchemaIIOformat
    if file_out.suffix == ".json":
        file_path = file_out
    else:
        schema_compat_date = schema_data.schema["info"]["version"]
        default_file_name = f"schema_{schema_compat_date}_{format.value}.json"
        file_path = file_out / default_file_name
    output_path = save_text_file(
        text=output_data,
        directory=file_path.parent,
        filename=file_path.name,
        overwrite=overwrite,
    )
    messenger.print(f"[green]Schema saved to {output_path}[/green]")
