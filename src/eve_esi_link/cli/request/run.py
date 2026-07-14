"""Validate ESI request collections against an ESI schema."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.json import JSON

from eve_esi_link.cli.helpers import get_eve_link_settings_from_context, get_stdin
from eve_esi_link.esi_request.models import (
    EsiRequestGroupRoot,
)
from eve_esi_link.esi_request.validate import (
    EsiRequestValidationErrors,
)
from eve_esi_link.helpers.esi_link_factory import esi_link_factory
from eve_esi_link.helpers.save_text_file import save_text_file
from eve_esi_link.schema.cache import SchemaCacheManager
from eve_esi_link.schema.helpers.schema_files import load_esi_schema_from_file

app = typer.Typer(no_args_is_help=True)


@app.command(
    name="run",
    help="Execute ESI requests from JSON input using a selected schema.",
)
def make_requests(
    ctx: typer.Context,
    schema_file: Annotated[
        Path | None,
        typer.Option(
            "--schema",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            show_default=True,
            help="Path to schema JSON file. Mutually exclusive with --date.",
        ),
    ] = None,
    compatibility_date: Annotated[
        str | None,
        typer.Option(
            "--date",
            show_default=True,
            help="Compatibility date (YYYY-MM-DD) of cached schema to use. Mutually exclusive with --schema.",
        ),
    ] = None,
    file_in: Annotated[
        Path,
        typer.Option(
            "--from",
            file_okay=True,
            dir_okay=False,
            allow_dash=True,
            show_default=True,
            help="Path to ESI requests JSON. Use `-` for stdin.",
        ),
    ] = Path("-"),
    file_out: Annotated[
        Path,
        typer.Option(
            "--to",
            file_okay=True,
            dir_okay=False,
            writable=True,
            allow_dash=True,
            show_default=True,
            help="Path to write ESI responses JSON. Use - for stdout.",
        ),
    ] = Path("-"),
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Output plain JSON without rich formatting.",
            show_default=True,
        ),
    ] = False,
    indent: Annotated[
        int | None,
        typer.Option(
            "--indent",
            help="Number of spaces to use for JSON indentation.",
            show_default=True,
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Overwrite the output file if it already exists.",
            show_default=True,
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help="Suppress success output.",
            show_default=True,
        ),
    ] = False,
) -> None:
    """Execute requests from an EsiRequestGroup JSON payload.

    Input JSON is parsed as EsiRequestGroupRoot. Requests are validated against the
    selected schema before execution.

    If neither --schema nor --date is provided, the most recent cached schema is used.

    NOTE: access tokens are currently serialized in the EsiResponses JSON, so be careful
    not to expose them in logs or output files. They are only valid for 20 minutes or less.
    """
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)
    if schema_file is not None and compatibility_date is not None:
        messenger.print(
            "[red]Error: Cannot specify both --schema and --date options.[/red]"
        )
        raise typer.Exit(code=1)
    settings = get_eve_link_settings_from_context(ctx)
    esi_link = esi_link_factory(settings)

    # Load and parse the ESI requests JSON from the input file or stdin
    if file_in == Path("-"):
        requests_data = get_stdin()
    else:
        try:
            requests_data = file_in.read_text(encoding="utf-8")
        except Exception as e:
            messenger.print(f"[red]Error: Failed to read requests input - {e}[/red]")
            raise typer.Exit(code=1) from e
    try:
        esi_requests = EsiRequestGroupRoot.model_validate_json(requests_data).root
    except Exception as e:
        messenger.print(f"[red]Error: Failed to parse ESI requests JSON - {e}[/red]")
        raise typer.Exit(code=1) from e

    if schema_file is not None:
        try:
            esi_schema = load_esi_schema_from_file(schema_file)
        except Exception as e:
            messenger.print(f"[red]Error: Failed to load schema from file - {e}[/red]")
            raise typer.Exit(code=1) from e
    else:
        # if compatibility_date is None, get the most recent cached schema
        manager = SchemaCacheManager(cache_directory=settings.schema_cache_directory)
        try:
            if compatibility_date is not None:
                esi_schema = manager.load(compatibility_date=compatibility_date)
            else:
                available_dates = manager.list_entries()
                if not available_dates:
                    messenger.print(
                        "[red]Error: No cached schemas found. Use --schema or update the cache.[/red]"
                    )
                    raise typer.Exit(code=1)
                most_recent_date = max(
                    entry.compatibility_date for entry in available_dates
                )
                esi_schema = manager.load(compatibility_date=most_recent_date)
                messenger.print(f"Using most recent cached schema: {most_recent_date}")
        except FileNotFoundError as e:
            messenger.print(
                f"[red]Error: No cached schema found for {compatibility_date}.[/red]"
            )
            raise typer.Exit(code=1) from e
        except Exception as e:
            messenger.print(f"[red]Error: Failed to load cached schema - {e}[/red]")
            raise typer.Exit(code=1) from e

    async def run_requests():
        async with esi_link:
            try:
                responses = await esi_link.make_requests(
                    esi_requests=esi_requests,
                    schema=esi_schema,
                )
            except EsiRequestValidationErrors as e:
                messenger.print(
                    f"[red]Error: Requests failed due to validation errors[/red]"
                )
                for error in e.errors:
                    messenger.print(f"[red] - {error}[/red]")
                raise typer.Exit(code=1) from e
            return responses

    responses = asyncio.run(run_requests())

    if file_out == Path("-"):
        if plain:
            print(responses.serialize(indent=indent))
        else:
            messenger.print(JSON(responses.serialize(indent=indent)))
        raise typer.Exit(code=0)

    output_path = save_text_file(
        text=responses.serialize(indent=indent),
        output_directory=file_out.parent,
        file_name=file_out.name,
        overwrite=overwrite,
    )
    messenger.print(f"[green]ESI responses written to {output_path}[/green]")
