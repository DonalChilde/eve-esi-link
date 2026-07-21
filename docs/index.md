# Eve Link

Eve Link provides a simple, scriptable cli and api to access the Eve Online ESI.

Features:

- Supports authenticated requests
- Get character id by name
- Caching
- Paged request handling
- Async requests
- Rate Limiting
- A pipeable cli
- An Api for use as a library
- Generated documentation for the ESI schema

## Project Status

Beta. Core functions available.

## Requirements

- Python 3.14+
- uv (recommended)

## Links To More Information

- [ESI Api Explorer](https://developers.eveonline.com/api-explorer)
- [ESI Application Portal](https://developers.eveonline.com/applications)
- [EVE Online 3rd party developer docs](https://developers.eveonline.com/docs/)

## Quick Start
```bash
# Use the appropriate command format for your install
eve-link schema cache update --all
eve-link schema generate-doc --to ./schema-docs/
eve-link samples --to ./sample-requests/
eve-link run --from ./sample-requests/status.request.json
```


