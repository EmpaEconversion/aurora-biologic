"""Tests for biologic.py."""

from pathlib import Path

import pytest

import aurora_biologic.biologic as bio


def test_get_pipelines(mock_bio) -> None:
    """Test get_pipelines() function."""
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

    assert bio.get_pipelines() == {**dev1, **dev2}
    assert bio.get_pipelines(show_offline=True) == {**dev1, **dev2, **dev3}

    # With context should behave the same
    with bio.BiologicAPI() as bapi:
        bapi.CONFIG = {
            "serial_to_name": {123: "MPG2-1"},
            "eclab_path": "this/path/doesnt/exist/EClab.exe",
        }
        bapi.pipelines = bapi._get_all_pipelines()
        assert bapi.get_pipelines() == {**dev1, **dev2}


def test_get_status(mock_bio) -> None:
    """Test the get_status() function."""
    expect = {
        "MPG2-1-1": {
            "Status": "Run",
            "Ox/Red": "Reduction",
            "OCV": "Other",
            "EIS": "No EIS",
            "Technique number": 5.0,
            "Technique code": "GCPL",
            "Sequence number": 2.0,
            "Current loop iteration number": 30.0,
            "Current sequence within loop number": 2.0,
            "Loop experiment iteration number": 2.0,
            "Cycle number": 3.0,
            "Counter 1": 0.0,
            "Counter 2": 0.0,
            "Counter 3": 0.0,
            "Buffer size": 38.0,
            "Time (s)": 5097814.5,
            "Ewe (V)": 3.616943597793579,
            "Ece (V)": -0.0009127054363489151,
            "Eoc (V)": 4.174654006958008,
            "I (A)": -0.5903541445732117,
            "Q-Q0 (Ah)": 0.8317033648490906,
            "Aux1": -0.000252805941272527,
            "Aux2": -0.0012308506993576884,
            "Irange (A)": 0.001,
            "R compensation (Ohm)": 0.0,
            "Frequency (Hz)": 0.0,
            "|Z| (Ohm)": -1.0,
            "Current point index": 61.0,
            "Total point index": 61.0,
            "T (°C)": 0.0,
            "Safety limit": "Ok",
            "Connection": "Ok",
        }
    }
    res = bio.get_status("MPG2-1-1")
    assert res == expect

    res = bio.get_status(["MPG2-1-1"])
    assert res == expect

    res = bio.get_status(["MPG2-1-1", "MPG2-1-2"])
    assert len(res) == 2

    res = bio.get_status()
    assert len(res) == 15

    res = bio.get_status(show_offline=True)
    assert len(res) == 18

    res = bio.get_status(["doesntexist"])
    assert len(res) == 0


def test_load_settings(mock_bio, tmpdir: Path) -> None:
    """Test load_settings() function."""
    mps_path = tmpdir / "settings.mps"
    with pytest.raises(FileNotFoundError):
        bio.load_settings("MPG2-1-1", mps_path)
    with mps_path.open("w") as f:
        f.write("some settings would go here")
    bio.load_settings("MPG2-1-1", mps_path)

    with pytest.raises(ValueError) as excinfo:
        bio.load_settings("MPG2-1-800", mps_path)
    assert "not known as a pipeline" in str(excinfo.value)

    # Loading settings on offline instruments is okay
    bio.load_settings("OFFLINE-2-1", mps_path)

    # This channel shouldnt work
    mock_bio.eclab.simulate_unselectable = True
    with pytest.raises(RuntimeError):
        bio.load_settings("999-1", mps_path)
    mock_bio.eclab.simulate_unselectable = False
    mock_bio.eclab.simulate_bad_channel = True
    with pytest.raises(RuntimeError):
        bio.load_settings("999-1", mps_path)
    mock_bio.eclab.simulate_bad_channel = False


def test_run_channel(mock_bio, tmpdir: Path) -> None:
    """Test run_channel() function."""
    with pytest.raises(ValueError) as excinfo:
        bio.run_channel("MPG2-1-1", tmpdir)
    assert "Must provide a full file path, not directory." in str(excinfo.value)
    output_path = tmpdir / "some-output.mpr"
    bio.run_channel("MPG2-1-1", output_path)

    with pytest.raises(ValueError) as excinfo:
        bio.run_channel("OFFLINE-2-1", output_path)
    assert "Device is offline" in str(excinfo.value)

    mock_bio.eclab.simulate_bad_channel = True
    with pytest.raises(RuntimeError):
        bio.run_channel("MPG2-1-1", output_path)
    mock_bio.eclab.simulate_bad_channel = False


def test_start(mock_bio, tmpdir: Path) -> None:
    """Test start() function."""
    mps_path = tmpdir / "settings.mps"
    output_path = tmpdir / "some-output.mps"
    with pytest.raises(FileNotFoundError):
        bio.start("MPG2-1-1", mps_path, output_path)
    with mps_path.open("w") as f:
        f.write("some settings would go here")
    bio.start("MPG2-1-1", mps_path, output_path)


def test_stop(mock_bio) -> None:
    """Test stop() function."""
    bio.stop("MPG2-1-1")

    mock_bio.eclab.simulate_bad_channel = True
    with pytest.raises(RuntimeError):
        bio.stop("MPG2-1-1")
    mock_bio.eclab.simulate_bad_channel = False


def test_get_experiment_info(mock_bio) -> None:
    """Test get_experiment_info() function."""
    res = bio.get_experiment_info("MPG2-1-1")
    expect = (
        "2025-11-10 15:22:09.494",
        None,
        "some\\folder\\location\\thisisthejob\\",
        ("file1.mpr", "file2.mpr", "file3.mpr", *[None] * 17),
    )
    assert res == expect

    mock_bio.eclab.simulate_bad_channel = True
    with pytest.raises(RuntimeError):
        res = bio.get_experiment_info("MPG2-1-1")
    mock_bio.eclab.simulate_bad_channel = False


def test_get_job_id(mock_bio) -> None:
    """Test get_job_id() function."""
    res = bio.get_job_id("MPG2-1-1")
    assert res == {"MPG2-1-1": "thisisthejob"}

    res = bio.get_job_id(["MPG2-1-1", "MPG2-1-2"])
    assert len(res) == 2

    res = bio.get_job_id(pipeline_ids=None)
    assert len(res) == 15

    res = bio.get_job_id(pipeline_ids=None, show_offline=True)
    assert len(res) == 18
