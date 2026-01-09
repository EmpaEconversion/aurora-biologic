"""Tests for CLI commands in aurora-biologic.

Most require Biologic hardware to run, only help command is tested here.
"""

import contextlib
import json
import socket
import threading
import time
from collections.abc import Generator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aurora_biologic.cli.daemon import PORT, start_daemon
from aurora_biologic.cli.main import app

runner = CliRunner()

dev1 = {
    f"MPG2-1-{i}": {
        "device_name": "MPG2-1",
        "device_index": 0,
        "device_serial_number": 123,
        "channel_index": i - 1,
        "channel_serial_number": 6000 + i,
        "is_online": True,
    }
    for i in range(1, 11)
}
dev2 = {
    f"999-{i}": {
        "device_name": 999,
        "device_index": 1,
        "device_serial_number": 999,
        "channel_index": i - 1,
        "channel_serial_number": 7000 + i,
        "is_online": True,
    }
    for i in range(1, 6)
}
dev3 = {
    f"OFFLINE-2-{i}": {
        "device_name": "OFFLINE-2",
        "device_index": 2,
        "device_serial_number": 0,
        "channel_index": i - 1,
        "channel_serial_number": 0,
        "is_online": False,
    }
    for i in range(1, 4)
}


def wait_for_port(timeout: float = 5) -> None:
    """Wait until port is listening."""
    start = time.time()
    while time.time() - start < timeout:
        with contextlib.suppress(OSError):
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
                return
            time.sleep(0.1)
    msg = "Daemon not ready"
    raise RuntimeError(msg)


@pytest.fixture
def mock_daemon(mock_bio, scope="session") -> Generator:
    """Create a daemon in a separate thread."""
    stop = threading.Event()
    thread = threading.Thread(
        target=start_daemon,
        kwargs={"stop_event": stop},
        daemon=True,
    )
    thread.start()
    wait_for_port(PORT)
    yield
    stop.set()
    thread.join(timeout=2)


def test_help(mock_bio) -> None:
    """Test --help command."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Show this message and exit." in result.stdout


def test_ssh_without_daemon(mock_bio, caplog: pytest.LogCaptureFixture) -> None:
    """Test that running without daemon gives error."""
    result = runner.invoke(app, ["status", "--ssh"])
    assert result.exit_code == 1
    assert "run 'biologic daemon'" in caplog.text


def test_pipelines(mock_bio) -> None:
    """Test pipelines CLI function."""
    result = runner.invoke(app, ["pipelines"])
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output == {**dev1, **dev2}

    result = runner.invoke(app, ["pipelines", "--show-offline"])
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output == {**dev1, **dev2, **dev3}


def test_pipelines_ssh(mock_bio, mock_daemon) -> None:
    """Test pipelines CLI function in SSH mode."""
    result = runner.invoke(app, ["pipelines", "--ssh"])
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output == {**dev1, **dev2}

    result = runner.invoke(app, ["pipelines", "--show-offline", "--indent=4", "--ssh"])
    assert result.exit_code == 0
    assert "    " in result.stdout
    output = json.loads(result.stdout)
    assert output == {**dev1, **dev2, **dev3}


def test_status(mock_bio) -> None:
    """Test status CLI function."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["MPG2-1-1"]["Status"] == "Run"
    assert len(output) == 15


def test_status_ssh(mock_bio, mock_daemon) -> None:
    """Test status CLI function in SSH mode."""
    result = runner.invoke(app, ["status", "--ssh"])
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["MPG2-1-1"]["Status"] == "Run"
    assert len(output) == 15

    result = runner.invoke(app, ["status", "--show-offline", "--ssh"])
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["MPG2-1-1"]["Status"] == "Run"
    assert len(output) == 18

    result = runner.invoke(app, ["status", "MPG2-1-1", "--indent=4", "--ssh"])
    assert result.exit_code == 0
    assert "    " in result.stdout
    output = json.loads(result.stdout)
    assert output["MPG2-1-1"]["Status"] == "Run"
    assert len(output) == 1


