"""Export example EsiRequestGroup objects to JSON files in a specified directory."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from pfmsoft.eve_link.esi_request.samples import export_examples

app = typer.Typer(no_args_is_help=True)


@app.command(name="samples", help="Export example request payload files.")
def export(
    output_directory: Annotated[
        Path,
        typer.Option(
            "--to", help="Directory where example request JSON files are written."
        ),
    ],
    indent: Annotated[
        int | None,
        typer.Option("--indent", help="Number of spaces for JSON indentation."),
    ] = 2,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing files if they exist."),
    ] = False,
):
    """Export bundled example EsiRequestGroup payloads to JSON files.

    This command writes one or more example request payloads that can be edited and
    used with request validate and request run commands.
    """
    messenger = Console(stderr=True)
    export_examples(output_directory, indent=indent, overwrite=overwrite)
    messenger.print(f"Exported example EsiRequestGroup objects to {output_directory}")
