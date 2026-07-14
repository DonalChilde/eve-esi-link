# eve_esi_link.esi_request package: behavior and contracts

This document defines the current, code-observed contracts for the
`eve_esi_link.esi_request` subsystem.

## Audience

- Contributors implementing request execution features.
- Integrators creating request JSON payloads and reading response output.

## Package purpose

The esi_request subsystem provides three layers:

1. Request/response data models used by CLI and library flows.
2. Runtime transformation from `EsiRequest` to executable HTTP request metadata.
3. Validation of user-supplied requests against `EsiSchema` operation constraints.

## Data model contracts

Implemented in `src/eve_esi_link/esi_request/models.py`.

### EsiRequest

`EsiRequest` is the user-facing request model.

Required:

- `operation_id`

Optional metadata:

- `request_id` (auto UUID)
- `name`
- `description`

Payload fields:

- `path_parameters`: `dict[str, str | int | float]`
- `query_parameters`: `dict[str, str | int | float]`
- `header_parameters`: `dict[str, str]`
- `json_payload`: any JSON-like value

Authorization fields:

- `character_id`: `int | None`
- `credential_id`: `UUID | None`

Derived properties:

- `has_authorization`: true only when both authorization fields are set.
- `authorization_slug`: deterministic UUID5 based on `credential_id` + `character_id`.
  - Raises `ValueError` if either value is missing.

### RuntimeEsiRequest

`RuntimeEsiRequest` is the execution-ready request representation.

Fields:

- `request_key`: deterministic UUID5 generated from app namespace + `request_id`
- `url`, `method`
- `cache_key`: UUID for cacheable operations, else `None`
- `rate_limit_key`: operation rate-limit group (or empty string)
- `headers`, `query_parameters`, `json_payload`
- `access_token`: access token loaded at runtime when needed

Security helpers:

- `purge_access_token()` redacts `access_token` to `"REDACTED"`.
- `headers_with_authorization` adds `Authorization: Bearer <token>` when token is present.

### Group/list models

Request containers:

- `EsiRequestList`: list-based request container
- `EsiRequestGroup`: UUID-keyed request container

Response containers:

- `EsiResponseList`: list-style response container + `purge_tokens()`
- `EsiResponseGroup`: group-style response container + `serialize(indent=None)`

`EsiResponseGroup.serialize()` behavior:

- Creates a deep copy.
- Purges `RuntimeEsiRequest.access_token` values from successful/failed responses.
- Serializes with `EsiResponseGroupRoot(...).model_dump_json(...)`.

## Runtime builder contracts

Implemented in `src/eve_esi_link/esi_request/runtime_builder.py`.

`build_runtime_esi_request(esi_request, esi_schema)` performs:

1. Resolve operation from schema by `operation_id`.
   - Raises `ValueError` if operation is unknown.
2. Build URL from schema operation template + `path_parameters`.
3. Set HTTP method from schema operation.
4. Set `rate_limit_key` from `x-rate-limit.group` when present, else empty string.
5. Normalize headers to lowercase and apply defaults when missing:
   - `accept-language=en`
   - `x-tenant=tranquility`
   - `x-compatibility-date=<schema.compatibility_date>`
6. Copy query parameters and inject `page=1` for paged operations when page omitted.
7. Compute cache key only for cacheable operations (`GET`).

Cache-key components:

- method
- canonicalized URL (path + sorted query)
- authorization slug (if authorized)
- compatibility date
- accept-language

Non-cacheable operations set `cache_key=None`.

## Validation contracts

Implemented in `src/eve_esi_link/esi_request/validate.py`.

`validate_esi_request(esi_request, esi_schema)` raises
`EsiRequestValidationErrors` when any rule fails.

Validation scope:

1. Operation existence:
   - `operation_id` must be present in schema.
2. Path/query params:
   - Unknown parameters rejected.
   - Missing required parameters rejected.
   - Primitive type and enum checks applied.
3. Pagination rule:
   - User must not supply query `page`; pagination is runtime-managed.
4. Headers:
   - Header names must be allowed by operation header params.
   - Runtime-managed headers are rejected when user-supplied:
     - `If-None-Match`
     - `If-Modified-Since`
   - `Accept-Language` must be one of known `LangEnum` values.
5. Authorization:
   - For non-auth operations, both auth fields must be `None`.
   - For auth-required operations:
     - `character_id` must be int (not bool)
     - `credential_id` must be UUID
6. Request body:
   - Enforces requestBody required/optional behavior.
   - Supports validation only for `application/json` content type.
   - Uses subset schema validation for type, enum, object, array,
     `required`, and `additionalProperties`.
   - Explicitly rejects unsupported schema keywords:
     - `$ref`, `oneOf`, `allOf`, `anyOf`, `not`

Error model:

- Individual messages are normalized as
  `operation_id=<id>: <message>`.
- `EsiRequestValidationErrors.errors` holds message list.

## Execution + response serialization contract notes

Execution behavior is implemented by `EsiLink.make_requests` in
`src/eve_esi_link/esi_link.py`, but depends on this subsystem.

Important redaction boundary:

- `EsiResponseGroup.serialize()` redacts tokens in `esi_runtime_request.access_token`.
- Underlying `api_request` response payload redaction is not yet invoked in this
  repository (see inline FIXME comments in models).
- Treat serialized failed-response request details as potentially containing
  sensitive authorization header values until upstream response secret purging is
  wired in.

## Invariants and edge cases

- Header names are normalized to lowercase in runtime requests.
- `RuntimeEsiRequest.headers_with_authorization` can include raw bearer token if
  called before token purge.
- Cache-key stability depends on canonical URL and normalized defaults.
- Validation currently supports only a subset of OpenAPI schema keywords for JSON bodies.

## Suggested follow-up for project-wide pass

When you run the whole-project docs pass, link this contract doc from:

- top-level README subsystem map,
- request CLI command docs (`request validate`, `request run`),
- any security notes describing token handling in serialized output.
