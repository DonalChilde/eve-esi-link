"""Main entry point for the Eve ESI Link CLI application."""

import logging
from dataclasses import asdict
from typing import Annotated

import typer
from api_request.cli import app as api_request_app
from api_request.settings import SETTINGS_KEY as API_REQUEST_SETTINGS_KEY
from eve_auth_manager.cli import app as auth_manager_app
from eve_auth_manager.settings import SETTINGS_KEY as AUTH_MANAGER_SETTINGS_KEY

from eve_esi_link import __app_name__, __version__
from eve_esi_link.cli.helpers import (
    construct_api_request_settings,
    construct_eve_auth_manager_settings,
)
from eve_esi_link.logging_config import (
    flush_deferred_handler,
    init_deferred_handler,
    setup_logging,
)
from eve_esi_link.settings import SETTINGS_KEY, get_settings

from . import app as main_app
from .examples import app as examples_app

logger = logging.getLogger(__name__)


def version_callback(value: bool) -> None:
    """Display the application version and exit.

    Args:
        value: A boolean indicating whether to display the version.
    """
    if value:
        typer.echo(f"{__app_name__} v{__version__}")
        raise typer.Exit()


def default_options(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the application version and exit",
            is_eager=True,
            callback=version_callback,
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


app.add_typer(
    examples_app,
    name="examples",
    help="A collection of example commands.",
)
app.add_typer(main_app)
app.add_typer(auth_manager_app, name="auth-manager")
app.add_typer(api_request_app, name="api-request")
