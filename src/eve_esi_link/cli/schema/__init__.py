import typer

app = typer.Typer(no_args_is_help=True)

from .fetch import app as fetch_schema_app

app.add_typer(fetch_schema_app)
