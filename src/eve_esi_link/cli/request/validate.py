"""Validate ESI request collections against an ESI schema."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from eve_esi_link.cli.schema.helpers import SchemaIOFormat
from eve_esi_link.esi_request.models import EsiRequestsRoot
from eve_esi_link.esi_request.validate import (
    EsiRequestValidationError,
    EsiRequestValidationErrors,
    validate_esi_request,
)

from ..helpers import get_stdin
from ..schema.helpers import deserialize_schema, get_esi_schema

app = typer.Typer(no_args_is_help=True)


@app.command(
    name="validate",
    help="Validate ESI requests from JSON input against a schema JSON file.",
)
def validate_requests(
    ctx: typer.Context,
    schema_file: Annotated[
        Path,
        typer.Option(
            "--schema",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to schema JSON file.",
        ),
    ],
    input_format: Annotated[
        SchemaIOFormat,
        typer.Option(
            "--input-format",
            help="Input format for the schema JSON. Options are: bare, timestamped_bare, "
            "dereferenced, timestamped_dereferenced. Defaults to timestamped_bare.",
        ),
    ] = SchemaIOFormat.TIMESTAMPED_BARE,
    file_in: Annotated[
        Path,
        typer.Option(
            "--from",
            file_okay=True,
            dir_okay=False,
            allow_dash=True,
            help="Path to ESI requests JSON. Defaults to `-` for stdin.",
        ),
    ] = Path("-"),
    require_access_token: Annotated[
        bool,
        typer.Option(
            "--require-access-token",
            help="Require authorization.access_token for authenticated operations.",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help="Suppress success output.",
        ),
    ] = False,
) -> None:
    """Validate an EsiRequests dictionary against a schema.

    This command validates input shape with EsiRequestsRoot, loads EsiSchema from a
    schema file, and then validates each request against the matching operation.
    """
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)

    if file_in == Path("-"):
        requests_data = get_stdin()
    else:
        try:
            requests_data = file_in.read_text(encoding="utf-8")
        except Exception as e:
            messenger.print(f"[red]Error: Failed to read requests input - {e}[/red]")
            raise typer.Exit(code=1) from e

    try:
        esi_requests = EsiRequestsRoot.model_validate_json(requests_data).root
    except Exception as e:
        messenger.print(f"[red]Error: Failed to parse ESI requests JSON - {e}[/red]")
        raise typer.Exit(code=1) from e

    try:
        schema_data = deserialize_schema(
            schema_file.read_text(encoding="utf-8"), input_format
        )
    except Exception as e:
        messenger.print(f"[red]Error: Failed to read schema file - {e}[/red]")
        raise typer.Exit(code=1) from e

    try:
        esi_schema = get_esi_schema(schema_data)
    except Exception as e:
        messenger.print(f"[red]Error: Failed to parse EsiSchema JSON - {e}[/red]")
        raise typer.Exit(code=1) from e

    all_errors: list[str] = []
    valid_count = 0
    for request_id, request in esi_requests.items():
        try:
            validate_esi_request(
                request,
                esi_schema,
                require_access_token=require_access_token,
            )
            valid_count += 1
        except EsiRequestValidationErrors as e:
            all_errors.extend([
                f"request_id={request_id}: {message}" for message in e.errors
            ])
        except EsiRequestValidationError as e:
            all_errors.append(f"request_id={request_id}: {e}")
        except Exception as e:
            all_errors.append(
                f"request_id={request_id}: Unexpected validation error - {e}"
            )

    if all_errors:
        messenger.print(
            f"[red]Validation failed for {len(esi_requests) - valid_count} of "
            f"{len(esi_requests)} request(s).[/red]"
        )
        for error in all_errors:
            messenger.print(f"[red]- {error}[/red]")
        raise typer.Exit(code=1)

    if not quiet:
        messenger.print(
            f"[green]Validated {valid_count} request(s) successfully.[/green]"
        )
