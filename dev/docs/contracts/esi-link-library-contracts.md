# eve_esi_link.EsiLink: library entrypoint contracts

This document defines the current, code-observed contracts for the
`EsiLink` class in `src/eve_esi_link/esi_link.py`.

## Audience

- Library users embedding eve_esi_link in Python applications.
- Contributors maintaining execution flow between request models and api_request.

## Purpose

`EsiLink` is the primary library entrypoint for executing validated ESI requests.
It bridges:

1. `EsiRequestGroup` input models,
2. schema-based request validation,
3. runtime request construction,
4. auth token injection for authorized operations,
5. batch HTTP execution through `api_request`,
6. response shaping into `EsiResponseGroup`.

## Lifecycle contract

`EsiLink` must be used as an async context manager:

- setup in `__aenter__`
- teardown in `__aexit__`

### __aenter__ behavior

- Creates `SqliteCacheFactory` with provided web cache path.
- Creates `AiolimiterRateLimiterFactory` using `max_rate` and `time_period`.
- Constructs `api_request.ApiRequester` with cache and rate limiter factories.
- Opens `ApiRequester` async context.
- Opens `SqliteAuthManager` sync context.

### __aexit__ behavior

- Closes `ApiRequester` if initialized.
- Closes `SqliteAuthManager` if initialized.

### Guard rails

Internal methods `_check_api_requester_initialized` and `_check_auth_manager` raise
`RuntimeError` when called before context entry.

## Construction contract

`EsiLink(...)` accepts:

- `auth_manager_db_path`: path to auth-manager sqlite DB.
- `web_cache_path`: path to api-request web cache sqlite DB.
- `max_rate`: request budget for limiter window (default `20.0`).
- `time_period`: limiter window seconds (default `1.0`).

No external I/O is performed during constructor call.

## Request execution contract

Primary method: `await make_requests(esi_requests, schema)`.

Input:

- `esi_requests`: `EsiRequestGroup`
- `schema`: `EsiSchema`

Per-request flow:

1. Validate request against schema via `validate_request`.
2. Build `RuntimeEsiRequest` with `build_runtime_esi_request`.
3. If authorization is present, fetch access token from auth manager and attach to runtime request.
4. Convert runtime request into `api_request.Request`.

Batch execution:

- Calls `requester.process_requests(request_objects)` once for the request batch.

Output shaping:

- Successful responses become `EsiResponse` entries.
- Failed responses become `FailedEsiResponse` entries.
- Returns `EsiResponseGroup` preserving input `name`, `description`, and `requests`.

## Validation contract

Static method `validate_request(esi_request, schema)` delegates to
`validate_esi_request` in the esi_request subsystem.

- Raises `EsiRequestValidationErrors` when validation fails.
- Logs validation failure details before re-raising.

## Authorization contract

`_check_required_access_token` behavior:

- If request has no authorization fields, no token is set.
- If request has authorization fields, both `credential_id` and `character_id` must be present.
- Token is loaded from auth manager `get_character(cred_id, character_id).access_token`.
- Token is attached to `RuntimeEsiRequest.access_token` for request-header composition.

## Response and secret-handling notes

Returned `EsiResponseGroup` contains runtime requests and upstream response payloads.

Important safety note:

- Runtime access tokens are represented in `RuntimeEsiRequest.access_token` and can be
  redacted through response-group serialization helpers in the esi_request models.
- Underlying upstream request payload redaction from api_request response objects is not
  fully wired in this repository yet (see FIXMEs in esi_request models).

Treat serialized failed-response details as potentially sensitive until full response
secret purging is in place.

## Exceptions and failure modes

- `RuntimeError`: when methods requiring initialized context are used outside `async with`.
- `ValueError`: for invalid operation IDs (via runtime builder/schema lookup) or incomplete
  authorization tuple states.
- `EsiRequestValidationErrors`: schema validation failures.
- Transport/cache/auth backend exceptions may propagate from dependencies.

## Related subsystem docs

- `docs/esi-request-package-contracts.md`
- `docs/schema-package-contracts.md`
