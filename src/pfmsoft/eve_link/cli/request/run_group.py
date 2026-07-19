"""Validate ESI request collections against an ESI schema."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.json import JSON

from pfmsoft.eve_link.cli.helpers import (
    get_eve_link_settings_from_context,
    get_schema,
    get_stdin,
)
from pfmsoft.eve_link.esi_request.models import (
    EsiRequestGroupRoot,
    EsiResponseGroup,
)
from pfmsoft.eve_link.esi_request.validate import (
    EsiRequestValidationErrors,
)
from pfmsoft.eve_link.helpers.esi_link_factory import esi_link_factory
from pfmsoft.eve_link.helpers.save_text_file import save_text_file
from pfmsoft.eve_link.schema.cache import SchemaCacheManager
from pfmsoft.eve_link.schema.helpers.schema_files import load_esi_schema_from_file

app = typer.Typer(no_args_is_help=True)


@app.command(
    name="run-group",
    help="Execute a group of ESI requests from JSON input using a selected ESI schema.",
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
            help="Path to the ESI schema JSON file. Mutually exclusive with --date.",
        ),
    ] = None,
    compatibility_date: Annotated[
        str | None,
        typer.Option(
            "--date",
            show_default=True,
            help="Compatibility date (YYYY-MM-DD) of cached ESI schema to use. Mutually exclusive with --schema.",
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
            help="Path to ESI request-group JSON. Use `-` for stdin.",
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
            help="Path to write ESI response-group JSON. Use - for stdout.",
        ),
    ] = Path("-"),
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Output plain JSON to the terminal without rich formatting.",
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
            help="Suppress messages.",
            show_default=True,
        ),
    ] = False,
) -> None:
    """Execute requests from an EsiRequestGroup JSON payload.

    Input JSON is deserialized with pydantic as EsiRequestGroup. Requests are then validated
    against the selected ESI schema before execution.

    If neither --schema nor --date is provided, the most recent cached schema is used.

    NOTE: access tokens are currently serialized in the EsiResponseGroup JSON, so be careful
    not to expose them in logs or output files. They are only valid for 20 minutes or less.
    This will be fixed soon.
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

    # Load the ESI request-group JSON from the input file or stdin
    if file_in == Path("-"):
        requests_data = get_stdin()
    else:
        try:
            requests_data = file_in.read_text(encoding="utf-8")
        except Exception as e:
            messenger.print(f"[red]Error: Failed to read requests input - {e}[/red]")
            raise typer.Exit(code=1) from e
    # Deserialize the request-group
    try:
        esi_requests = EsiRequestGroupRoot.model_validate_json(
            requests_data, extra="forbid"
        ).root
    except Exception as e:
        messenger.print(
            f"[red]Error: Failed to parse EsiRequestGroup JSON. Did you try to run a single EsiRequest?\n{e}[/red]"
        )
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
        esi_schema = get_schema(
            messenger=messenger,
            schema_manager=manager,
            compatibility_date=compatibility_date,
        )

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
            _fail_check(messenger, responses)
            raise typer.Exit()
        else:
            messenger.print(JSON(responses.serialize(indent=indent)))
            _fail_check(messenger, responses)
            raise typer.Exit()

    output_path = save_text_file(
        text=responses.serialize(indent=indent),
        directory=file_out.parent,
        filename=file_out.name,
        overwrite=overwrite,
    )
    messenger.print(f"[green]ESI responses written to {output_path}[/green]")
    _fail_check(messenger, responses)
    raise typer.Exit()


def _fail_check(messenger: Console, response: EsiResponseGroup) -> None:
    """Checks for failures before exit."""
    if response.failed_responses:
        messenger.print(f"There were {len(response.failed_responses)} failed requests.")
        for request_key, failed_response in response.failed_responses.items():
            messenger.print(
                f"Request {request_key} reports {failed_response.failed_response.error_messages}"
            )
        raise typer.Exit(1)
