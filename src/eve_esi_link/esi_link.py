"""Hold the EsiLink class."""

from pathlib import Path
from types import TracebackType

from api_request import ApiRequester
from api_request.cache import SqliteCacheFactory
from api_request.rate_limit import AiolimiterRateLimiterFactory
from eve_auth_manager.sqlite.manager import SqliteAuthManager

from eve_esi_link.esi_request.models import EsiRequests, EsiResponses
from eve_esi_link.schema.models import EsiSchema


class EsiLink:
    def __init__(
        self,
        auth_manager_db_path: Path,
        web_cache_path: Path,
        max_rate: float = 20.0,
        time_period: float = 1.0,
    ):
        """Initialize the EsiLink class.

        Args:
            auth_manager_db_path (Path): The path to the database file for the SqliteAuthManager.
            web_cache_path (Path): The path to the web cache.
            max_rate (float): The maximum number of requests per time period.
            time_period (float): The time period for rate limiting in seconds.
        """
        self.api_requester: ApiRequester | None = None
        self.auth_manager: SqliteAuthManager | None = None
        self.auth_manager_db_path = auth_manager_db_path
        self.web_cache_path = web_cache_path
        self.max_rate = max_rate
        self.time_period = time_period

    async def _aenter__(self):
        """Async context manager entry point."""
        web_cache_factory = SqliteCacheFactory(db_path=self.web_cache_path)
        rate_limiter_factory = AiolimiterRateLimiterFactory(
            max_rate=self.max_rate, time_period=self.time_period
        )
        self.api_requester = ApiRequester(
            cache_factory=web_cache_factory, rate_limiter_factory=rate_limiter_factory
        )
        self.auth_manager = SqliteAuthManager(db_path=self.auth_manager_db_path)
        await self.api_requester.__aenter__()
        self.auth_manager.__enter__()
        return self

    async def _aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ):
        """Async context manager exit point."""
        if self.api_requester is not None:
            await self.api_requester.__aexit__(exc_type, exc_value, traceback)
        if self.auth_manager is not None:
            self.auth_manager.__exit__(exc_type, exc_value, traceback)

    async def do_requests(
        self, requests: EsiRequests, schema: EsiSchema
    ) -> EsiResponses:
        """Perform the given ESI requests and return the responses.

        Args:
            requests (EsiRequests): The ESI requests to perform.
            schema (EsiSchema): The schema to use for the requests.

        Returns:
            EsiResponses: The responses from the ESI requests.
        """
        ...
