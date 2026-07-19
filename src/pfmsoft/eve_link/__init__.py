"""eve-esi-link package.

CLI and library interface for working with EVE Online ESI.

For library usage, EsiLink is the primary entrypoint. See:
- docs/esi-link-library-contracts.md
- docs/esi-request-package-contracts.md
- docs/schema-package-contracts.md
"""

__project_namespace__ = "pfmsoft"
__author__ = "Chad Lowe"
__email__ = "pfmsoft.dev@gmail.com"
__app_name__ = "eve-esi-link"
#######################################################################################
# Update in pyproject.toml, as uv build backend does not yet support dynamic metadata #
# https://github.com/astral-sh/uv/issues/11718                                        #
#######################################################################################
__description__ = "A command line first interface to the Eve Online API"
__version__ = "0.4.0"
__release__ = __version__
#######################################################################################
__url__ = "https://github.com/DonalChilde/eve-esi-link"
__license__ = "MIT"


from pfmsoft.eve_link.esi_link import EsiLink
from pfmsoft.eve_link.esi_request.models import (
    EsiRequest,
    EsiRequestGroup,
    EsiResponse,
    EsiResponseGroup,
)
from pfmsoft.eve_link.schema.models import EsiSchema

__all__ = [
    "EsiLink",
    "EsiRequest",
    "EsiRequestGroup",
    "EsiResponse",
    "EsiResponseGroup",
    "EsiSchema",
]
