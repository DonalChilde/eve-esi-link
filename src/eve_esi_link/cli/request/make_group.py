"""A Command to load EsiRequestList, and convert to a EsiRequestGroup."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.json import JSON

from eve_esi_link.cli.helpers import get_eve_link_settings_from_context, get_stdin
from eve_esi_link.cli.schema.helpers import (
    SchemaIOFormat,
    deserialize_schema,
    get_esi_schema,
)
from eve_esi_link.esi_request.models import (
    EsiRequestGroupRoot,
    EsiResponseGroupRoot,
)
from eve_esi_link.esi_request.validate import (
    EsiRequestValidationErrors,
)
from eve_esi_link.helpers.esi_link_factory import esi_link_factory
from eve_esi_link.helpers.save_text_file import save_text_file

app = typer.Typer(
    no_args_is_help=True,
    help="A Command to load EsiRequestList, and convert to a EsiRequestGroup.",
)


@app.command()
def make_group(
    ctx: typer.Context,
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
):
    raise NotImplementedError()
