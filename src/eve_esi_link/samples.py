"""Generate sample EsiRequestGroup objects for testing and demonstration purposes."""

from collections.abc import Callable
from pathlib import Path
from uuid import UUID, uuid4

from eve_esi_link.esi_request.models import (
    EsiRequest,
    EsiRequestGroup,
    EsiRequestGroupRoot,
)
from eve_esi_link.helpers.save_text_file import save_text_file


def auth(character_id: int, credential_id: UUID) -> EsiRequestGroup:
    """Generate an EsiRequestGroup with a single authenticated request."""
    request_key = uuid4()
    request = EsiRequestGroup(
        name="Character Attributes Request",
        description="Request to fetch character attributes for a specific character.",
        requests={
            request_key: EsiRequest(
                name="Get Character Attributes",
                description="Fetches the attributes of a character.",
                operation_id="GetCharactersCharacterIdAttributes",
                path_parameters={"character_id": character_id},
                credential_id=credential_id,
                character_id=character_id,
            )
        },
    )
    return request


def lang() -> EsiRequestGroup:
    """Generate an EsiRequestGroup with two requests for the same operation in different languages."""
    request_key_1 = uuid4()
    request_key_2 = uuid4()
    request_group = EsiRequestGroup(
        name="Get type information in two languages",
        description="Retrieve information about a specific universe type in multiple languages.",
        requests={
            request_key_1: EsiRequest(
                request_id=request_key_1,
                name="Universe Types Type ID request",
                description="Retrieve information about a specific universe type.",
                operation_id="GetUniverseTypesTypeId",
                path_parameters={"type_id": 34},
            ),
            request_key_2: EsiRequest(
                request_id=request_key_2,
                name="Universe Types Type ID request",
                description="Retrieve information about a specific universe type. In Spanish.",
                operation_id="GetUniverseTypesTypeId",
                path_parameters={"type_id": 34},
                header_parameters={"accept-language": "es"},
            ),
        },
    )
    return request_group


def paged() -> EsiRequestGroup:
    """Generate an EsiRequestGroup with a single paged request."""
    request_key = uuid4()
    request_group = EsiRequestGroup(
        name="Universe types",
        description="A single paged request that retrieves a list of universe types.",
        requests={
            request_key: EsiRequest(
                request_id=request_key,
                name="Get Universe Types",
                description="Gets a list of the universe types.",
                operation_id="GetUniverseTypes",
                path_parameters={},
                query_parameters={},
                header_parameters={},
            )
        },
    )
    return request_group


def params() -> EsiRequestGroup:
    """Generate an EsiRequestGroup with a single request that includes path and query parameters."""
    request_key = uuid4()
    request_group = EsiRequestGroup(
        name="Request with Parameters",
        description="An example request that includes both path and query parameters.",
        requests={
            request_key: EsiRequest(
                request_id=request_key,
                name="Get Markets Region Id History",
                description="Retrieves the market history for a specific region and type.",
                operation_id="GetMarketsRegionIdHistory",
                path_parameters={"region_id": 10000002},
                query_parameters={"type_id": 34},
            )
        },
    )
    return request_group


def post_names() -> EsiRequestGroup:
    """Generate an EsiRequestGroup with a single POST request."""
    request_key = uuid4()
    request_group = EsiRequestGroup(
        name="Post Universe Names",
        description="Post universe names for the specified IDs.",
        requests={
            request_key: EsiRequest(
                request_id=request_key,
                name="Post Universe Names",
                description="Post universe names for the specified IDs.",
                operation_id="PostUniverseNames",
                json_payload=[34, 10000002],
            )
        },
    )
    return request_group


def status() -> EsiRequestGroup:
    """Generate an EsiRequestGroup with a single request to get the server status."""
    request_key = uuid4()
    request_group = EsiRequestGroup(
        name="Status Example",
        description="This is a functional example of making a single request to get the server status and player count.",
        requests={
            request_key: EsiRequest(
                request_id=request_key,
                name="Get Status",
                description="Get the server status and player count.",
                operation_id="GetStatus",
                path_parameters={},
                query_parameters={},
                header_parameters={},
            )
        },
    )
    return request_group


def export_examples(
    output_directory: Path, *, indent: int | None = 2, overwrite: bool = False
) -> None:
    """Exportexample EsiRequestGroupRoot objects to JSON files in the specified directory.

    These examples are useful for testing and demonstration purposes, showcasing various
    request types and configurations. An authorized request is not included in the
    exported examples, as it requires valid credentials.
    """
    output_directory.mkdir(parents=True, exist_ok=True)
    sample_generators: list[tuple[str, Callable[[], EsiRequestGroup]]] = [
        ("params.json", params),
        ("post_names.json", post_names),
        ("status.json", status),
        ("lang.json", lang),
        ("paged.json", paged),
    ]
    for filename, generator in sample_generators:
        request_group = generator()
        output_text = EsiRequestGroupRoot(root=request_group).model_dump_json(
            indent=indent
        )
        save_text_file(
            text=output_text + "\n",
            output_directory=output_directory,
            file_name=filename,
            overwrite=overwrite,
        )
