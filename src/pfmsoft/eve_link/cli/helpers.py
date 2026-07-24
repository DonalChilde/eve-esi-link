"""Helpers for the CLI."""

import sys
from typing import cast

import typer
from pfmsoft.api_request.settings import ApiRequestSettings
from pfmsoft.eve_auth_manager.settings import EveAuthManagerSettings
from rich.console import Console

from pfmsoft.eve_link.schema.cache.schema_cache_disk import SchemaCacheManager
from pfmsoft.eve_link.schema.models import EsiSchema
from pfmsoft.eve_link.settings import SETTINGS_KEY, EsiLinkSettings


def get_stdin() -> str:
    """Read piped or redirected stdin content until EOF.

    Returns:
        Full stdin content as a string.

    Raises:
        ValueError: If stdin is attached to an interactive terminal instead
            of a pipe or redirected input source.
    """
    if sys.stdin.isatty():
        raise ValueError("Error: provide a file path or pipe data via stdin.")
    return sys.stdin.read()


def get_eve_link_settings_from_context(ctx: typer.Context) -> EsiLinkSettings:
    """Retrieve the Eve ESI Link settings from the Typer context.

    Args:
        ctx: The Typer context object.

    Returns:
        The Eve ESI Link settings.
    """
    settings = cast(EsiLinkSettings, ctx.obj.get(SETTINGS_KEY))
    return settings


def construct_eve_auth_manager_settings(
    settings: EsiLinkSettings,
) -> EveAuthManagerSettings:
    """Construct an EveAuthManagerSettings object from the Eve ESI Link settings.

    Args:
        settings: The Eve ESI Link settings.

    Returns:
        An EveAuthManagerSettings object with the appropriate configuration.
    """
    return EveAuthManagerSettings(
        application_directory=settings.application_directory,
        logging_directory=settings.logging_directory,
        authorization_database_path=settings.auth_manager_db_file,
    )


def construct_api_request_settings(settings: EsiLinkSettings) -> ApiRequestSettings:
    """Construct an ApiRequestSettings object from the Eve ESI Link settings.

    Args:
        settings: The Eve ESI Link settings.

    Returns:
        An ApiRequestSettings object with the appropriate configuration.
    """
    return ApiRequestSettings(
        application_directory=settings.application_directory,
        logging_directory=settings.logging_directory,
        web_cache_path=settings.api_request_cache_file,
    )


def get_schema(
    messenger: Console,
    schema_manager: SchemaCacheManager,
    compatibility_date: str | None,
) -> EsiSchema:
    """Get the EsiSchema from the cache."""
    try:
        if compatibility_date is not None:
            esi_schema = schema_manager.load(compatibility_date=compatibility_date)
        else:
            available_dates = schema_manager.list_entries()
            if not available_dates:
                messenger.print(
                    "[red]Error: No cached schemas found. Use --schema or update the cache.[/red]"
                )
                raise typer.Exit(code=1)
            most_recent_date = max(
                entry.compatibility_date for entry in available_dates
            )
            esi_schema = schema_manager.load(compatibility_date=most_recent_date)
            messenger.print(f"Using most recent cached schema: {most_recent_date}")
    except typer.Exit:
        raise
    except FileNotFoundError as e:
        messenger.print(
            f"[red]Error: No cached schema found for {compatibility_date}.[/red]"
        )
        raise typer.Exit(code=1) from e
    except Exception as e:
        messenger.print(f"[red]Error: Failed to load cached schema - {e}[/red]")
        raise typer.Exit(code=1) from e
    return esi_schema