def test_load_settings(mock_bio, tmp_path: Path) -> None:
    """Test load-settings CLI function."""
    mps_path = tmp_path / "settings.mps"

    result = runner.invoke(app, ["load-settings", "MPG2-1-1", str(mps_path)])
    assert result.exit_code == 1

    with mps_path.open("w") as f:
        f.write("some settings would go here")

    result = runner.invoke(app, ["load-settings", "MPG2-1-1", str(mps_path)])
    assert result.exit_code == 0


def test_load_settings_ssh(mock_bio, mock_daemon, tmp_path: Path) -> None:
    """Test load-settings CLI function."""
    mps_path = tmp_path / "settings.mps"
    assert not mps_path.exists()

    result = runner.invoke(app, ["load-settings", "MPG2-1-1", str(mps_path), "--ssh"])
    assert "FileNotFoundError" in result.stdout

    with mps_path.open("w") as f:
        f.write("some settings would go here")

    result = runner.invoke(app, ["load-settings", "MPG2-1-1", str(mps_path), "--ssh"])
    assert result.stdout.strip() == ""


def test_run_channel(mock_bio, tmp_path: Path) -> None:
    """Test run-channel CLI function."""
    output_path = tmp_path / "output.mpr"
    result = runner.invoke(app, ["run-channel", "MPG2-1-123"])
    assert result.exit_code == 2
    result = runner.invoke(app, ["run-channel", "MPG2-1-123", str(output_path)])
    assert result.exit_code == 1
    result = runner.invoke(app, ["run-channel", "MPG2-1-1", str(output_path)])
    assert result.exit_code == 0


def test_run_channel_ssh(mock_bio, mock_daemon, tmp_path: Path) -> None:
    """Test run-channel CLI function in SSH mode."""
    output_path = tmp_path / "output.mpr"
    result = runner.invoke(app, ["run-channel", "MPG2-1-123", "--ssh"])
    assert result.exit_code == 2
    result = runner.invoke(app, ["run-channel", "MPG2-1-123", str(output_path), "--ssh"])
    assert "ValueError" in result.stdout
    result = runner.invoke(app, ["run-channel", "MPG2-1-1", str(output_path), "--ssh"])
    assert result.stdout.strip() == ""


def test_start(mock_bio, tmp_path: Path) -> None:
    """Test start CLI function."""
    mps_path = tmp_path / "settings.mps"
    output_path = tmp_path / "output.mpr"
    with mps_path.open("w") as f:
        f.write("some settings would go here")
    result = runner.invoke(app, ["start", "MPG2-1-1", str(mps_path), str(output_path)])
    assert result.exit_code == 0


def test_start_ssh(mock_bio, mock_daemon, tmp_path: Path) -> None:
    """Test start CLI function in SSH mode."""
    mps_path = tmp_path / "settings.mps"
    output_path = tmp_path / "output.mpr"
    with mps_path.open("w") as f:
        f.write("some settings would go here")
    result = runner.invoke(app, ["start", "MPG2-1-1", str(mps_path), str(output_path), "--ssh"])
    assert result.exit_code == 0
    assert result.stdout.strip() == ""


def test_stop(mock_bio) -> None:
    """Test stop CLI function."""
    result = runner.invoke(app, ["stop", "MPG2-1-1"])
    assert result.exit_code == 0


def test_stop_ssh(mock_bio, mock_daemon) -> None:
    """Test stop CLI function in SSH mode."""
    result = runner.invoke(app, ["stop", "MPG2-1-1", "--ssh"])
    assert result.exit_code == 0
    assert result.stdout.strip() == ""


def test_get_job_id(mock_bio) -> None:
    """Test get-job-id CLI function."""
    result = runner.invoke(app, ["get-job-id", "MPG2-1-1"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"MPG2-1-1": "thisisthejob"}
    result = runner.invoke(app, ["get-job-id", "--show-offline", "--indent=4"])
    assert "    " in result.stdout
    assert len(json.loads(result.stdout)) == 18


def test_get_job_id_ssh(mock_bio, mock_daemon) -> None:
    """Test get-job-id CLI function in SSH mode."""
    result = runner.invoke(app, ["get-job-id", "MPG2-1-1", "--ssh"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"MPG2-1-1": "thisisthejob"}
    result = runner.invoke(app, ["get-job-id", "--show-offline", "--indent=4", "--ssh"])
    assert "    " in result.stdout
    assert len(json.loads(result.stdout)) == 18
