"""CLI for the Biologic battery cycling API."""

import json
import logging
import sys
from pathlib import Path
from typing import Annotated

import typer

from aurora_biologic import BiologicAPI
from aurora_biologic.cli.daemon import send_command, start_daemon

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

app = typer.Typer(add_completion=False)

IndentOption = Annotated[int | None, typer.Option(help="Indent the output.")]
PipelinesArgument = Annotated[list[str] | None, typer.Argument()]
SSHArgument = Annotated[
    bool,
    typer.Option(
        "--ssh",
        "-s",
        is_flag=True,
        help="Use SSH to connect to the Biologic daemon.",
    ),
]
NumberOfPoints = Annotated[int, typer.Argument()]
PathArgument = Annotated[Path, typer.Argument(help="Path to a file")]


@app.command()
def pipelines(
    indent: IndentOption = None,
    ssh: SSHArgument = False,
) -> None:
    """Return details of all connected instruments.

    Returns a dictionary as a JSON string.

    Example usage:
    >>> biologic pipelines
    {"MPG2-16-1": {"device_index": 0, "device_serial_number": 365 ... } ... }

    Args:
        indent (optional): an integer number that controls the identation of the printed output
        ssh (optional): must be set if running in a non-interactive terminal session like SSH

    """
    if ssh:
        command = ["biologic", "pipelines"]
        typer.echo(send_command(command))
        return
    with BiologicAPI() as bio:
        typer.echo(json.dumps(bio.pipelines, indent=indent))


@app.command()
def status(
    pipeline_ids: PipelinesArgument = None,
    indent: IndentOption = None,
    ssh: SSHArgument = False,
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
        ssh (optional): must be set if running in a non-interactive terminal session like SSH

    """
    if ssh:
        command = ["biologic", "status"]
        if pipeline_ids:
            command.extend(pipeline_ids)
        typer.echo(send_command(command))
        return
    with BiologicAPI() as bio:
        status = bio.get_status(pipeline_ids=pipeline_ids)
        typer.echo(json.dumps(status, indent=indent))


@app.command()
def load_settings(
    pipeline: str,
    settings_file: PathArgument,
    ssh: SSHArgument = False,
) -> None:
    """Load a protocol on to a pipeline.

    Args:
        pipeline (str): the pipeline ID to load settings on
        settings_file (Path): path to the settings file
        ssh (optional): must be set if running in a non-interactive terminal session like SSH

    """
    if ssh:
        command = ["biologic", "load-settings", pipeline, str(settings_file)]
        typer.echo(send_command(command))
        return
    with BiologicAPI() as bio:
        bio.load_settings(pipeline, settings_file)


@app.command()
def run_channel(
    pipeline: str,
    output_path: PathArgument,
    ssh: SSHArgument = False,
) -> None:
    """Run the protocol loaded on a pipeline.

    Args:
        pipeline (str): the pipeline ID to run settings on
        output_path (Path): path to the output file
        ssh (optional): must be set if running in a non-interactive terminal session like SSH

    """
    if ssh:
        command = ["biologic", "run-channel", pipeline, str(output_path)]
        typer.echo(send_command(command))
        return
    with BiologicAPI() as bio:
        bio.run_channel(pipeline, output_path)


@app.command()
def start(
    pipeline: str,
    settings_file: PathArgument,
    output_path: PathArgument,
    ssh: SSHArgument = False,
) -> None:
    """Submit and run a protocol on a pipeline.

    Args:
        pipeline (str): the pipeline ID to submit
        settings_file (Path): path to the settings file
        output_path (Path): path to the output file
        ssh (optional): must be set if running in a non-interactive terminal session like SSH

    """
    if ssh:
        command = ["biologic", "start", pipeline, str(settings_file), str(output_path)]
        typer.echo(send_command(command))
        return
    with BiologicAPI() as bio:
        bio.start(pipeline, settings_file, output_path)


@app.command()
def stop(
    pipeline: str,
    ssh: SSHArgument = False,
) -> None:
    """Stop the cycling process on a pipeline.

    Args:
        pipeline (str): the pipeline ID to stop
        ssh (optional): must be set if running in a non-interactive terminal session like SSH

    """
    if ssh:
        command = ["biologic", "stop", pipeline]
        typer.echo(send_command(command))
        return
    with BiologicAPI() as bio:
        bio.stop(pipeline)


@app.command()
def get_job_id(
    pipeline_ids: PipelinesArgument = None,
    indent: IndentOption = None,
    ssh: SSHArgument = False,
) -> None:
    """Get the job id for selected pipelines.

    Args:
        pipeline_ids (optional): list of pipeline IDs to get job IDs from
            will use the full channel map if not provided
        indent (optional): an integer number that controls the identation of the printed output
        ssh (optional): must be set if running in a non-interactive terminal session like SSH

    Returns:
        A dictionary with pipeline IDs as keys and job IDs as values.
        If the job is running, the job ID is the folder name, otherwise it is None.

    """
    if ssh:
        command = ["biologic", "get-job-id"]
        if pipeline_ids:
            command.extend(pipeline_ids)
        typer.echo(send_command(command))
        return
    with BiologicAPI() as bio:
        typer.echo(json.dumps(bio.get_job_id(pipeline_ids), indent=indent))


@app.command()
def daemon() -> None:
    """Start the Biologic daemon to listen for commands."""
    start_daemon()
