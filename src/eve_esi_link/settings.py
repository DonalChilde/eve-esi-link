"""Settings module for the Eve ESI Link application."""

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import NAMESPACE_DNS, uuid5

from pydantic_settings import BaseSettings, SettingsConfigDict
from typer import get_app_dir

from eve_esi_link import __app_name__, __project_namespace__, __url__, __version__

logger = logging.getLogger(__name__)

COMPATIBILITY_DATES_URL = "https://esi.evetech.net/meta/compatibility-dates"
"""URL to fetch the list of compatibility dates from the ESI API."""
ESI_SCHEMA_URL = "https://esi.evetech.net/meta/openapi.json"
"""URL to fetch ESI OpenAPI schema."""
USER_AGENT = f"{__app_name__}/{__version__} ({__url__})"
APP_DOMAIN = f"{__project_namespace__}.{__app_name__}"
APP_NAMESPACE = uuid5(NAMESPACE_DNS, APP_DOMAIN)
ENV_PREFIX = APP_DOMAIN.replace(".", "_").replace("-", "_").upper() + "_"
SETTINGS_KEY = ENV_PREFIX + "SETTINGS"


@dataclass(slots=True, kw_only=True)
class EsiLinkSettings:
    """Configuration settings for the Eve ESI Link application."""

    application_directory: Path
    logging_directory: Path
    schema_cache_directory: Path
    # Eve Auth Manager settings
    auth_manager_db_file: Path
    # API Request settings
    api_request_cache_file: Path
    max_rate: float = 50.0
    time_period: float = 1.0


class EsiLinkSettingsPydantic(BaseSettings):
    """Pydantic-based configuration settings for the Eve ESI Link application."""

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_file=(".env", ".env.dev"),
        env_file_encoding="utf-8",
    )

    application_directory: Path = Path(get_app_dir(__app_name__))


def get_settings() -> EsiLinkSettings:
    """Retrieve the Eve ESI Link application settings.

    Returns:
        EsiLinkSettings: The resolved application settings.
    """
    logger.info("Loading settings from environment variables...")
    logger.info(f"Environment variable prefix: {ENV_PREFIX}")
    pydantic_settings = EsiLinkSettingsPydantic()
    logger.info(
        f"Loaded settings from environment variables: {pydantic_settings.model_dump()}"
    )
    application_directory = pydantic_settings.application_directory.resolve()
    if not application_directory.exists():
        application_directory.mkdir(parents=True, exist_ok=True)
    settings = EsiLinkSettings(
        application_directory=application_directory,
        logging_directory=application_directory / "logs",
        schema_cache_directory=application_directory / "schema_cache",
        api_request_cache_file=application_directory / "api_requests_web_cache.sqlite",
        auth_manager_db_file=application_directory / "eve_auth_manager.sqlite",
    )
    logger.info(f"Resolved application settings: {asdict(settings)}")
    return settings
