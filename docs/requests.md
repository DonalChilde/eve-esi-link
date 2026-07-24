## Requests

eve-link requests are defined internally by two python dataclasses -

```python
@dataclass(slots=True, kw_only=True)
class EsiRequest:
    """Represents a single ESI request to be executed.

    Can be loaded from a file or created programmatically. The request_id is used to
    identify the request.

    Requests can be be contained in a RequestGroup, and the request_id is used
    to link the Request to its RuntimeRequest, and to the final EsiResponse.
    """

    request_id: UUID = field(default_factory=uuid4)
    """The unique identifier for the request. This is used to link the request to various
        objects during the request lifecycle."""
    name: str | None = None
    """An optional name for the request. This is used for documentation purposes,
        and can be used to provide context for the request when viewing it in a UI or in
        logs."""
    description: str | None = None
    """An optional description of the request. This is used for documentation purposes,
        and can be used to provide context for the request when viewing it in a UI or in
        logs."""
    operation_id: str
    """The operation ID of the request, corresponding to the operationId in the ESI
        OpenAPI schema."""
    path_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The path parameters for the request, if applicable. This is used to fill in the
        path parameters in the URL template."""
    query_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The query parameters for the request, if applicable.

    This is used to fill in the query parameters in the URL template.

    NOTE: The page parameter is handled automatically by eve-link, and should not
        be set manually. If it is set, it will raise a validation error. This is to help
        normalize cache keys, which rely on predictable parameters.
    """
    header_parameters: dict[str, str] = field(default_factory=dict[str, str])
    """The header parameters for the request, if applicable.

        Acceptable headers are:
        - Accept-Language
        - X-Tenant
        - X-Compatibility-Date

        Do not use this to set:

        - If-None-Match
        - If-Modified-Since headers.

        Those are set at runtime during HTTP execution."""
    json_payload: Any | None = None
    """The JSON payload of the request, if applicable. This is used for POST, PUT, and PATCH
        requests."""
    character_id: int | None = None
    """The character ID used for authorization."""
    credential_id: UUID | None = None
    """The credential ID for authorization. This is used to link the authorization
        to the credential that was used to obtain it. This UUID is obtained from the
        credential manager that provides the access token."""

@dataclass(slots=True, kw_only=True)
class EsiRequestGroup:
    name: str | None = None
    """The name of this group of runtime ESI requests."""
    description: str | None = None
    """An optional description of this group of runtime ESI requests."""
    requests: dict[UUID, EsiRequest] = field(default_factory=dict[UUID, EsiRequest])
    """The dict of  ESI requests in this group."""
```

When you are working from the command line, you will be using json representations of these dataclasses. This json is loaded by eve-link, validated, and the requests are made.

### EsiRequest

A complete EsiRequest object might look something like this

```json
{
  "request_id": "THIS_IS_A_UUID_OPTIONAL_WHEN_LOADED_FROM_JSON",
  "name": "THIS_IS_AN_OPTIONAL_NAME",
  "description": "THIS_IS_AN_OPTIONAL_DESCRIPTION",
  "operation_id": "THIS_IS_AN_OPERATION_ID",
  "path_parameters": {},
  "query_parameters": {},
  "header_parameters": {},
  "character_id": "THIS_IS_INT_OR_NONE_IS_NONE_IF_THE_REQUEST_IS_PUBLIC",
  "credential_id": "THIS_IS_UUID_OR_NONE_IS_NONE_IF_THE_REQUEST_IS_PUBLIC",
  "json_payload": null
}
```

while a EsiRequestGroup looks like this

```json
{
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
      "json_payload": null
    },
    "THIS_IS_A_UUID_2": {
      "request_id": "THIS_IS_A_UUID_2",
      "name": "THIS_IS_AN_OPTIONAL_NAME",
      "description": "THIS_IS_AN_OPTIONAL_DESCRIPTION",
      "operation_id": "THIS_IS_AN_OPERATION_ID",
      "path_parameters": {},
      "query_parameters": {},
      "header_parameters": {},
      "character_id": "THIS_IS_INT_OR_NONE_IS_NONE_IF_THE_REQUEST_IS_PUBLIC",
      "credential_id": "THIS_IS_UUID_OR_NONE_IS_NONE_IF_THE_REQUEST_IS_PUBLIC",
      "json_payload": null
    }
  }
}
```

Fields that are not required can be omited from the json.

If you are making just one request, you can use an EsiRequest. The simplest one looks like

```json
{
  "name": "Get Status",
  "description": "Get the server status and player count.",
  "operation_id": "GetStatus"
}
```

This request has no required parameters, so only some values are needed. You could make this one even simpler, since name and description are optional:

```json
{
  "operation_id": "GetStatus"
}
```

Note, that for an EsiRequest, a request_id will be generated automatically during deserialization, and used internally. It is usually not important to the user, because there is only one request/response, and there is no need to be able to tell different requests apart.

A request that uses parameters might look like:

```json
{
  "name": "Get Markets Region Id History",
  "description": "Retrieves the market history for a specific region and type.",
  "operation_id": "GetMarketsRegionIdHistory",
  "path_parameters": {
    "region_id": 10000002
  },
  "query_parameters": {
    "type_id": 34
  }
}
```

and one that requires authentication would look like:

```json
{
  "request_id": "6cc16cd0-11d3-4eec-890e-a0356c665806",
  "name": "Character Attributes request",
  "description": "Retrieve the attributes of a specific character.",
  "operation_id": "GetCharactersCharacterIdAttributes",
  "path_parameters": { "character_id": 93118551 },
  "query_parameters": {},
  "header_parameters": {},
  "character_id": 93118551,
  "credential_id": "4dbfbc12-5238-5961-8c42-cb1ffd121851",
  "json_payload": null
}
```

Note that character_id is used twice, once as a required path parameter, and once as part of the authentication request fields

### EsiRequestGroup

An EsiRequestGroup has one or more requests inside:

```json
{
  "name": "Get type information in two languages",
  "description": "Retrieve information about a specific universe type in multiple languages.",
  "requests": {
    "86ee7395-2de1-4f15-ae0e-6dca9b7e9c5d": {
      "request_id": "86ee7395-2de1-4f15-ae0e-6dca9b7e9c5d",
      "name": "Universe Types Type ID request",
      "description": "Retrieve information about a specific universe type.",
      "operation_id": "GetUniverseTypesTypeId",
      "path_parameters": {
        "type_id": 34
      }
    },
    "d2eb2728-93d9-4ee0-9ba6-939acc04d9b4": {
      "request_id": "d2eb2728-93d9-4ee0-9ba6-939acc04d9b4",
      "name": "Universe Types Type ID request",
      "description": "Retrieve information about a specific universe type. In Spanish.",
      "operation_id": "GetUniverseTypesTypeId",
      "path_parameters": {
        "type_id": 34
      },
      "header_parameters": {
        "accept-language": "es"
      }
    }
  }
}
```

Note the use of a header parameter to get a response in another language.
The default request language is English, `en`.

Also note the presence of the UUIDs in the json. Because there is more than one request in a group, there has to be a way to tell them part - they have to have a unique name.

Uuids can be generated on the command line, and then copy/pasted into the json.

```bash
eve-link uuid --qty 5
```

produces

```bash
[
   '2aa2edf9-6443-4bfd-824c-938d98496894',
   '6c2e869e-04d7-43bc-8957-4e063ae4e169',
   '01b459e1-42ad-4e5d-9bb8-453b64641f4d',
   '5cf162f9-f465-4570-aee3-a88bc39eb5b9',
   'ed94d33f-7051-49f3-b90d-f7bde1eb064a'
]
```
