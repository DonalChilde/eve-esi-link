"""List cached ESI schema entries."""

from typing import Annotated

import typer
from pfmsoft.eve_snippets.markdown.markdown_table import MarkdownTable
from rich.console import Console
from rich.markdown import Markdown
from whenever import Instant

from pfmsoft.eve_link.cli.helpers import get_eve_link_settings_from_context
from pfmsoft.eve_link.schema.cache import SchemaCacheManager

app = typer.Typer(no_args_is_help=True)


@app.command(name="list", help="List cached ESI schema entries.")
def list_cache(
    ctx: typer.Context,
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Display output as plain-text markdown instead of rendered markdown.",
        ),
    ] = False,
):
    """List all cached ESI schema entries as a markdown table.

    Columns:
        Compatibility Date: Schema version date in YYYY-MM-DD format.
        Fetched At: UTC timestamp of when the schema was fetched, or empty.
    """
    # ctx is an invisible typer context parameter — not documented in help.
    settings = get_eve_link_settings_from_context(ctx)
    console = Console()
    manager = SchemaCacheManager(cache_directory=settings.schema_cache_directory)
    entries = manager.list_entries()

    table = MarkdownTable(headers=["Compatibility Date", "Fetched At"])
    for entry in entries:
        fetched_at = (
            Instant.from_timestamp_nanos(entry.timestamp).format("YYYY-MM-DD hh:mm:ss")
            if entry.timestamp is not None
            else ""
        )
        table.add_row([entry.compatibility_date, fetched_at])

    rendered = table.render()
    report = f"# Cached ESI schema entries\n\n{rendered}"
    if plain:
        print(report)
    else:
        console.print(Markdown(report))
