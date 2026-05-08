"""Fixtures for setting up tests."""

import json
import os
import socket
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

import aurora_biologic.biologic as bio
from aurora_biologic.cli.daemon import HOST, PORT

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


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --real-eclab flag to run integration tests against a live EC-Lab.exe."""
    parser.addoption(
        "--real-eclab",
        action="store_true",
        default=False,
        help=(
            "Run tests against a real EC-Lab.exe. "
            "Requires EC-Lab to be running, and a device available (virtual or real)."
        ),
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip real_eclab tests by default, skip mock tests when --real-eclab is passed."""
    real_eclab = config.getoption("--real-eclab")
    skip_mock = pytest.mark.skip(reason="use without --real-eclab to run mock tests")
    skip_real = pytest.mark.skip(reason="pass --real-eclab to run")
    for item in items:
        is_real = bool(item.get_closest_marker("real_eclab"))
        if real_eclab and not is_real:
            item.add_marker(skip_mock)
        elif not real_eclab and is_real:
            item.add_marker(skip_real)


def pytest_sessionstart(session: pytest.Session) -> None:
    """Ensure EC-lab and biologic daemon are not running before tests start."""
    if session.config.option.collectonly:
        return

    real_eclab = session.config.getoption("--real-eclab")

    # Ensure biologic daemon not already running
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex((HOST, PORT)) == 0:
            pytest.exit(
                f"Biologic daemon already running (or port {PORT} otherwise occupied). "
                "Please stop it before running tests.",
                returncode=1,
            )

    # Check EC-Lab running state matches the test mode
    result = subprocess.run(
        [r"C:\Windows\System32\tasklist.exe", "/FI", "IMAGENAME eq ECLab.exe", "/NH"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.exit(f"Failed to check for ECLab.exe: {result.stderr}", returncode=1)
    eclab_running = "eclab" in result.stdout.lower()
    if eclab_running and not real_eclab:
        pytest.exit(
            "ECLab.exe must not be running during mock tests. "
            "Close EC-Lab, or pass --real-eclab to run integration tests instead.",
            returncode=1,
        )
    if not eclab_running and real_eclab:
        pytest.exit(
            "ECLab.exe is not running. Start EC-Lab before using --real-eclab.",
            returncode=1,
        )


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


@pytest.fixture
def no_eclab_exe(test_config_dir: Path) -> Generator[Path]:
    """Point to a bad config."""
    os.environ["AURORA_BIOLOGIC_CONFIG_FILENAME"] = "config4.json"
    config_path = test_config_dir / "config4.json"
    with config_path.open("w") as f:
        json.dump(
            {
                "serial_to_name": {12345: "MPG2-1"},
                "eclab_path": "this/path/doesnt/exist/EClab.msi",
            },
            f,
        )
    yield config_path
    os.environ["AURORA_BIOLOGIC_CONFIG_FILENAME"] = "config.json"


@pytest.fixture(scope="module")
def real_bio() -> Generator[bio.BiologicAPI]:
    """BiologicAPI connected to the real EC-Lab.exe, used with --real-eclab."""
    bio._instance = None
    api = bio._get_api()
    yield api
    bio._instance = None
