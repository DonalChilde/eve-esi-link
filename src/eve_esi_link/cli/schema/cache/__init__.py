"""CLI commands for managing the ESI schema cache."""

import typer

app = typer.Typer(
    no_args_is_help=True, name="cache", help="Manage the local ESI schema cache."
)

from .clear import app as clear_app
from .doc import app as doc_app
from .list import app as list_app
from .update import app as update_app

app.add_typer(list_app)
app.add_typer(clear_app)
app.add_typer(update_app)
app.add_typer(doc_app)
