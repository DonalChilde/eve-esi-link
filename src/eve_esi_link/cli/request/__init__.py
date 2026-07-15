"""Request CLI command group."""

import typer

from .run import app as run_request_app
from .run_group import app as run_request_group_app
from .samples import app as samples_app
from .validate import app as validate_request_app

app = typer.Typer(no_args_is_help=True)

app.add_typer(validate_request_app)
app.add_typer(run_request_app)
app.add_typer(run_request_group_app)
app.add_typer(samples_app)
