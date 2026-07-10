import logging

from ..language import LangEnum
from ..schema.models import EsiSchema, SchemaOperation
from .models import EsiAuthorization, EsiRequest

logger = logging.getLogger(__name__)


# TODO: Validate an EsiRequest against an EsiSchema.
# This validation stage is for the user submitted EsiRequest. Runtimeinformation has not been set.
# This will be used to validate requests before they are sent to the ESI API.
# The validation will check:
# - The operation_id is valid for the given EsiSchema,
# - that the request has all required parameters,
# - that the parameters are of the correct type
# - that the request is valid
# - that the page parameter is not set, even for paged requests, as this is handled automatically by the esi-link.
# - If headers are set, only the allowed headers are set, and that they are of the correct type.
# - If authorization is required, that the EsiAuthorization is set, but not the access token.
#
# Implement validation functions such that it is easy to add more.
# Add ValidationErrors as needed for clarity, but value simplicity over verbosity.
# - Validation errors will be used to provide feedback to the user, and should be clear, concise, and useful!
# Log as needed to help with debugging.


class EsiRequestValidationError(Exception):
    """Base class for ESI request validation errors."""


def validate_esi_request(
    esi_request: EsiRequest,
    esi_schema: EsiSchema,
    require_access_token: bool = False,
) -> None: ...
