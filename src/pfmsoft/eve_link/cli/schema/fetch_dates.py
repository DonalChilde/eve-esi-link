"""Fetch the available ESI schema compatibility dates."""

from pathlib import Path
from typing import Annotated

import typer
from pfmsoft.eve_snippets import json_io, save_text_file
from pfmsoft.eve_snippets.httpx2.http_session_factory import client_manager
from rich.console import Console
from rich.json import JSON

from pfmsoft.eve_link.schema.helpers.fetch import fetch_compatibility_dates
from pfmsoft.eve_link.settings import USER_AGENT

app = typer.Typer(no_args_is_help=True)


@app.command(name="fetch-dates", help="Fetch available ESI schema compatibility dates.")
def fetch_esi_compatibility_dates(
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
            help="Number of spaces to use for indentation. Defaults to None for a "
            "compact representation.",
        ),
    ] = None,
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
    """Fetch the list of available ESI schema compatibility dates.

    Compatibility dates are YYYY-MM-DD formatted date strings representing the
    dates for which schemas are available. These dates correspond to ESI API
    compatibility versions, typically updated at downtime (11:00 UTC).

    Returns the list as a JSON array of date strings.
    """
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)
    with client_manager(user_agent=USER_AGENT) as session:
        try:
            dates_data = fetch_compatibility_dates(session)
        except Exception as e:
            messenger.print(
                f"[red]Error: Failed to fetch compatibility dates - {e}[/red]"
            )
            raise typer.Exit(code=1) from e

    output_data = json_io.json_dumps(dates_data, indent=indent)
    if file_out == Path("-"):
        if plain:
            print(output_data)
        else:
            messenger.print(JSON(output_data))
        raise typer.Exit()
    # Save to file with default naming if directory is provided
    if file_out.suffix == ".json":
        file_path = file_out
    else:
        default_file_name = "compatibility_dates.json"
        file_path = file_out / default_file_name
    output_path = save_text_file(
        text=output_data,
        directory=file_path.parent,
        filename=file_path.name,
        overwrite=overwrite,
    )
    messenger.print(f"[green]Compatibility dates saved to {output_path}[/green]")
