"""Factory module for creating instances of EsiLink."""

from eve_esi_link import EsiLink
from eve_esi_link.settings import EsiLinkSettings


def esi_link_factory(settings: EsiLinkSettings) -> EsiLink:
    """Factory function to create an instance of EsiLink.

    Args:
        settings (EsiLinkSettings): The application settings.

    Returns:
        EsiLink: An instance of the EsiLink class.
    """
    return EsiLink(
        auth_manager_db_path=settings.auth_manager_db_file,
        web_cache_path=settings.api_request_cache_file,
        max_rate=settings.max_rate,
        time_period=settings.time_period,
    )
