"""Main entry point for the Eve ESI Link CLI application."""

import logging
from dataclasses import asdict
from typing import Annotated

import typer

from eve_esi_link import __app_name__, __version__
from eve_esi_link.logging_config import setup_logging
from eve_esi_link.settings import get_settings

from .examples import app as examples_app
from .schema import app as schema_app

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
    settings = get_settings()
    setup_logging(log_dir=settings.logging_directory)
    ctx.obj = {"eve-esi-link-settings": settings}
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
app.add_typer(
    schema_app,
    name="schema",
    help="Commands for fetching and working with ESI schemas.",
)
