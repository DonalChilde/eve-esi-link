# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pfmsoft-eve-link>=0.4.1",
#     "typer>=0.26.8",
# ]
# ///

import asyncio
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from pfmsoft.eve_snippets import save_text_file
from pfmsoft.eve_snippets.eve.eve_dates import latest_schema_date
from pfmsoft.eve_snippets.httpx2.http_session_factory import client_manager

from pfmsoft.eve_link import EsiLink, EsiRequest
from pfmsoft.eve_link.esi_request.models import EsiRequestGroup
from pfmsoft.eve_link.schema.helpers.fetch import fetch_schema
from pfmsoft.eve_link.schema.models import EsiSchema
from pfmsoft.eve_link.settings import USER_AGENT

app = typer.Typer(no_args_is_help=True)

# This command can be run with the following command line:
# The --active flag tells uv to use the active virtual environment, a convenience for development.
# The flag can be removed if you are not doing active development on pfmsoft-eve-link.
# uv run --active ./examples/market_orders_scratch.py 10000002 --auth-db ./dev/tmp/scratch/auth.sqlite --web-cache ./dev/tmp/scratch/web-cache.sqlite


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
    # It is suboptimal to fetch the schema every time, but for this example, we will do it.
    esi_schema = fetch_esi_schema()
    market_orders_request = EsiRequest(
        request_id=uuid4(),
        operation_id="GetMarketsRegionIdOrders",
        path_parameters={"region_id": region_id},
        query_parameters={"order_type": "all"},
    )
    request_group = EsiRequestGroup(
        requests={market_orders_request.request_id: market_orders_request}
    )

    async def fetch_market_orders():
        async with EsiLink(
            auth_manager_db_path=auth_manager_db_path,
            web_cache_path=web_cache_path,
            max_rate=max_rate,
            time_period=time_period,
        ) as esi_link:
            market_orders = await esi_link.make_requests(
                esi_requests=request_group, schema=esi_schema
            )
            return market_orders

    response = asyncio.run(fetch_market_orders())
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


def fetch_esi_schema() -> EsiSchema:
    """Fetch the latest ESI schema from the EVE Online API."""
    with client_manager(USER_AGENT) as session:
        compatibility_date = latest_schema_date()
        timestamped_schema = fetch_schema(
            session=session, schema_as_of=compatibility_date
        )
        esi_schema = EsiSchema.from_raw_schema(
            raw_schema=timestamped_schema.schema,
            timestamp=timestamped_schema.timestamp,
        )
    return esi_schema


if __name__ == "__main__":
    app()
