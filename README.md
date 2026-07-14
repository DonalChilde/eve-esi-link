# eve-esi-link

CLI and Python library for working with the EVE Online ESI API.

This project supports:

- schema-aware request validation,
- request execution with caching and rate limiting,
- optional authenticated requests via eve-auth-manager,
- schema fetch/cache/documentation workflows.

## Requirements

- Python 3.14+
- uv (recommended)

## Install

### From source (recommended for development)

```bash
git clone https://github.com/DonalChilde/eve-esi-link
cd eve-esi-link
uv sync
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

## Quick CLI tour

Top-level commands:

- `eve-link request`
- `eve-link schema`
- `eve-link auth-manager`

Useful help commands:

```bash
uv run eve-link --help
uv run eve-link request --help
uv run eve-link schema --help
uv run eve-link schema cache --help
```

## Request JSON format

`request run` and `request validate` expect JSON matching `EsiRequestGroup`, for
example:

```json
{
	"name": "Status Example",
	"description": "Single request example",
	"requests": {
		"d4c54c12-dfb4-43d6-b0d4-56cdd28c0c1a": {
			"request_id": "d4c54c12-dfb4-43d6-b0d4-56cdd28c0c1a",
			"operation_id": "GetStatus",
			"path_parameters": {},
			"query_parameters": {},
			"header_parameters": {}
		}
	}
}
```

Working examples are in [dev/test-requests](dev/test-requests):

- [dev/test-requests/status.json](dev/test-requests/status.json)
- [dev/test-requests/lang.json](dev/test-requests/lang.json)
- [dev/test-requests/paged.json](dev/test-requests/paged.json)
- [dev/test-requests/auth.json](dev/test-requests/auth.json)

## Generating UUIDs for request JSON

Each request entry key and `request_id` field should be a UUID.

### Command line examples

Using Python directly:

```bash
python -c "import uuid; print(uuid.uuid4())"
```

Using uv from this repo environment:

```bash
uv run python -c "import uuid; print(uuid.uuid4())"
```

Generate multiple UUIDs:

```bash
uv run python -c "import uuid; [print(uuid.uuid4()) for _ in range(5)]"
```

```bash
# or use the uuidgen utility if available
uuidgen
```

## CLI usage examples

### 1. Fetch and cache schema(s)

Fetch one compatibility date:

```bash
uv run eve-link schema cache update --date 2026-06-09
```

Fetch all available dates:

```bash
uv run eve-link schema cache update --all
```

List cached schemas:

```bash
uv run eve-link schema cache list
```

### 2. Validate a request group

Use latest cached schema:

```bash
uv run eve-link request validate --from ./dev/test-requests/status.json
```

Use a specific compatibility date:

```bash
uv run eve-link request validate \
	--date 2026-06-09 \
	--from ./dev/test-requests/lang.json
```

Use an explicit schema file:

```bash
uv run eve-link request validate \
	--schema ./dev/tmp/schemas/schema_2026-06-09_esi_schema.json \
	--from ./dev/test-requests/paged.json
```

### 3. Run requests

Write response JSON to stdout:

```bash
uv run eve-link request run --from ./dev/test-requests/status.json --plain
```

Write response JSON to a file:

```bash
uv run eve-link request run \
	--from ./dev/test-requests/lang.json \
	--to ./dev/tmp/lang-response.json \
	--overwrite
```

Authenticated request example:

```bash
uv run eve-link request run --from ./dev/test-requests/auth.json
```

### 4. Generate schema docs

From cached schema:

```bash
uv run eve-link schema cache doc --date 2026-06-09 --to ./dev/tmp/
```

From schema file:

```bash
uv run eve-link schema generate-doc \
	--from ./dev/tmp/schemas/schema_2026-06-09_esi_schema.json \
	--to ./dev/tmp/schema-docs.md
```

## Python API usage

`EsiLink` is the main library entrypoint.

```python
import asyncio
from pathlib import Path

from eve_esi_link import EsiLink
from eve_esi_link.esi_request.models import EsiRequestGroupRoot
from eve_esi_link.schema.helpers.schema_files import load_esi_schema_from_file


async def main() -> None:
		schema = load_esi_schema_from_file(
				Path("./dev/tmp/schemas/schema_2026-06-09_esi_schema.json")
		)

		request_group = EsiRequestGroupRoot.model_validate_json(
				Path("./dev/test-requests/status.json").read_text(encoding="utf-8")
		).root

		async with EsiLink(
				auth_manager_db_path=Path("./dev/app-dir/eve_auth_manager.sqlite"),
				web_cache_path=Path("./dev/app-dir/api_requests_web_cache.sqlite"),
				max_rate=20.0,
				time_period=1.0,
		) as esi:
				responses = await esi.make_requests(request_group, schema)
				print(responses.serialize(indent=2))


asyncio.run(main())
```

Run from source with uv:

```bash
uv run python your_script.py
```

## Development commands

```bash
uv sync
uv run eve-link --help
uv run pytest
uv run ruff format
uv run ruff check
```

## Notes on secrets

- Runtime access tokens are redacted in serialized `EsiResponseGroup` runtime request
	fields.
- Treat serialized failed-response request details as potentially sensitive until
	downstream response-secret purging is fully wired.

## Additional docs

- [docs/esi-link-library-contracts.md](docs/esi-link-library-contracts.md)
- [docs/esi-request-package-contracts.md](docs/esi-request-package-contracts.md)
- [docs/schema-package-contracts.md](docs/schema-package-contracts.md)
