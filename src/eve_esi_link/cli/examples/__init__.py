import typer

from .format_json import app as format_json_app

app = typer.Typer(
    name="examples",
    help="A collection of example commands.",
    no_args_is_help=True,
)

app.add_typer(
    format_json_app,
    name="format-json",
    help="Format JSON files for better readability.",
)
