"""Generate markdown documentation from a cached ESI schema."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from eve_esi_link.cli.helpers import get_eve_link_settings_from_context
from eve_esi_link.helpers.save_text_file import save_text_file
from eve_esi_link.schema.cache import SchemaCacheManager
from eve_esi_link.schema.schema_doc import (
    FencedDataFormat,
    generate_esi_schema_markdown_doc,
)

app = typer.Typer(no_args_is_help=True)


@app.command(
    name="doc",
    help="Generate markdown documentation from a cached ESI schema.",
)
def doc_cache(
    ctx: typer.Context,
    compatibility_date: Annotated[
        str,
        typer.Option(
            "--date",
            metavar="YYYY-MM-DD",
            help="Compatibility date (YYYY-MM-DD) of the cached schema to document.",
        ),
    ],
    file_out: Annotated[
        Path,
        typer.Option(
            "--to",
            help="Output markdown file path. Use - for stdout.",
            allow_dash=True,
            dir_okay=True,
        ),
    ] = Path("-"),
    fenced_format: Annotated[
        FencedDataFormat,
        typer.Option(
            "--fenced-format",
            help="Serialization format for fenced request/response blocks. Defaults to json.",
        ),
    ] = FencedDataFormat.JSON,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Overwrite output file if it already exists.",
        ),
    ] = False,
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Display the output in plain text instead of Rich Markdown.",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help="Suppress status output.",
        ),
    ] = False,
) -> None:
    """Generate markdown documentation from a cached ESI schema.

    The schema is loaded from the local cache by its compatibility date. The generated
    markdown includes version metadata, TOC grouped by tag, and a per-operation section
    that covers summary, parameters, request body, response schema, and extension fields.

    Examples:
        Print docs to stdout:
            eve-link schema cache doc --date 2026-06-09

        Save docs to a directory (auto-named):
            eve-link schema cache doc --date 2026-06-09 --to ./docs/

        Save docs to a specific file:
            eve-link schema cache doc --date 2026-06-09 --to ./docs/esi.md
    """
    # ctx is an invisible typer context parameter — not documented in help.
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)

    settings = get_eve_link_settings_from_context(ctx)
    manager = SchemaCacheManager(cache_directory=settings.schema_cache_directory)

    try:
        available_dates = [entry.compatibility_date for entry in manager.list_entries()]
        if compatibility_date not in available_dates:
            messenger.print(
                f"[red]Error: No cached schema found for {compatibility_date}. Available "
                f"dates are {available_dates}[/red]"
            )
            raise typer.Exit(code=1)
        esi_schema = manager.load(compatibility_date=compatibility_date)
    except FileNotFoundError as e:
        messenger.print(
            f"[red]Error: No cached schema found for {compatibility_date}.[/red]"
        )
        raise typer.Exit(code=1) from e
    except Exception as e:
        messenger.print(f"[red]Error: Failed to load cached schema - {e}[/red]")
        raise typer.Exit(code=1) from e

    markdown_doc = generate_esi_schema_markdown_doc(
        schema=esi_schema,
        fenced_format=fenced_format,
    )

    if file_out == Path("-"):
        if plain:
            print(markdown_doc)
        else:
            messenger.print(Markdown(markdown_doc))
        raise typer.Exit()

    if file_out.suffix == ".md":
        file_path = file_out
    else:
        default_file_name = f"schema_docs_{compatibility_date}.md"
        file_path = file_out / default_file_name

    try:
        output_path = save_text_file(
            text=markdown_doc,
            output_directory=file_path.parent,
            file_name=file_path.name,
            overwrite=overwrite,
        )
    except Exception as e:
        messenger.print(f"[red]Error: Failed to save output file - {e}[/red]")
        raise typer.Exit(code=1) from e

    messenger.print(f"[green]Markdown documentation saved to {output_path}[/green]")
