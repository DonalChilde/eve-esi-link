# Eve Esi Link

Eve Esi Link provides a simple, scriptable cli and api to access the Eve Online ESI.

Features:
- Authenticated requests
- Get character id by name.
- Caching
- Paged request handling
- Async requests
- Rate Limiting
- A pipeable cli
- An Api for use as a library.
- Generated documentation for the ESI schema.

## Project Status

Stabilizing... Functionality should not revert, but details may still change.

## Requirements

- Python 3.14+
- uv (recommended)

## Links To More Information

- [ESI Api Explorer](https://developers.eveonline.com/api-explorer)
- [ESI Application Portal](https://developers.eveonline.com/applications)
- [EVE Online 3rd party developer docs](https://developers.eveonline.com/docs/)

## Installation

### From pypi

    **Not Yet Available**

### From source (recommended for development)

```bash
git clone https://github.com/DonalChilde/eve-esi-link
cd eve-esi-link
uv sync
source ./.venv/bin/activate
eve-link --help
```

Run the CLI from source:

```bash
uv run eve-link --help
```

### Run directly from GitHub with uv (no clone)

Run once:

```bash
uvx --from git+https://github.com/DonalChilde/eve-esi-link eve-link --help
```

Install as a uv-managed tool:

```bash
uv tool install git+https://github.com/DonalChilde/eve-esi-link
eve-link --help
```

## Quick Start
```bash
# Use the appropriate command format for your install
eve-link schema cache update --all
eve-link schema generate-doc --to ./schema-doc.md
eve-link samples --to ./sample-requests/
eve-link run --from ./sample-requests/status.request.json
```

## Schemas
First, cache the available ESI schemas
```bash
eve-link schema cache update --all
```
This will download and store all the available schemas. Commands that use schemas can load these stored schemas automatically, or an external schema specified on the command line.

Then, generate a markdown report on the latest schema
```bash
eve-link schema generate-doc --to ./schema-docs.md
```
Note: if you have a compatible editor, like vscode, you can view the markdown file as a webpage, for easier navigation.

The schema report will help you find operations, and the parameters needed to make them into requests.

## Authentication

### Create `credentials.json` from EVE Developers

1. Go to https://developers.eveonline.com/applications and sign in.
2. Create a new ESI application, or open an existing one. Selecting all scopes is recommended.
3. Copy/paste the application JSON payload from the portal to a file.
4. Save it locally as `credentials.json`.

Expected JSON shape:

```json
{
  "name": "My ESI App",
  "description": "Optional human-readable description",
  "clientId": "your_client_id",
  "clientSecret": "your_client_secret",
  "callbackUrl": "http://localhost:8080/callback",
  "scopes": ["scope1", "scope2"]
}
```

### Add Credentials and Authorize a Character

Add your app credentials to the eve-link auth store
```bash
eve-link auth-manager credentials add --from ./credentials.json
eve-link auth-manager credentials display
```

To add a character to the auth store, you need the character id. You can look it up with
```bash
eve-link auth-manager characters search --name "My Cool Name"
```
This actually searches all in game names, so
```bash
eve-link auth-manager characters search --name "Tritanium"
```
gets back a character, and a mineral.

Now, authorize the character
```bash
eve-link auth-manager characters add <character_id> --cred-name "My App Name"
eve-link auth-manager characters display
```

    Note eve-link should support multiple separate sets of credential and characters, but it hasnt been tested.
## Performance

### Rate Limiting

***TODO Explain the current rate limiting scheme, and how to change settings.***

### Concurrent Requests

Requests are made using httpx2's asyncio support. This means that within the eve-link ratelimiting scheme, requests are made all at once. This can make a huge difference even with single EsiRequests, because many of the endpoints are paged. Internally, those pages are turned into requests themselves, and fetched at the same time. The combined pages are then all return as one response. For example, the region of space with Jita might have 400 or more pages of market order data. At about .5 seconds per page, that would take over 3 minutes. But making concurrent requests cuts that time down dramatically. The ESI api does not rate limit by successful request (Though that is changing) but still, please don't ddos the servers. Keep resonable rate limit settings.

### Caching

eve-link caches GET requests, so the same request may return cached data if it has not expired. This can also be a huge time saver, and can simplify data retrieval strategies. The cache could be treated just like a database (it is) and requests can be made as often as desired. Network calls will only be made if the data has not been cached, or the cache is stale.

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
  "operation_id": "GetStatus",
}
```
This request has no required parameters, so only some values are needed. You could make this one even simpler, since name and description are optional:
```json
{
  "operation_id": "GetStatus",
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
  },
}
 ```

 and one that requires authentication would look like:
 ```json
{
    "request_id": "6cc16cd0-11d3-4eec-890e-a0356c665806",
    "name": "Character Attributes request",
    "description": "Retrieve the attributes of a specific character.",
    "operation_id": "GetCharactersCharacterIdAttributes",
    "path_parameters": {"character_id": 93118551},
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
      },
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
      },
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

### Making Requests

To make a single request, you might run
```bash
eve-link run --from ./status.request.json
```
This results in 
```json
{"players": 25236, "server_version": "3435006", "start_time": "2026-07-15T11:03:27Z"}
```
Because no schema was specified, the most recent cached schema was used. You should update the cached schemas when new ones come available.

You can also pipe the request json into the command
```bash
cat ./status.request.json | eve-link run
```

This can be useful when integrating with other scripts.

output can also be saved to a file, or piped
```bash
cat ./status.request.json | eve-link run --to ./status-response.json
# or
cat ./status.request.json | eve-link run | foo-do-something
```
For a single EsiRequest, the --debug flag will output the complete EsiResonse object
```bash
eve-link run --from ./status.request.json --debug --indent 2
```

EsiRequestGroup operates the same way, except that the output is always the complete EsiResponseGroup object. The expectation is, that group requests will normally be post processed by the user, so no assumptions are made about desired output format.

An example EsiRequestGroup
```bash
eve-link run-group --from ./languages.request-group.json --indent 2
```

## Api Usage

***TODO***

## Contributing

Lets be honest. This has been a miracle of monkeys pounding on typewriters to get this far. While I would love to say "bring on your code!", I still have not figured out how to make that work. So, ideas and suggestions are great! Bug reports and problems, that too! But.... It will take a bit for me to sort that out.