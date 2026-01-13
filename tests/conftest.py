"""Fixtures for setting up tests."""

import json
import os
import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

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


@pytest.fixture(scope="session", autouse=True)
def no_sleep() -> Generator:
    """Make all sleeps instant in biologic.py."""
    with patch("aurora_biologic.biologic.sleep", return_value=None):
        yield


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
