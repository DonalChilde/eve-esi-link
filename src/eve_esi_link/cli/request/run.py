"""Validate ESI request collections against an ESI schema."""

import asyncio
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

import typer
from rich.console import Console
from rich.json import JSON

from eve_esi_link.cli.helpers import (
    get_eve_link_settings_from_context,
    get_schema,
    get_stdin,
)
from eve_esi_link.esi_request.models import (
    EsiRequestGroup,
    EsiRequestRoot,
    EsiResponse,
    EsiResponseGroup,
    FailedEsiResponse,
)
from eve_esi_link.esi_request.validate import (
    EsiRequestValidationErrors,
)
from eve_esi_link.helpers import json_io
from eve_esi_link.helpers.esi_link_factory import esi_link_factory
from eve_esi_link.helpers.save_text_file import save_text_file
from eve_esi_link.schema.cache import SchemaCacheManager
from eve_esi_link.schema.helpers.schema_files import load_esi_schema_from_file

app = typer.Typer(no_args_is_help=True)


@app.command(
    name="run",
    help="Execute an ESI requests from JSON input using a selected ESI schema.",
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
            help="Path to ESI request JSON. Use `-` for stdin.",
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
            help="Path to write ESI response JSON. Use - for stdout.",
        ),
    ] = Path("-"),
    debug: Annotated[
        bool,
        typer.Option(
            "--debug", help="Output response in debug mode.", show_default=True
        ),
    ] = False,
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
    """Execute requests from an EsiRequest JSON payload.

    Input JSON is deserialized with pydantic as EsiRequest, and internally turned into
    an EsiRequestGroup. Requests are then validated against the selected ESI schema before
    execution.

    If debug output is selected, the EsiResponse|FailedEsiResponse will
    be output, before failure checks are made.

    If neither --schema nor --date is provided, the most recent cached schema is used.

    NOTE: access tokens are currently serialized in the EsiResponse|FailedEsiResponse JSON, so be careful
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

    # Load the ESI request JSON from the input file or stdin
    if file_in == Path("-"):
        request_data = get_stdin()
    else:
        try:
            request_data = file_in.read_text(encoding="utf-8")
        except Exception as e:
            messenger.print(f"[red]Error: Failed to read requests input - {e}[/red]")
            raise typer.Exit(code=1) from e

    # Deserialize the request
    try:
        esi_request = EsiRequestRoot.model_validate_json(request_data).root
    except Exception as e:
        messenger.print(f"[red]Error: Failed to parse ESI requests JSON - {e}[/red]")
        raise typer.Exit(code=1) from e
    request_key = esi_request.request_id

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
                request_group = EsiRequestGroup(
                    name="Internal use group",
                    requests={esi_request.request_id: esi_request},
                )
                responses = await esi_link.make_requests(
                    esi_requests=request_group,
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

    response_group = asyncio.run(run_requests())
    esi_response = _get_response(response_group, request_key)

    if file_out == Path("-"):
        if plain:
            if debug:
                print(esi_response.serialize(indent=indent))
                _fail_check(messenger, esi_response)
            else:
                _fail_check(messenger, esi_response)
                json_result = _get_response_json(esi_response)
                print(json_io.json_dumps(json_result, indent=indent))
            raise typer.Exit()
        else:
            if debug:
                messenger.print(JSON(esi_response.serialize(indent=indent)))
                _fail_check(messenger, esi_response)
            else:
                _fail_check(messenger, esi_response)
                json_result = _get_response_json(esi_response)
                messenger.print(JSON.from_data(json_result, indent=indent))
            raise typer.Exit()

    if debug:
        # Save the result before the fail check
        output_path = save_text_file(
            text=esi_response.serialize(indent=indent),
            directory=file_out.parent,
            filename=file_out.name,
            overwrite=overwrite,
        )
        _fail_check(messenger, esi_response)
    else:
        # Failcheck before saving result
        _fail_check(messenger, esi_response)
        json_result = _get_response_json(esi_response)
        output_text = json_io.json_dumps(json_result, indent=indent)
        output_path = save_text_file(
            text=output_text,
            directory=file_out.parent,
            filename=file_out.name,
            overwrite=overwrite,
        )
    messenger.print(f"[green]ESI response written to {output_path}[/green]")
    _fail_check(messenger, esi_response)
    raise typer.Exit()


def _fail_check(messenger: Console, response: EsiResponse | FailedEsiResponse) -> None:
    """Checks for failures before exit."""
    match response:
        case EsiResponse():
            return
        case FailedEsiResponse():
            messenger.print(
                f"[red]Error: Request failed - {response.failed_response.error_messages}[/red]"
            )
            raise typer.Exit(1)
        case _:
            messenger.print("[red]Error: Unknown response type[/red]")
            raise typer.Exit(1)


def _get_response_json(response: EsiResponse | FailedEsiResponse) -> Any | None:
    match response:
        case EsiResponse():
            return response.response.json
        case FailedEsiResponse():
            return None
        case _:
            raise ValueError("Unknown response type")


def _get_response(
    response_group: EsiResponseGroup, request_key: UUID
) -> EsiResponse | FailedEsiResponse:
    """Get the response for a specific request key."""
    successful_response = response_group.successful_responses.get(request_key)
    if successful_response is not None:
        return successful_response
    failed_response = response_group.failed_responses.get(request_key)
    if failed_response is not None:
        return failed_response
    raise KeyError(f"Request key {request_key} not found in responses.")
