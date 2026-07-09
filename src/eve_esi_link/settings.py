"""Settings module for the Eve ESI Link application."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from typer import get_app_dir

from eve_esi_link import __app_name__, __url__, __version__


@dataclass(slots=True, kw_only=True)
class EsiLinkSettings:
    """Configuration settings for the Eve ESI Link application."""

    application_directory: Path
    logging_directory: Path


@dataclass(slots=True, kw_only=True)
class EsiLinkSettingsPydantic(BaseSettings):
    """Pydantic-based configuration settings for the Eve ESI Link application."""

    model_config = SettingsConfigDict(
        env_prefix="EVE_ESI_LINK_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    application_directory: Path = Path(get_app_dir(__app_name__))
    logging_directory: Path = application_directory / "logs"


def get_settings() -> EsiLinkSettings:
    """Retrieve the Eve ESI Link application settings.

    Returns:
        EsiLinkSettings: The resolved application settings.
    """
    pydantic_settings = EsiLinkSettingsPydantic()
    return EsiLinkSettings(
        application_directory=pydantic_settings.application_directory,
        logging_directory=pydantic_settings.logging_directory,
    )
