# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pfmsoft-eve-link>=0.4.1",
#     "typer>=0.26.8",
# ]
# ///
"""This script fetches market orders for a given region ID from the EVE Online API and saves them to a file or prints them to stdout.

This is not the most efficient way to fetch market orders via the API, but it
offers the most explicit control over the fetching process.
"""

import asyncio
from os import devnull
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from pfmsoft.eve_snippets import save_text_file
from pfmsoft.eve_snippets.httpx2.http_session_factory import client_manager

from pfmsoft.eve_link import EsiRequest, make_request
from pfmsoft.eve_link.esi_request.models import FailedEsiResponse
from pfmsoft.eve_link.schema.cache.schema_cache_disk import SchemaCacheManager
from pfmsoft.eve_link.settings import USER_AGENT, EsiLinkSettings

app = typer.Typer(no_args_is_help=True)

# This command can be run with the following command line:
# The --active flag tells uv to use the active virtual environment, a convenience for development.
# The flag can be removed if you are not doing active development on pfmsoft-eve-link.
# uv run --active ./examples/market_orders_scratch.py 10000002 --auth-db ./dev/tmp/scratch/auth.sqlite --web-cache ./dev/tmp/scratch/web-cache.sqlite --schema-cache ./dev/tmp/scratch/schema-cache --filepath ./dev/tmp/scratch/market_orders.json --overwrite


@app.command()
def main(
    region_id: Annotated[
        int, typer.Argument(help="The region ID to fetch market orders for")
    ],
    auth_manager_db_path: Annotated[
        Path,
        typer.Option(
            "--auth-db",
            help="Path to the auth manager database",
            file_okay=True,
            dir_okay=False,
        ),
    ],
    web_cache_path: Annotated[
        Path,
        typer.Option(
            "--web-cache",
            help="Path to the web cache database",
            file_okay=True,
            dir_okay=False,
        ),
    ],
    schema_cache_path: Annotated[
        Path,
        typer.Option(
            "--schema-cache",
            help="Path to the schema cache directory",
            file_okay=False,
            dir_okay=True,
        ),
    ],
    filepath: Annotated[
        Path,
        typer.Option(
            "--filepath",
            help="Path to the file where the market orders will be saved. Use '-' to print to stdout.",
            exists=False,
            file_okay=True,
            dir_okay=False,
            show_default=True,
        ),
    ] = Path("-"),
    indent: Annotated[
        int,
        typer.Option(
            "--indent",
            help="Number of spaces to use for indentation in the output JSON",
            show_default=True,
        ),
    ] = 2,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Whether to overwrite the output file if it already exists",
            show_default=True,
        ),
    ] = False,
    max_rate: Annotated[
        float,
        typer.Option(
            "--max-rate", help="Maximum number of requests per rate-limit window"
        ),
    ] = 20.0,
    time_period: Annotated[
        float,
        typer.Option(
            "--time-period", help="Window duration in seconds for rate limiting"
        ),
    ] = 1.0,
):
    """Fetch market orders for a given region ID from the EVE Online API and save them to a file or print to stdout."""
    settings = EsiLinkSettings(
        application_directory=Path(devnull),
        logging_directory=Path(devnull),
        auth_manager_db_file=auth_manager_db_path,
        api_request_cache_file=web_cache_path,
        schema_cache_directory=schema_cache_path,
        max_rate=max_rate,
        time_period=time_period,
    )
    schema_manager = SchemaCacheManager(cache_directory=schema_cache_path)
    # TODO this bit needs to be reworked after the schema cache update refactors.
    if not schema_manager.list_entries():
        typer.echo(
            f"No cached schemas found in {schema_cache_path}. Fetching the latest schema..."
        )
        with client_manager(USER_AGENT) as session:
            schema_manager.fetch_updates(session=session)
        schema_entries = schema_manager.list_entries()
        if not schema_entries:
            typer.echo(
                f"Failed to fetch and cache the latest schema. Please check your network connection and try again."
            )
            raise typer.Exit(code=1)
        else:
            typer.echo(
                f"Successfully fetched and cached {len(schema_entries)} schemas in {schema_cache_path}."
            )

    latest_schema_entry = schema_manager.latest_entry()
    if latest_schema_entry is None:
        typer.echo(
            f"Failed to find the latest cached schema in {schema_cache_path}. Please check your cache and try again."
        )
        raise typer.Exit(code=1)
    esi_schema = schema_manager.load(
        compatibility_date=latest_schema_entry.compatibility_date
    )
    market_orders_request = EsiRequest(
        request_id=uuid4(),
        operation_id="GetMarketsRegionIdOrders",
        path_parameters={"region_id": region_id},
        query_parameters={"order_type": "all"},
    )

    response = asyncio.run(
        make_request(
            request=market_orders_request, settings=settings, schema=esi_schema
        )
    )
    if isinstance(response, FailedEsiResponse):
        typer.echo(
            f"Failed to fetch market orders for region {region_id}: {response.failed_response.error_messages}"
        )
        raise typer.Exit(code=1)
    if filepath != Path("-"):
        output_path = save_text_file(
            text=response.serialize(indent=indent),
            directory=filepath.parent,
            filename=filepath.name,
            overwrite=overwrite,
        )
        typer.echo(f"Market orders saved to {output_path}")
        raise typer.Exit()
    print(response)


# def fetch_esi_schema() -> EsiSchema:
#     """Fetch the latest ESI schema from the EVE Online API."""
#     with client_manager(USER_AGENT) as session:
#         compatibility_date = latest_schema_date()
#         timestamped_schema = fetch_schema(
#             session=session, schema_as_of=compatibility_date
#         )
#         esi_schema = EsiSchema.from_raw_schema(
#             raw_schema=timestamped_schema.schema,
#             timestamp=timestamped_schema.timestamp,
#         )
#     return esi_schema


if __name__ == "__main__":
    app()
