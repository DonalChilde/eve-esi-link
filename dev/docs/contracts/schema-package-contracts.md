# eve_esi_link.schema package: behavior and contracts

This document describes the current, code-observed contracts for the
`eve_esi_link.schema` subsystem.

## Audience

- Contributors implementing schema-aware features.
- Integrators calling schema load, cache, and documentation utilities.

## Package purpose

The schema subsystem provides four capabilities:

1. Represent ESI OpenAPI data as an `EsiSchema` model with operation-level access.
2. Load schema files in several accepted JSON envelope shapes.
3. Persist and retrieve schema snapshots from a local file cache.
4. Render operation-focused markdown documentation from an `EsiSchema` instance.

## Core model contracts

### HttpMethod

`HttpMethod` is a `StrEnum` with values:

- `GET`
- `POST`
- `PUT`
- `DELETE`
- `PATCH`
- `HEAD`
- `OPTIONS`

### SchemaOperation

`SchemaOperation` is an immutable flattened view of one OpenAPI operation and has:

- `path`: OpenAPI path template (example: `/characters/{character_id}/attributes`).
- `method`: `HttpMethod`.
- `operation_schema`: the operation payload from the schema.

Important derived properties:

- `operation_id`: operation identifier string (empty string if absent).
- `path_parameters`, `query_parameters`, `header_params`: parameter subsets by `in`.
- `request_body`: request body schema metadata (or `None`).
- `responses_200`: `application/json` schema under HTTP 200 (or empty dict).
- `is_authentication_required`: true when operation contains non-empty `security`.
- `is_paged`: true when a query parameter named `page` exists.
- `is_cached`: true only for `GET` operations.
- `compatibility_date`: value of `x-compatibility-date`.
  - Raises `ValueError` if missing.

### EsiSchema

`EsiSchema` stores:

- `dereferenced_schema`: schema dictionary used by this model.
- `timestamp`: optional nanosecond fetch timestamp (`int | None`).

Post-init behavior:

- Requires top-level `openapi` key.
- Builds an operation index by `operationId`.
- Builds sorted tag -> operation-id mapping.

Important API:

- `operations`: `{operation_id: SchemaOperation}` mapping.
- `operations_id_by_tag`: `{tag: [operation_id, ...]}` mapping.
- `version`: `dereferenced_schema["info"]["version"]`.
- `compatibility_date`: alias of `version`.
- `base_url`: first server URL from `servers[0]["url"]`.
- `operation_url(operation_id)`: `base_url + path`, raises `ValueError` if unknown.
- `content_languages`: set of values from `components.headers.ContentLanguage.schema.enum`.
- `serialize(indent=None)`: JSON object with keys:
  - `dereferenced_schema`
  - `timestamp`

## Schema loading contracts

Implemented in `schema/helpers/schema_files.py`.

`load_esi_schema(schema_dict, timestamp=None)` accepts three top-level shapes:

1. OpenAPI dictionary shape
   - Must include `openapi`, `info`, `paths`, and `components` keys.
2. EsiSchemaTD shape
   - Exact keys: `{"dereferenced_schema", "timestamp"}`.
3. TimestampedSchema shape
   - Exact keys: `{"schema", "timestamp"}`.

If shape is not recognized, `ValueError` is raised.

### OpenAPI input handling

When an OpenAPI dictionary is provided to `load_esi_schema`:

- If nested `$ref` values are detected, the loader dereferences via
  `EsiSchema.from_raw_schema(raw_schema=..., timestamp=...)`.
- If no `$ref` values are detected, the loader treats input as already
  dereferenced and validates into `EsiSchema` directly.

This makes `load_esi_schema` safe for both raw and already-expanded OpenAPI
payloads.

## Fetch helper contracts

Implemented in `schema/helpers/fetch.py`.

### fetch_schema(session, schema_as_of, url=ESI_SCHEMA_URL)

- Performs GET to `url` with query parameter `compatibility_date=schema_as_of`.
- Returns `TimestampedSchema` with:
  - `schema`: `response.json()` payload.
  - `timestamp`: current `Instant.now().timestamp_nanos()`.
- Re-raises exceptions after logging.

### fetch_compatibility_dates(session)

- Performs GET to `COMPATIBILITY_DATES_URL`.
- Expects payload key `compatibility_dates`.
- Validates each date parses as `%Y-%m-%d`.
- Returns `TimestampedCompatibilityDates` with tuple values and timestamp.

## Cache contracts

Implemented in `schema/cache/__init__.py`.

### File naming convention

Recognized cache files must match:

`schema_<YYYY-MM-DD>_<timestamp|None>_esi_schema.json`

### Save semantics

`SchemaCacheManager.save(schema=...)`:

- Ensures cache directory exists.
- Deletes any existing recognized file with same compatibility date.
- Writes serialized schema to canonical filename.
- Returns `SchemaCacheEntry(compatibility_date, timestamp)`.

### Load semantics

`SchemaCacheManager.load(compatibility_date=...)`:

- Finds recognized files for that date.
- Raises `FileNotFoundError` when none exist.
- Raises `ValueError` when more than one exists.
- Returns loaded `EsiSchema` from the matching file.

### Listing and clear

- `list_entries()` returns parsed recognized entries sorted by date then timestamp.
- `clear_date(compatibility_date=...)` deletes recognized files for that date.
- `clear_all()` deletes all recognized cache files.

Unrecognized files in the cache directory are ignored by parse/load/list logic.

## Markdown documentation generator contracts

Implemented in `schema/schema_doc.py`.

`generate_esi_schema_markdown_doc(schema, download_date=None, fenced_format=JSON)`:

- Groups operations by tag (`untagged` when none).
- Produces deterministic ordering of tags and operations.
- Emits sections per operation containing:
  - summary table
  - description
  - parameters table (path/query/header)
  - request body schema
  - `200` response `application/json` schema
  - `x-*` extension block (when present)
- Normalizes final markdown with `mdformat` and table extension.

## Invariants and edge cases

- `SchemaOperation.compatibility_date` is required; missing value raises `ValueError`.
- `EsiSchema.version` assumes `info.version` exists and is a string-castable value.
- `EsiSchema.base_url` assumes at least one server entry exists.
- Operation indexing skips operations without `operationId`.
- Loader shape checks for EsiSchemaTD and TimestampedSchema are exact-key checks.
  - Additional top-level keys in those envelopes fail shape matching.

## Suggested follow-up for project-wide pass

When you are ready for the full-doc pass, this schema contract can be linked from:

- project README subsystem map,
- CLI command docs for schema commands,
- request-validation docs where schema-derived constraints are enforced.
