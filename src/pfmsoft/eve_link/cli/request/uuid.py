from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from rich.console import Console

from pfmsoft.eve_link.helpers import json_io
from pfmsoft.eve_link.helpers.save_text_file import save_text_file

app = typer.Typer(no_args_is_help=True)


@app.command(
    name="uuid",
    help="Generate UUIDs.",
)
def generate_uuids(
    ctx: typer.Context,
    quantity: Annotated[
        int,
        typer.Option(
            "--qty",
            help="Number of uuids to generate. Defaults to 1.",
            show_default=True,
        ),
    ] = 1,
    file_out: Annotated[
        Path,
        typer.Option(
            "--to",
            file_okay=True,
            dir_okay=False,
            writable=True,
            allow_dash=True,
            show_default=True,
            help="Path to write uuids as JSON. Use - for stdout.",
        ),
    ] = Path("-"),
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Output plain JSON to the terminal without rich formatting.",
            show_default=True,
        ),
    ] = False,
    indent: Annotated[
        int | None,
        typer.Option(
            "--indent",
            help="Number of spaces to use for JSON indentation.",
            show_default=True,
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Overwrite the output file if it already exists.",
            show_default=True,
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help="Suppress messages.",
            show_default=True,
        ),
    ] = False,
) -> None:
    """Generate UUIDs."""
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)
    uuids = [str(uuid4()) for _ in range(quantity)]
    if file_out == Path("-"):
        if plain:
            print(json_io.json_dumps(uuids, indent=indent))
        else:
            messenger.print(uuids)
        raise typer.Exit()
    output_path = save_text_file(
        text=json_io.json_dumps(uuids, indent=indent),
        directory=file_out.parent,
        filename=file_out.name,
        overwrite=overwrite,
    )
    messenger.print(f"UUIDs written to {output_path}")
