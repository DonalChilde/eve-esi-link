"""Request CLI command group."""

import typer

from .make_group import app as make_group_app
from .run import app as run_request_app
from .validate import app as validate_request_app

app = typer.Typer(
    name="request", help="Commands for managing ESI requests.", no_args_is_help=True
)

app.add_typer(validate_request_app)
app.add_typer(run_request_app)
app.add_typer(make_group_app)
