"""Helpers for the CLI."""

import sys
from typing import cast

import typer
from api_request.settings import ApiRequestSettings
from eve_auth_manager.settings import EveAuthManagerSettings

from eve_esi_link.settings import SETTINGS_KEY, EsiLinkSettings


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
