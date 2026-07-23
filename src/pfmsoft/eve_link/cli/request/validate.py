"""Validate ESI request collections against an ESI schema."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from pfmsoft.eve_link.cli.helpers import (
    get_eve_link_settings_from_context,
    get_schema,
    get_stdin,
)
from pfmsoft.eve_link.esi_link import esi_link_factory
from pfmsoft.eve_link.esi_request.models import EsiRequestGroupRoot
from pfmsoft.eve_link.esi_request.validate import (
    EsiRequestValidationErrors,
)
from pfmsoft.eve_link.schema.cache import SchemaCacheManager
from pfmsoft.eve_link.schema.helpers.schema_files import load_esi_schema_from_file

app = typer.Typer(no_args_is_help=True)


@app.command(
    name="validate",
    help="Validate EsiRequestGroup JSON input against a selected schema.",
)
def validate_requests(
    ctx: typer.Context,
    schema_file: Annotated[
        Path | None,
        typer.Option(
            "--schema",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to schema JSON file. Mutually exclusive with --date.",
        ),
    ] = None,
    compatibility_date: Annotated[
        str | None,
        typer.Option(
            "--date",
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
            help="Path to ESI requests JSON. Defaults to `-` for stdin.",
        ),
    ] = Path("-"),
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help="Suppress success output.",
        ),
    ] = False,
) -> None:
    """Validate requests from an EsiRequestGroup JSON payload.

    Input JSON is parsed as EsiRequestGroup. Each request is validated against
    the matching schema operation and validation errors are reported per request_id.
    """
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)
    if schema_file is not None and compatibility_date is not None:
        messenger.print("[red]Error: --schema and --date are mutually exclusive.[/red]")
        raise typer.Exit(code=1)
    settings = get_eve_link_settings_from_context(ctx)
    esi_link = esi_link_factory(settings)

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
        manager = SchemaCacheManager(cache_directory=settings.schema_cache_directory)
        esi_schema = get_schema(
            messenger=messenger,
            schema_manager=manager,
            compatibility_date=compatibility_date,
        )

    all_errors: list[str] = []
    valid_count = 0
    for request_id, request in esi_requests.requests.items():
        try:
            esi_link.validate_request(request, esi_schema)
            valid_count += 1
        except EsiRequestValidationErrors as e:
            all_errors.extend([
                f"request_id={request_id}: {message}" for message in e.errors
            ])
        except Exception as e:
            all_errors.append(
                f"request_id={request_id}: Unexpected validation error - {e}"
            )

    if all_errors:
        messenger.print(
            f"[red]Validation failed for {len(esi_requests.requests) - valid_count} of "
            f"{len(esi_requests.requests)} request(s).[/red]"
        )
        for error in all_errors:
            messenger.print(f"[red]- {error}[/red]")
        raise typer.Exit(code=1)

    if not quiet:
        messenger.print(
            f"[green]Validated {valid_count} request(s) successfully.[/green]"
        )
