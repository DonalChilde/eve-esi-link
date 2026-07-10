"""Request CLI command group."""

import typer

from .validate import app as validate_request_app

app = typer.Typer(
    name="request", help="Commands for managing ESI requests.", no_args_is_help=True
)

app.add_typer(
    validate_request_app,
)
