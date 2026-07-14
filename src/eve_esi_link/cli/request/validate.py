"""Validate ESI request collections against an ESI schema."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from eve_esi_link.cli.helpers import get_eve_link_settings_from_context, get_stdin
from eve_esi_link.esi_request.models import EsiRequestGroupRoot
from eve_esi_link.esi_request.validate import (
    EsiRequestValidationErrors,
)
from eve_esi_link.helpers.esi_link_factory import esi_link_factory
from eve_esi_link.schema.cache import SchemaCacheManager
from eve_esi_link.schema.helpers.schema_files import load_esi_schema_from_file

app = typer.Typer(no_args_is_help=True)


@app.command(
    name="validate",
    help="Validate EsiRequestGroup from JSON input against a schema JSON file.",
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
            help="Path to schema JSON file.",
        ),
    ] = None,
    compatibility_date: Annotated[
        str | None,
        typer.Option(
            "--date",
            help="Compatibility date (YYYY-MM-DD) of the schema to use for validation.",
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
    """Validate an EsiRequests dictionary against a schema.

    This command validates input shape with EsiRequestsRoot, loads EsiSchema from a
    schema file, and then validates each request against the matching operation.
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
