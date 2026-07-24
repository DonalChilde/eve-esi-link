"""Generate markdown documentation from ESI schema JSON."""

from pathlib import Path
from typing import Annotated

import typer
from pfmsoft.eve_snippets import json_io, save_text_file
from rich.console import Console
from rich.markdown import Markdown

from pfmsoft.eve_link.schema.cache.schema_cache_disk import SchemaCacheManager
from pfmsoft.eve_link.schema.helpers.schema_files import (
    load_esi_schema,
    load_esi_schema_from_file,
)
from pfmsoft.eve_link.schema.schema_doc import (
    FencedDataFormat,
    generate_esi_schema_markdown_doc,
)

from ..helpers import get_eve_link_settings_from_context, get_schema, get_stdin

app = typer.Typer(no_args_is_help=True)


@app.command(
    name="generate-doc",
    help="Generate operation-focused markdown documentation from schema JSON input.",
)
def generate_schema_doc(
    ctx: typer.Context,
    file_in: Annotated[
        Path | None,
        typer.Option(
            "--from",
            file_okay=True,
            dir_okay=False,
            readable=True,
            allow_dash=True,
            help="Path to schema JSON. Use - for stdin. Defaults to None, which will use the cached schema from --date.",
        ),
    ] = None,
    compatibility_date: Annotated[
        str | None,
        typer.Option(
            "--date",
            show_default=True,
            help="Compatibility date (YYYY-MM-DD) of cached ESI schema to use. Mutually exclusive with --file-in.",
        ),
    ] = None,
    file_out: Annotated[
        Path,
        typer.Option(
            "--to",
            help="Output markdown file path. Use - for stdout.",
            allow_dash=True,
            dir_okay=False,
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
    """Generate markdown documentation from ESI schema JSON.

    The generated markdown includes version metadata, TOC grouped by tag, and a
    per-operation section that covers summary, parameters, request body, response schema,
    and extension fields.
    """
    if quiet:
        messenger = Console(stderr=True, quiet=True)
    else:
        messenger = Console(stderr=True)
    if file_in is not None and compatibility_date is not None:
        messenger.print(
            "[red]Error: Cannot specify both --schema and --date options.[/red]"
        )
        raise typer.Exit(code=1)
    # Get the EsiSchema from the input file or stdin
    if file_in == Path("-"):
        input_data = get_stdin()
        try:
            schema_dict = json_io.json_loads(input_data)
        except Exception as e:
            messenger.print(f"[red]Error: Failed to parse JSON input - {e}[/red]")
            raise typer.Exit(code=1) from e
        try:
            esi_schema = load_esi_schema(schema_dict)
        except Exception as e:
            messenger.print(
                f"[red]Error: Failed to load schema from JSON input - {e}[/red]"
            )
            raise typer.Exit(code=1) from e
    elif file_in is not None:
        try:
            esi_schema = load_esi_schema_from_file(file_path=file_in)
        except Exception as e:
            messenger.print(f"[red]Error: Failed to read input file - {e}[/red]")
            raise typer.Exit(code=1) from e
    else:
        settings = get_eve_link_settings_from_context(ctx)
        # if compatibility_date is None, get the most recent cached schema
        manager = SchemaCacheManager(cache_directory=settings.schema_cache_directory)
        esi_schema = get_schema(
            messenger=messenger,
            schema_manager=manager,
            compatibility_date=compatibility_date,
        )

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
        schema_compat_date = esi_schema.compatibility_date
        default_file_name = f"schema_docs_{schema_compat_date}.md"
        file_path = file_out / default_file_name
    try:
        output_path = save_text_file(
            text=markdown_doc,
            directory=file_path.parent,
            filename=file_path.name,
            overwrite=overwrite,
        )
    except Exception as e:
        messenger.print(f"[red]Error: Failed to save output file - {e}[/red]")
        raise typer.Exit(code=1) from e
    messenger.print(f"[green]Markdown documentation saved to {output_path}[/green]")
