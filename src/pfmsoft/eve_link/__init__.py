"""eve-esi-link package.

CLI and library interface for working with EVE Online ESI.

For library usage, EsiLink is the primary entrypoint. See:
- docs/esi-link-library-contracts.md
- docs/esi-request-package-contracts.md
- docs/schema-package-contracts.md
"""

from importlib.metadata import version

__project_namespace__ = "pfmsoft"
__author__ = "Chad Lowe"
__email__ = "pfmsoft.dev@gmail.com"
__app_name__ = "pfmsoft-eve-link"
__description__ = "A command line first interface to the Eve Online ESI API"
__version__ = version(__app_name__)
__release__ = __version__
__url__ = "https://github.com/DonalChilde/pfmsoft-eve-link"
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
