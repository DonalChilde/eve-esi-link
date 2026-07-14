"""Export example EsiRequestGroup objects to JSON files in a specified directory."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from eve_esi_link.samples import export_examples

app = typer.Typer(no_args_is_help=True)


@app.command()
def export(
    output_directory: Annotated[
        Path, typer.Option("--to", help="Directory to export examples to.")
    ],
    indent: Annotated[
        int | None, typer.Option(None, help="Indentation level for JSON files.")
    ] = 2,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing files if they exist."),
    ] = False,
):
    """Export example EsiRequestGroup objects to JSON files in the specified directory."""
    messenger = Console(stderr=True)
    export_examples(output_directory, indent=indent, overwrite=overwrite)
    messenger.print(f"Exported example EsiRequestGroup objects to {output_directory}")
