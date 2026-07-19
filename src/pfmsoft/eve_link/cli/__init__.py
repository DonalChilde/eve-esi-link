import typer

from .request import app as request_app
from .schema import app as schema_app

app = typer.Typer(
    no_args_is_help=True,
    help="A command line interface for interacting with EVE Online's ESI API.",
)

app.add_typer(request_app)
app.add_typer(schema_app)
