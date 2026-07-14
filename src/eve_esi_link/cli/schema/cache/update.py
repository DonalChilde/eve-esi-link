from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.json import JSON
from whenever import Instant

from eve_esi_link.cli.helpers import get_eve_link_settings_from_context, get_stdin
from eve_esi_link.helpers import json_io
from eve_esi_link.helpers.http_session_factory import client_manager
from eve_esi_link.helpers.save_text_file import save_text_file
from eve_esi_link.schema.cache import SchemaCacheManager
from eve_esi_link.schema.helpers.fetch import fetch_compatibility_dates, fetch_schema

app = typer.Typer(no_args_is_help=True)

# can update the cached schema files, by compatibility_date, or all of the available dates.
# Follow cli conventions.
