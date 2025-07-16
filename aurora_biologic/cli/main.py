"""CLI for the Biologic battery cycling API."""

import json
from pathlib import Path
from typing import Annotated

import typer

from aurora_biologic import BiologicAPI

app = typer.Typer(add_completion=False)

IndentOption = Annotated[int | None, typer.Option(help="Indent the output.")]
PipelinesArgument = Annotated[list[str] | None, typer.Argument()]
NumberOfPoints = Annotated[int, typer.Argument()]
PathArgument = Annotated[Path, typer.Argument(help="Path to a file")]


@app.command()
def pipelines(
    indent: IndentOption = None,
) -> None:
    """Return details of all connected instruments.

    Returns a dictionary as a JSON string.

    Example usage:
    >>> biologic pipelines
    {"MPG2-16-1": {"device_index": 0, "device_serial_number": 365 ... } ... }

    Args:
        indent (optional): an integer number that controls the identation of the printed output

    """
    with BiologicAPI() as bio:
        typer.echo(json.dumps(bio.pipelines, indent=indent))


@app.command()
def status(
    pipeline_ids: PipelinesArgument = None,
    indent: IndentOption = None,
) -> None:
    """Get the status of the cycling process for all or selected pipelines.

    Returns a dictionary as a JSON string.

    Example usage:
    >>> biologic status
    {"MPG2-16-1": { ... }}

    Args:
        pipeline_ids (optional): list of pipeline IDs to get status from
            will use the full channel map if not provided
        indent (optional): an integer number that controls the identation of the printed output

    """
    with BiologicAPI() as bio:
        status = bio.get_status(pipeline_ids=pipeline_ids)
        typer.echo(json.dumps(status, indent=indent))
