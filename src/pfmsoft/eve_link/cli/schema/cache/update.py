"""Fetch and save ESI schemas to the local cache."""

from typing import Annotated

import typer
from pfmsoft.eve_snippets import markdown_table
from pfmsoft.eve_snippets.httpx2.http_session_factory import client_manager
from rich.console import Console
from rich.markdown import Markdown
from whenever import Instant

from pfmsoft.eve_link.cli.helpers import get_eve_link_settings_from_context
from pfmsoft.eve_link.schema.cache import SchemaCacheEntry, SchemaCacheManager
from pfmsoft.eve_link.settings import USER_AGENT

app = typer.Typer(no_args_is_help=True)


@app.command(name="update", help="Fetch and save ESI schemas to the local cache.")
def update_cache(
    ctx: typer.Context,
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Display the output in plain text instead of Rich Markdown.",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help="Suppress status output.",
        ),
    ] = False,
):
    """Fetch and save ESI schemas to the local cache.

    Exactly one of --date or --all must be provided.

    With --all, fetches schemas for every available compatibility date from ESI.
    Existing entries for a date are replaced.

    Examples:
        Cache schema for a specific date:
            eve-link schema cache update --date 2026-06-09

        Cache all available schemas:
            eve-link schema cache update --all
    """
    # ctx is an invisible typer context parameter — not documented in help.
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)

    settings = get_eve_link_settings_from_context(ctx)
    manager = SchemaCacheManager(cache_directory=settings.schema_cache_directory)

    with client_manager(user_agent=USER_AGENT) as session:
        current_entries = manager.list_entries()
        manager.fetch_updates(session=session)
        updated_entries = manager.list_entries()

    report = _build_update_report(current_entries, updated_entries)
    if plain:
        print(report)
    else:
        messenger.print(Markdown(report))


def _build_update_report(
    current_entries: list[SchemaCacheEntry], updated_entries: list[SchemaCacheEntry]
) -> str:
    """Build a report of the cache update operation as markdown."""
    output = ["# ESI Schema Cache Update Report", ""]
    output.append("## Before Update")
    output.append(_build_cache_entries(current_entries))
    output.append("")
    output.append("## After Update")
    output.append(_build_cache_entries(updated_entries))
    return "\n".join(output)


def _build_cache_entries(entries: list[SchemaCacheEntry]) -> str:
    """Build a markdown table of cache entries."""
    table = markdown_table.MarkdownTable(
        headers=["Compatibility Date", "Timestamp (ns)", "UTC"],
        rows=[
            [
                entry.compatibility_date,
                str(entry.timestamp) if entry.timestamp else "None",
                Instant.from_timestamp_nanos(entry.timestamp).format_iso()
                if entry.timestamp
                else "None",
            ]
            for entry in entries
        ],
    )
    return table.render()
