"""Main entry point for the Eve ESI Link CLI application."""

import logging
from dataclasses import asdict
from typing import Annotated

import typer
from pfmsoft.api_request.settings import SETTINGS_KEY as API_REQUEST_SETTINGS_KEY
from pfmsoft.eve_auth_manager.cli import app as auth_manager_app
from pfmsoft.eve_auth_manager.settings import SETTINGS_KEY as AUTH_MANAGER_SETTINGS_KEY
from rich.console import Console

from pfmsoft.eve_link import __app_name__, __version__
from pfmsoft.eve_link.cli import app as main_app
from pfmsoft.eve_link.cli.helpers import (
    construct_api_request_settings,
    construct_eve_auth_manager_settings,
    get_eve_link_settings_from_context,
)
from pfmsoft.eve_link.logging_config import (
    flush_deferred_handler,
    init_deferred_handler,
    setup_logging,
)
from pfmsoft.eve_link.settings import SETTINGS_KEY, get_settings

logger = logging.getLogger(__name__)


def default_options(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the application version and exit",
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Initialize settings and logging for standalone CLI execution.

    Notes:
        The resolved EsiLinkSettings object is stored in ctx.obj under
        the eve-esi-link-settings key.
    """
    init_deferred_handler()
    settings = get_settings()
    auth_manager_settings = construct_eve_auth_manager_settings(settings)
    api_request_settings = construct_api_request_settings(settings)
    setup_logging(log_dir=settings.logging_directory)
    flush_deferred_handler()
    ctx.obj = {
        SETTINGS_KEY: settings,
        AUTH_MANAGER_SETTINGS_KEY: auth_manager_settings,
        API_REQUEST_SETTINGS_KEY: api_request_settings,
    }
    logger.info(
        f"Starting {__app_name__} v{__version__} with settings: {asdict(settings)!r}"
    )


app = typer.Typer(
    name="eve-link",
    help="A command line interface for interacting with EVE Online's ESI API.",
    callback=default_options,
    no_args_is_help=True,
)


@app.command()
def version(ctx: typer.Context) -> None:
    """Display the application version and exit."""
    settings = get_eve_link_settings_from_context(ctx)
    console = Console(stderr=True)
    console.print(f"{__app_name__} v{__version__}")
    console.print(f"Settings:")
    console.print(settings)


app.add_typer(main_app)
app.add_typer(auth_manager_app, name="auth-manager")
