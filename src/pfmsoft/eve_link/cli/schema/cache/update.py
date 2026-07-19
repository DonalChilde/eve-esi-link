"""Fetch and save ESI schemas to the local cache."""

from typing import Annotated

import typer
from rich.console import Console

from pfmsoft.eve_link.cli.helpers import get_eve_link_settings_from_context
from pfmsoft.eve_link.helpers.http_session_factory import client_manager
from pfmsoft.eve_link.schema.cache import SchemaCacheManager
from pfmsoft.eve_link.schema.helpers.fetch import (
    fetch_compatibility_dates,
    fetch_schema,
)
from pfmsoft.eve_link.schema.models import EsiSchema

app = typer.Typer(no_args_is_help=True)


@app.command(name="update", help="Fetch and save ESI schemas to the local cache.")
def update_cache(
    ctx: typer.Context,
    date: Annotated[
        str | None,
        typer.Option(
            "--date",
            help="Compatibility date (YYYY-MM-DD) of the schema to fetch and cache.",
        ),
    ] = None,
    all_dates: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Fetch and cache schemas for all available compatibility dates.",
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
    messenger = Console(stderr=True, quiet=quiet)

    if date is None and not all_dates:
        messenger.print("[red]Error: provide --date DATE or --all.[/red]")
        raise typer.Exit(code=1)
    if date is not None and all_dates:
        messenger.print("[red]Error: --date and --all are mutually exclusive.[/red]")
        raise typer.Exit(code=1)

    settings = get_eve_link_settings_from_context(ctx)
    manager = SchemaCacheManager(cache_directory=settings.schema_cache_directory)

    with client_manager() as session:
        if all_dates:
            try:
                dates_data = fetch_compatibility_dates(session)
            except Exception as e:
                messenger.print(
                    f"[red]Error: Failed to fetch compatibility dates - {e}[/red]"
                )
                raise typer.Exit(code=1) from e
            dates = list(dates_data.compatibility_dates)
        else:
            assert date is not None
            dates = [date]

        saved = 0
        for schema_date in dates:
            try:
                schema_data = fetch_schema(session, schema_as_of=schema_date)
            except Exception as e:
                messenger.print(
                    f"[red]Error: Failed to fetch schema for {schema_date} - {e}[/red]"
                )
                continue
            esi_schema = EsiSchema.from_raw_schema(
                raw_schema=schema_data.schema, timestamp=schema_data.timestamp
            )
            manager.save(schema=esi_schema)
            messenger.print(f"[green]Cached schema for {schema_date}.[/green]")
            saved += 1

    messenger.print(f"[green]Done. Cached {saved} schema(s).[/green]")
