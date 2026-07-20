"""Generate sample EsiRequestGroup objects for testing and demonstration purposes."""

from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pfmsoft.eve_snippets import json_io, save_text_file

from pfmsoft.eve_link.esi_request.models import (
    EsiRequest,
    EsiRequestGroup,
    EsiRequestGroupRoot,
    EsiRequestRoot,
)


def auth(character_id: int, credential_id: UUID) -> tuple[EsiRequest, str]:
    """Generate an EsiRequestGroup with a single authenticated request."""
    request_key = uuid4()
    request = EsiRequest(
        request_id=request_key,
        name="Get Character Attributes",
        description="Fetches the attributes of a character.",
        operation_id="GetCharactersCharacterIdAttributes",
        path_parameters={"character_id": character_id},
        credential_id=credential_id,
        character_id=character_id,
    )
    return request, "authorized.request.json"


def lang() -> tuple[EsiRequestGroup, str]:
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
    return request_group, "languages.request-group.json"


def paged() -> tuple[EsiRequest, str]:
    """Generate an EsiRequestGroup with a single paged request."""
    request_key = uuid4()
    request_group = EsiRequest(
        request_id=request_key,
        name="Get Universe Types",
        description="Gets a list of the universe types.",
        operation_id="GetUniverseTypes",
        path_parameters={},
        query_parameters={},
        header_parameters={},
    )

    return request_group, "paged.request.json"


def params() -> tuple[EsiRequest, str]:
    """Generate an EsiRequestGroup with a single request that includes path and query parameters."""
    request_key = uuid4()
    request_group = EsiRequest(
        request_id=request_key,
        name="Get Markets Region Id History",
        description="Retrieves the market history for a specific region and type.",
        operation_id="GetMarketsRegionIdHistory",
        path_parameters={"region_id": 10000002},
        query_parameters={"type_id": 34},
    )

    return request_group, "parameters.request.json"


def post_names() -> tuple[EsiRequest, str]:
    """Generate an EsiRequestGroup with a single POST request."""
    request_key = uuid4()
    request_group = EsiRequest(
        request_id=request_key,
        name="Post Universe Names",
        description="Post universe names for the specified IDs.",
        operation_id="PostUniverseNames",
        json_payload=[34, 10000002],
    )

    return request_group, "post_names.request.json"


def status() -> tuple[EsiRequest, str]:
    """Generate an EsiRequestGroup with a single request to get the server status."""
    request_key = uuid4()
    request_group = EsiRequest(
        request_id=request_key,
        name="Get Status",
        description="Get the server status and player count.",
        operation_id="GetStatus",
    )

    return request_group, "status.request.json"


TEMPLATE_GROUP_JSON: dict[str, Any] = {
    "name": "THIS_IS_AN_OPTIONAL_NAME",
    "description": "THIS_IS_AN_OPTIONAL_DESCRIPTION",
    "requests": {
        "THIS_IS_A_UUID": {
            "request_id": "THIS_IS_A_UUID",
            "name": "THIS_IS_AN_OPTIONAL_NAME",
            "description": "THIS_IS_AN_OPTIONAL_DESCRIPTION",
            "operation_id": "THIS_IS_AN_OPERATION_ID",
            "path_parameters": {},
            "query_parameters": {},
            "header_parameters": {},
            "character_id": "THIS_IS_INT_OR_NONE_IS_NONE_IF_THE_REQUEST_IS_PUBLIC",
            "credential_id": "THIS_IS_UUID_OR_NONE_IS_NONE_IF_THE_REQUEST_IS_PUBLIC",
            "json_payload": None,
        }
    },
}

TEMPLATE_REQUEST_JSON: dict[str, Any] = {
    "request_id": "THIS_IS_A_UUID_OPTIONAL_WHEN_LOADED_FROM_JSON",
    "name": "THIS_IS_AN_OPTIONAL_NAME",
    "description": "THIS_IS_AN_OPTIONAL_DESCRIPTION",
    "operation_id": "THIS_IS_AN_OPERATION_ID",
    "path_parameters": {},
    "query_parameters": {},
    "header_parameters": {},
    "character_id": "THIS_IS_INT_OR_NONE_IS_NONE_IF_THE_REQUEST_IS_PUBLIC",
    "credential_id": "THIS_IS_UUID_OR_NONE_IS_NONE_IF_THE_REQUEST_IS_PUBLIC",
    "json_payload": None,
}


def export_examples(
    output_directory: Path, *, indent: int | None = 2, overwrite: bool = False
) -> None:
    """Exportexample EsiRequestGroupRoot objects to JSON files in the specified directory.

    These examples are useful for testing and demonstration purposes, showcasing various
    request types and configurations. An authorized request is not included in the
    exported examples, as it requires valid credentials.
    """
    output_directory.mkdir(parents=True, exist_ok=True)
    sample_generators: list[
        Callable[[], tuple[EsiRequestGroup, str]] | Callable[[], tuple[EsiRequest, str]]
    ] = [post_names, status, lang, paged, params]
    for generator in sample_generators:
        request_obj, filename = generator()
        if isinstance(request_obj, EsiRequestGroup):
            output_text = EsiRequestGroupRoot(root=request_obj).model_dump_json(
                indent=indent
            )
        elif isinstance(request_obj, EsiRequest):  # type: ignore
            output_text = EsiRequestRoot(root=request_obj).model_dump_json(
                indent=indent
            )
        else:
            raise ValueError("Unknown object")
        save_text_file(
            text=output_text,
            directory=output_directory,
            filename=filename,
            overwrite=overwrite,
        )
    save_text_file(
        text=json_io.json_dumps(TEMPLATE_GROUP_JSON, indent=indent),
        directory=output_directory,
        filename="template.request-group.json",
        overwrite=overwrite,
    )
    save_text_file(
        text=json_io.json_dumps(TEMPLATE_REQUEST_JSON, indent=indent),
        directory=output_directory,
        filename="template.request.json",
        overwrite=overwrite,
    )
