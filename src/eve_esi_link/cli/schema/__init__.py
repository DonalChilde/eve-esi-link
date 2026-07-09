"""Schema CLI command group."""

import typer

app = typer.Typer(no_args_is_help=True)

from .doc import app as generate_doc_app
from .fetch import app as fetch_schema_app

app.add_typer(fetch_schema_app)
app.add_typer(generate_doc_app)
