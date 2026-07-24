# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pfmsoft-eve-link>=0.4.1",
#     "typer>=0.26.8",
# ]
# ///
"""This script fetches market orders for a given region ID from the EVE Online API and saves them to a file or prints them to stdout.

This is not the most efficient way to make repeated requests via the API, but it is fine
for a single request, and offers an example of populating settings from environment variables.
"""

import asyncio
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from pfmsoft.eve_snippets import save_text_file
from pfmsoft.eve_snippets.httpx2.http_session_factory import client_manager

from pfmsoft.eve_link import EsiRequest, make_request
from pfmsoft.eve_link.esi_request.models import FailedEsiResponse
from pfmsoft.eve_link.schema.cache.schema_cache_disk import SchemaCacheManager
from pfmsoft.eve_link.settings import USER_AGENT, get_settings

app = typer.Typer(no_args_is_help=True)

# This command can be run with the following command line:
# The --active flag tells uv to use the active virtual environment, a convenience for development.
# The flag can be removed if you are not doing active development on pfmsoft-eve-link.
# uv run --active ./examples/market_orders_env.py 10000002 --filepath ./dev/tmp/scratch/market_orders.json --overwrite


@app.command()
def main(
    region_id: Annotated[
        int, typer.Argument(help="The region ID to fetch market orders for")
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
):
    """Fetch market orders for a given region ID from the EVE Online API and save them to a file or print to stdout."""
    # This script get its settings from get_settings(), which allows some default settings
    # to be overridden by environment variables. You can set these variables in a .env
    # file or directly in the shell. See the documentation for pfmsoft-eve-link for more
    # information on the available environment variables.
    settings = get_settings()

    # Use the latest schema from the schema cache. If the cache is empty, or new schemas
    # are available, fetch them from the ESI API and cache them.
    schema_manager = SchemaCacheManager(cache_directory=settings.schema_cache_directory)
    with client_manager(USER_AGENT) as session:
        schema_manager.fetch_updates(session=session)
    esi_schema = schema_manager.latest_schema()
    if esi_schema is None:
        typer.echo(
            f"Failed to fetch the latest schema. Please check your cache and try again."
        )
        raise typer.Exit(code=1)

    # Define the ESI request for fetching market orders in the specified region. The
    # request is constructed with a unique request ID, the operation ID for fetching
    # market orders, and the necessary path and query parameters.
    market_orders_request = EsiRequest(
        request_id=uuid4(),
        operation_id="GetMarketsRegionIdOrders",
        path_parameters={"region_id": region_id},
        query_parameters={"order_type": "all"},
    )
    # Make the request to the ESI API using the defined request and the latest schema.
    # This is fine for one-off requests, but for production use, you may want keep the
    # EsiLink object around and reuse it for multiple requests, top avoid the overhead
    # of reinitializing it for each request.
    response = asyncio.run(
        make_request(
            request=market_orders_request, settings=settings, schema=esi_schema
        )
    )
    if isinstance(response, FailedEsiResponse):
        # Prints a failure message to the console if the request fails, including any
        # error messages returned by the API. You could also log this error or handle
        # it in other ways as needed. The FailedEsiResponse object contains more detailed
        # information about the failure, which can be accessed through its attributes.
        typer.echo(
            f"Failed to fetch market orders for region {region_id}: {response.failed_response.error_messages}"
        )
        raise typer.Exit(code=1)

    # If the request is successful, the response is serialized to JSON and either saved
    # to the specified file or printed to stdout, depending on the value of the filepath
    # argument. The --overwrite flag controls whether an existing file will be overwritten.
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


if __name__ == "__main__":
    app()
