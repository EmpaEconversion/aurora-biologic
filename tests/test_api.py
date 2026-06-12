"""Tests for the FastAPI REST API."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import aurora_biologic.biologic as bio
from aurora_biologic.api.main import app

client = TestClient(app)

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


def test_get_pipelines(mock_bio: bio.BiologicAPI) -> None:
    """Test GET /pipelines returns online pipelines."""
    response = client.get("/pipelines")
    assert response.status_code == 200
    assert response.json() == {**dev1, **dev2}


def test_get_pipelines_show_offline(mock_bio: bio.BiologicAPI) -> None:
    """Test GET /pipelines?show_offline=true includes offline devices."""
    response = client.get("/pipelines?show_offline=true")
    assert response.status_code == 200
    assert response.json() == {**dev1, **dev2, **dev3}


def test_get_status(mock_bio: bio.BiologicAPI) -> None:
    """Test GET /status returns status for all online pipelines."""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["MPG2-1-1"]["Status"] == "Run"
    assert len(data) == 15


def test_get_status_selected(mock_bio: bio.BiologicAPI) -> None:
    """Test GET /status with selected pipeline_ids."""
    response = client.get("/status?pipeline_ids=MPG2-1-1")
    assert response.status_code == 200
    data = response.json()
    assert data["MPG2-1-1"]["Status"] == "Run"
    assert len(data) == 1


def test_get_status_show_offline(mock_bio: bio.BiologicAPI) -> None:
    """Test GET /status?show_offline=true includes offline devices."""
    response = client.get("/status?show_offline=true")
    assert response.status_code == 200
    assert len(response.json()) == 18


def test_get_job_id(mock_bio: bio.BiologicAPI) -> None:
    """Test GET /job-id returns job IDs for all online pipelines."""
    response = client.get("/job-id?pipeline_ids=MPG2-1-1")
    assert response.status_code == 200
    assert response.json() == {"MPG2-1-1": "thisisthejob"}


def test_get_job_id_all(mock_bio: bio.BiologicAPI) -> None:
    """Test GET /job-id without selection returns all online pipelines."""
    response = client.get("/job-id?show_offline=true")
    assert response.status_code == 200
    assert len(response.json()) == 18


def test_load_settings(mock_bio: bio.BiologicAPI, tmp_path: Path) -> None:
    """Test POST /load-settings/{pipeline} loads a settings file."""
    mps_path = tmp_path / "settings.mps"
    mps_path.write_text("some settings would go here")
    response = client.post("/load-settings/MPG2-1-1", json={"settings_file": str(mps_path)})
    assert response.status_code == 204


def test_load_settings_file_not_found(mock_bio: bio.BiologicAPI, tmp_path: Path) -> None:  # noqa: ARG001
    """Test POST /load-settings/{pipeline} returns 422 for missing file."""
    mps_path = tmp_path / "missing.mps"
    response = client.post("/load-settings/MPG2-1-1", json={"settings_file": str(mps_path)})
    assert response.status_code == 422


def test_run_channel(mock_bio: bio.BiologicAPI, tmp_path: Path) -> None:
    """Test POST /run-channel/{pipeline} runs the loaded settings."""
    output_path = tmp_path / "output.mpr"
    response = client.post("/run-channel/MPG2-1-1", json={"output_path": str(output_path)})
    assert response.status_code == 204


def test_run_channel_invalid_pipeline(mock_bio: bio.BiologicAPI, tmp_path: Path) -> None:  # noqa: ARG001
    """Test POST /run-channel/{pipeline} returns 400 for unknown pipeline."""
    output_path = tmp_path / "output.mpr"
    response = client.post("/run-channel/MPG2-1-123", json={"output_path": str(output_path)})
    assert response.status_code == 400


def test_start(mock_bio: bio.BiologicAPI, tmp_path: Path) -> None:
    """Test POST /start/{pipeline} loads and runs a protocol."""
    mps_path = tmp_path / "settings.mps"
    mps_path.write_text("some settings would go here")
    output_path = tmp_path / "output.mpr"
    response = client.post(
        "/start/MPG2-1-1",
        json={"settings_file": str(mps_path), "output_path": str(output_path)},
    )
    assert response.status_code == 204


def test_stop(mock_bio: bio.BiologicAPI) -> None:
    """Test POST /stop/{pipeline} stops cycling."""
    response = client.post("/stop/MPG2-1-1")
    assert response.status_code == 204


def test_stop_invalid_pipeline(mock_bio: bio.BiologicAPI) -> None:
    """Test POST /stop/{pipeline} returns 400 for unknown pipeline."""
    response = client.post("/stop/MPG2-1-999")
    assert response.status_code == 400


@pytest.mark.real_eclab
def test_get_pipelines_real(real_bio: bio.BiologicAPI) -> None:
    """Test GET /pipelines against real EC-Lab."""
    response = client.get("/pipelines")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
