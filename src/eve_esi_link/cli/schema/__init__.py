"""Schema CLI command group."""

import typer

app = typer.Typer(
    no_args_is_help=True,
    name="schema",
    help="Commands for fetching and working with ESI schemas.",
)

from .cache import app as cache_app
from .doc import app as generate_doc_app
from .fetch import app as fetch_schema_app
from .fetch_changelog import app as fetch_changelog_app
from .fetch_dates import app as fetch_dates_app

app.add_typer(fetch_schema_app)
app.add_typer(fetch_dates_app)
app.add_typer(generate_doc_app)
app.add_typer(cache_app)
app.add_typer(fetch_changelog_app)
