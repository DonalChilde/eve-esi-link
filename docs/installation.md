# Installation

## From pypi

```bash
# add to your projects pyproject.toml
uv add pfmsoft-eve-link
```

```bash
# run with uv
uvx  --from pfmsoft-eve-link eve-link --help
# To disable a system wide --exclude-newer for one command:
# You might want do do this to get the latest version during active development
uvx  --from pfmsoft-eve-link --exclude-newer '1 second'  eve-link --help
```

## From source

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

## Run directly from GitHub with uv (no clone)

Run once:

```bash
uvx --from git+https://github.com/DonalChilde/eve-esi-link eve-link --help
```

Install as a uv-managed tool:

```bash
uv tool install git+https://github.com/DonalChilde/eve-esi-link
eve-link --help
```

## Add as a dependency to a script

Add pfmsoft-eve-link as an inline script dependency:

- [PEP 723](https://peps.python.org/pep-0723)
- [PYPA Specification](https://packaging.python.org/en/latest/specifications/inline-script-metadata/#inline-script-metadata)

```bash
uv init --script ./example.py
uv add pfmsoft-eve-link --script ./example.py
```

Results in:

```python
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pfmsoft-eve-link>=0.4.1",
# ]
# ///


def main() -> None:
    print("Hello from example.py!")


if __name__ == "__main__":
    main()
```

This script can be run (with automatic dependency management) by:

```bash
# https://docs.astral.sh/uv/guides/scripts/#running-scripts
uv run ./example.py
```
