"""Format JSON files for better readability."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.json import JSON

from ..helpers import get_stdin

app = typer.Typer(
    name="format-json",
    help="Format JSON files for better readability.",
    no_args_is_help=True,
)


@app.command()
def format_json(
    ctx: typer.Context,
    file_in: Annotated[
        Path,
        typer.Option(
            "--from", help="Path to the input JSON file. Defaults to `-` for stdin."
        ),
    ] = Path("-"),
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
            help="Number of spaces to use for indentation. Defaults to None for a compact representation.",
        ),
    ] = None,
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
) -> None:
    """Format a JSON file for better readability."""
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)

    if file_in == Path("-"):
        input_data = get_stdin()
    else:
        input_data = file_in.read_text()

    try:
        json_data = json.loads(input_data)
        output_data = json.dumps(json_data, indent=indent)
    except json.JSONDecodeError as e:
        messenger.print(f"[red]Error: Invalid JSON input - {e}[/red]")
        raise typer.Exit(code=1) from e

    if file_out == Path("-"):
        if plain:
            print(output_data)
        else:
            messenger.print(JSON(output_data))
        raise typer.Exit()
    file_out.parent.mkdir(parents=True, exist_ok=True)
    if file_out.exists() and not overwrite:
        messenger.print(
            f"[red]Error: Output file '{file_out}' already exists. Use --overwrite to overwrite it.[/red]"
        )
        raise typer.Exit(code=1)
    file_out.write_text(json.dumps(json_data, indent=indent))
    messenger.print(f"[green]Formatted JSON written to '{file_out}'[/green]")
