"""Fixtures for setting up tests."""

import json
import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

import aurora_biologic.biologic as bio

# Add tests directory to path so mocks can be imported
tests_dir = str(Path(__file__).parent)

# For the current Python process
sys.path.insert(0, tests_dir)

# For any subprocesses
original_pythonpath = os.environ.get("PYTHONPATH", "")
if original_pythonpath:
    os.environ["PYTHONPATH"] = f"{tests_dir}{os.pathsep}{original_pythonpath}"
else:
    os.environ["PYTHONPATH"] = tests_dir


@pytest.fixture(scope="session")
def test_config_dir(tmp_path_factory: pytest.TempPathFactory) -> Generator[Path]:
    """Create a temporary config directory - shared across all tests."""
    temp_dir = tmp_path_factory.mktemp("config")
    config_file = temp_dir / "config.json"
    test_config = {
        "serial_to_name": {123: "MPG2-1"},
        "eclab_path": "this/path/doesnt/exist/EClab.exe",
    }
    config_file.write_text(json.dumps(test_config))

    os.environ["AURORA_BIOLOGIC_CONFIG_DIR"] = str(temp_dir)
    os.environ["AURORA_BIOLOGIC_CONFIG_FILENAME"] = "config.json"
    os.environ["AURORA_BIOLOGIC_MOCK_OLECOM"] = "1"

    yield temp_dir

    # Cleanup
    del os.environ["AURORA_BIOLOGIC_CONFIG_DIR"]
    del os.environ["AURORA_BIOLOGIC_CONFIG_FILENAME"]
    del os.environ["AURORA_BIOLOGIC_MOCK_OLECOM"]


@pytest.fixture(scope="module")
def mock_bio(test_config_dir: Path) -> Generator[bio.BiologicAPI]:
    """Create BiologicAPI instance with fake EC-lab."""
    api = bio._get_api()
    yield api

    bio._instance = None  # Reset singleton


@pytest.fixture
def empty_config(test_config_dir: Path) -> Generator[Path]:
    """Point to a non-existent config."""
    os.environ["AURORA_BIOLOGIC_CONFIG_FILENAME"] = "config2.json"
    yield test_config_dir / "config2.json"
    os.environ["AURORA_BIOLOGIC_CONFIG_FILENAME"] = "config.json"


@pytest.fixture
def bad_config(test_config_dir: Path) -> Generator[Path]:
    """Point to a bad config."""
    os.environ["AURORA_BIOLOGIC_CONFIG_FILENAME"] = "config3.json"
    config_path = test_config_dir / "config3.json"
    with config_path.open("w") as f:
        json.dump({"serial_to_name": {12345: "OFFLINE-1"}}, f)
    yield config_path
    os.environ["AURORA_BIOLOGIC_CONFIG_FILENAME"] = "config.json"


@pytest.fixture
def no_eclab_config(test_config_dir: Path) -> Generator[Path]:
    """Point to a bad config."""
    os.environ["AURORA_BIOLOGIC_CONFIG_FILENAME"] = "config4.json"
    config_path = test_config_dir / "config4.json"
    with config_path.open("w") as f:
        json.dump({"serial_to_name": {12345: "MPG2-1"}}, f)
    yield config_path
    os.environ["AURORA_BIOLOGIC_CONFIG_FILENAME"] = "config.json"
