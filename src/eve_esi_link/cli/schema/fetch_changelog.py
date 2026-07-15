"""Fetch the ESI schema for a given date and save it to a file."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.json import JSON

from eve_esi_link.helpers import json_io
from eve_esi_link.helpers.http_session_factory import client_manager
from eve_esi_link.helpers.save_text_file import save_text_file
from eve_esi_link.schema.helpers.fetch import fetch_schema_changelog as fetch_changelog

app = typer.Typer(no_args_is_help=True)


@app.command(name="fetch-changelog", help="Fetch the ESI schema changelog.")
def fetch_schema_changelog(
    ctx: typer.Context,
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
            help="Number of spaces to use for indentation. Use -1 for a compact representation.",
            show_default=True,
        ),
    ] = 2,
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
    """Fetch the ESI schema changelog."""
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)
    if indent == -1:
        indent = None
    with client_manager() as session:
        try:
            schema_changelog = fetch_changelog(session)
        except Exception as e:
            messenger.print(f"[red]Error: Failed to fetch schema - {e}[/red]")
            raise typer.Exit(code=1) from e

    if file_out == Path("-"):
        if plain:
            print(json_io.json_dumps(schema_changelog, indent=indent))
        else:
            messenger.print(JSON.from_data(schema_changelog, indent=indent))
        raise typer.Exit()

    output_path = save_text_file(
        text=json_io.json_dumps(schema_changelog, indent=indent),
        directory=file_out.parent,
        filename=file_out.name,
        overwrite=overwrite,
    )
    messenger.print(f"[green]Schema saved to {output_path}[/green]")
