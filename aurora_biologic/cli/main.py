"""CLI for the Biologic battery cycling API."""

import json
import logging
import sys
from pathlib import Path
from typing import Annotated

import typer

import aurora_biologic.biologic as bio
from aurora_biologic.cli.daemon import send_command, start_daemon

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

app = typer.Typer(add_completion=False)

IndentOption = Annotated[int | None, typer.Option(help="Indentation on JSON string output.")]
SinglePipelineArgument = Annotated[
    str,
    typer.Argument(
        help="Pipeline ID. Use 'biologic pipelines' to see available.",
    ),
]
PipelinesArgument = Annotated[
    list[str] | None,
    typer.Argument(
        help="List of pipeline IDs. Will use the full channel map if not provided.",
    ),
]
SSHOption = Annotated[
    bool,
    typer.Option(
        "--ssh",
        "-s",
        help="Use SSH to connect to the Biologic daemon.",
    ),
]
NumberOfPoints = Annotated[int, typer.Argument()]
InputPathArgument = Annotated[Path, typer.Argument(help="Path to a .mps settings file")]
OutputPathArgument = Annotated[
    Path,
    typer.Argument(
        help="Path to the output file. Several files will be generated with different suffixes."
    ),
]
ShowOfflineOption = Annotated[
    bool,
    typer.Option(
        "--show-offline",
        "-a",
        help="Show all devices, including offline (disconnected or virtual) devices.",
    ),
]


@app.command()
def pipelines(
    indent: IndentOption = None,
    ssh: SSHOption = False,
    show_offline: ShowOfflineOption = False,
) -> None:
    """Get details of all connected instruments.

    Returns a dictionary as a JSON string.
    """
    if ssh:
        command = ["biologic", "pipelines"]
        if indent:
            command += [f"--indent={indent}"]
        if show_offline:
            command += ["--show-offline"]
        typer.echo(send_command(command))
        return
    typer.echo(json.dumps(bio.get_pipelines(show_offline=show_offline), indent=indent))


@app.command()
def status(
    pipeline_ids: PipelinesArgument = None,
    indent: IndentOption = None,
    ssh: SSHOption = False,
    show_offline: ShowOfflineOption = False,
) -> None:
    """Get the status of the cycling process for all or selected pipelines.

    Returns a dictionary as a JSON string.
    """
    if ssh:
        command = ["biologic", "status"]
        if pipeline_ids:
            command.extend(pipeline_ids)
        if show_offline:
            command += ["--show-offline"]
        if indent:
            command += [f"--indent={indent}"]
        typer.echo(send_command(command))
        return
    status = bio.get_status(pipeline_ids=pipeline_ids, show_offline=show_offline)
    typer.echo(json.dumps(status, indent=indent))


@app.command()
def load_settings(
    pipeline: SinglePipelineArgument,
    settings_file: InputPathArgument,
    ssh: SSHOption = False,
) -> None:
    """Load settings on to a pipeline."""
    if ssh:
        command = ["biologic", "load-settings", pipeline, str(settings_file)]
        typer.echo(send_command(command))
        return
    bio.load_settings(pipeline, settings_file)


@app.command()
def run_channel(
    pipeline: SinglePipelineArgument,
    output_path: OutputPathArgument,
    ssh: SSHOption = False,
) -> None:
    """Run the settings loaded on a pipeline."""
    if ssh:
        command = ["biologic", "run-channel", pipeline, str(output_path)]
        typer.echo(send_command(command))
        return
    bio.run_channel(pipeline, output_path)


@app.command()
def start(
    pipeline: SinglePipelineArgument,
    settings_file: InputPathArgument,
    output_path: OutputPathArgument,
    ssh: SSHOption = False,
) -> None:
    """Load and run settings on a pipeline."""
    if ssh:
        command = ["biologic", "start", pipeline, str(settings_file), str(output_path)]
        typer.echo(send_command(command))
        return
    bio.start(pipeline, settings_file, output_path)


@app.command()
def stop(
    pipeline: SinglePipelineArgument,
    ssh: SSHOption = False,
) -> None:
    """Stop the cycling process on a pipeline."""
    if ssh:
        command = ["biologic", "stop", pipeline]
        typer.echo(send_command(command))
        return
    bio.stop(pipeline)


@app.command()
def get_job_id(
    pipeline_ids: PipelinesArgument = None,
    indent: IndentOption = None,
    ssh: SSHOption = False,
    show_offline: ShowOfflineOption = False,
) -> None:
    """Get the job id for selected pipelines.

    If the job is running, the job ID is the folder name, otherwise it is None.

    Returns a dictionary as a JSON string.
    """
    if ssh:
        command = ["biologic", "get-job-id"]
        if pipeline_ids:
            command.extend(pipeline_ids)
        if show_offline:
            command += ["--show-offline"]
        if indent:
            command += [f"--indent={indent}"]
        typer.echo(send_command(command))
        return
    typer.echo(json.dumps(bio.get_job_id(pipeline_ids, show_offline=show_offline), indent=indent))


@app.command()
def daemon() -> None:
    """Start the Biologic daemon to listen for commands."""
    start_daemon()
