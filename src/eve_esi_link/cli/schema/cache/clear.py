"""Clear cached ESI schema files."""

from typing import Annotated

import typer
from rich.console import Console

from eve_esi_link.cli.helpers import get_eve_link_settings_from_context
from eve_esi_link.schema.cache import SchemaCacheManager

app = typer.Typer(no_args_is_help=True)


@app.command(name="clear", help="Clear cached ESI schema files.")
def clear_cache(
    ctx: typer.Context,
    date: Annotated[
        str | None,
        typer.Option(
            "--date",
            help="Compatibility date (YYYY-MM-DD) of the schema to remove.",
        ),
    ] = None,
    all_dates: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Clear all cached schemas.",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help="Suppress output messages.",
        ),
    ] = False,
):
    """Clear one or all cached ESI schema files.

    Exactly one of --date or --all must be provided.

    Examples:
        Clear schema for a specific date:
            eve-link schema clear-cache --date 2026-06-09

        Clear all cached schemas:
            eve-link schema clear-cache --all
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

    if all_dates:
        deleted = manager.clear_all()
        messenger.print(f"[green]Cleared {deleted} cached schema(s).[/green]")
    else:
        deleted = manager.clear_date(compatibility_date=date)  # type: ignore[arg-type]
        if deleted == 0:
            messenger.print(f"[yellow]No cached schema found for {date}.[/yellow]")
        else:
            messenger.print(
                f"[green]Cleared {deleted} cached schema(s) for {date}.[/green]"
            )
