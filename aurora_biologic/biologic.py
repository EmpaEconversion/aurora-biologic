"""Python API for Biologic EC-lab potentiostats.

Contains the class BiologicAPI that provides methods to interact with the EC-lab
potentiostats.
"""

import functools
import json
import logging
import subprocess
from collections.abc import Callable
from pathlib import Path
from time import sleep
from types import TracebackType

import psutil
from comtypes.client import CreateObject
from platformdirs import user_config_dir

from aurora_biologic.dicts import status_codes, status_nested_codes

logger = logging.getLogger(__name__)

APP_NAME = "aurora-biologic"
CONFIG_FILENAME = "config.json"
config_dir = Path(user_config_dir(APP_NAME, appauthor=False))
config_path = config_dir / CONFIG_FILENAME
if not config_path.exists():
    config_dir.mkdir(parents=True, exist_ok=True)
    default_config = {
        "serial_to_name": {
            12345: "MPG2-1",
            12346: "MPG2-2",
        },
        "eclab_path": "C:/Program Files (x86)/EC-Lab/EClab.exe",
    }
    with config_path.open("w") as f:
        json.dump(default_config, f, indent=4)
    msg = (
        "IMPORTANT: Config file created at %s. "
        "You must put serial number: device name pairs in the file, "
        "and ensure the EC-lab executable path is correct."
    )
    logger.critical(msg, config_dir)

with config_path.open("r") as f:
    CONFIG = json.load(f)
serial_to_name = CONFIG.get("serial_to_name", {})
serial_to_name = {int(k): v for k, v in serial_to_name.items()}


def open_eclab() -> None:
    """Open EC-lab if it is not already running."""
    if not any("EClab" in proc.info["name"] for proc in psutil.process_iter(["name"])):
        if eclab_path := CONFIG.get("eclab_path"):
            subprocess.Popen([eclab_path])
            sleep(2)  # To allow the program to initialize
        else:
            msg = (
                "EC-lab is not running. "
                f"Either open EC-lab or add 'eclab_path' key to config at '{config_path}'"
            )
            raise ValueError(msg)


def _human_readable_status(status: tuple) -> dict:
    """Convert status codes to human-readable strings."""
    return {
        status_codes[i]: status_nested_codes[i].get(s, s) if i in status_nested_codes else s
        for i, s in enumerate(status[: len(status_codes)])
    }


def retry_with_backoff(delays_s: tuple[float, ...] = (0.01, 0.05, 0.25)) -> Callable:
    """Retry a function with exponential backoff.

    OLE-COM functions can fail if too many requests are made in a short time.
    This decorator will retry the function with increasing delays if
    RuntimeErrors are raised.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: tuple, **kwargs: dict) -> None:
            for delay in delays_s:
                try:
                    return func(*args, **kwargs)
                except RuntimeError:  # noqa: PERF203
                    sleep(delay)
            return func(*args, **kwargs)  # Final attempt, allow to raise error

        return wrapper

    return decorator


class BiologicAPI:
    """Class to interact with Biologic EC-lab potentiostats."""

    ### Initialization and context management ###

    def __init__(self) -> None:
        """Initialize the API with the host and port."""
        open_eclab()
        try:
            self.eclab = CreateObject("EClabCOM.EClabExe")
        except OSError as e:
            msg = (
                "Failed to connect to EC-Lab. "
                "Make sure you have EC-lab registered with OLE-COM. "
                "cd to the directory and use ECLab /regserver"
            )
            raise RuntimeError(msg) from e
        sleep(0.001)
        self.eclab.EnableMessagesWindows(0)
        sleep(0.001)
        self.pipelines: dict[str, dict] = self._get_all_pipelines()

    def __enter__(self) -> "BiologicAPI":
        """Do nothing when entering context."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Do nothing when exiting the context."""

    def __del__(self) -> None:
        """Do nothing when deleted."""

    ### Private methods to get pipelines and pipeline details ###

    def _get_all_pipelines(self) -> dict[str, dict]:
        """Get all pipelines (device+channel) connected to EC-lab.

        Returns:
            dict: A dictionary with pipeline IDs as keys and their properties as values.

        """
        devices = {}
        for i in range(100):
            sn, channel_sns, success = self.eclab.GetDeviceSN(i)
            if not success:  # Index out of range - stop searching
                break

            is_online = bool(sn)

            if is_online:
                device_name = serial_to_name.get(sn)
            else:  # Device found but not connected
                msg = (
                    f"Device position {i}: serial number and name not found, "
                    "it may be disconnected, uninitialized, or a virtual device. "
                    f"Naming the device 'OFFLINE-{i}'."
                )
                logger.warning(msg)
                device_name = f"OFFLINE-{i}"
            if not device_name:
                device_name = sn
                logger.warning(
                    "Device with serial number '%s' not found in config file. "
                    "The serial number will be used as device name.",
                    sn,
                )
            for j, channel_sn in enumerate(channel_sns):
                pipeline_id = f"{device_name}-{j + 1}"
                devices[pipeline_id] = {
                    "device_name": device_name,
                    "device_index": i,
                    "device_serial_number": int(sn),
                    "channel_index": j,
                    "channel_serial_number": int(channel_sn),
                    "is_online": is_online,
                }
        return devices

    def _get_pipeline(self, pipeline: str) -> dict[str, int]:
        """Get a specific pipeline by its ID. Raise ValueError if not found."""
        pipeline_dict = self.pipelines.get(pipeline)
        if not pipeline_dict:
            msg = (
                f"'{pipeline}' not known as a pipeline. Try 'biologic pipelines' to see available."
            )
            raise ValueError(msg)
        return pipeline_dict

    def _get_pipeline_indices(self, pipeline: str) -> tuple[int, int]:
        """Get device and channel indices for a pipeline."""
        pipeline_dict = self._get_pipeline(pipeline)
        return pipeline_dict["device_index"], pipeline_dict["channel_index"]

    def _assert_online(self, pipeline: str) -> None:
        """Raise error if pipeline belongs to offline device."""
        if not self._get_pipeline(pipeline).get("is_online"):
            msg = "Device is offline"
            raise ValueError(msg)

    ### EC-lab OLE-COM methods with retrying on failure ###

    @retry_with_backoff()
    def _olecom_select_channel(self, dev_idx: int, channel_idx: int) -> None:
        """Select a channel using OLE-COM with device and channel index."""
        result = self.eclab.SelectChannel(dev_idx, channel_idx)
        if result != 1:
            raise RuntimeError

    @retry_with_backoff()
    def _olecom_load_settings(self, dev_idx: int, channel_idx: int, settings_file: str) -> None:
        """Load settings on a channel using OLE-COM."""
        result = self.eclab.LoadSettings(
            dev_idx,
            channel_idx,
            str(settings_file),
        )
        if result != 1:
            raise RuntimeError

    @retry_with_backoff()
    def _olecom_run_channel(self, dev_idx: int, channel_idx: int, output_path: str) -> None:
        result = self.eclab.RunChannel(dev_idx, channel_idx, str(output_path))
        if result != 1:
            raise RuntimeError

    @retry_with_backoff()
    def _olecom_stop_channel(self, dev_idx: int, channel_idx: int) -> None:
        result = self.eclab.StopChannel(dev_idx, channel_idx)
        if result != 1:
            raise RuntimeError

    @retry_with_backoff()
    def _olecom_get_experiment_infos(
        self,
        dev_idx: int,
        channel_idx: int,
    ) -> tuple[str, str, str, tuple[str | None]]:
        start, end, folder, files, result = self.eclab.GetExperimentInfos(
            dev_idx,
            channel_idx,
        )
        if result != 1:
            raise RuntimeError
        return start, end, folder, files

    ### Public API methods ###

    def get_pipelines(self, *, show_offline: bool = False) -> dict[str, dict]:
        """Show pipeline details: index in EC-Lab, serial number, connection status etc.

        Args:
            show_offline (bool, default: False): Also show offline devices.

        """
        if show_offline:
            return self.pipelines
        return {k: v for k, v in self.pipelines.items() if v["is_online"]}

    def get_status(
        self, pipeline_ids: list[str] | None = None, *, show_offline: bool = False
    ) -> dict[str, dict]:
        """Get the status of the cycling process for all or selected pipelines.

        Args:
            pipeline_ids (list[str] | None): List of pipeline IDs to get status from.
                If None, will use the full channel map.
            show_offline (bool, default: False): Also show offline devices.

        Returns:
            dict: A dictionary with pipeline IDs as keys and their status as values.

        """
        if not pipeline_ids:
            if show_offline:
                pipeline_dicts = self.pipelines
            else:
                pipeline_dicts = {k: v for k, v in self.pipelines.items() if v["is_online"]}
        else:
            if isinstance(pipeline_ids, str):
                pipeline_ids = [pipeline_ids]
            pipeline_dicts = {
                pid: self.pipelines[pid] for pid in pipeline_ids if pid in self.pipelines
            }

        # Get the status of each pipeline and add it to the result dictionary
        status = {}
        for pipeline_id, pipeline_dict in pipeline_dicts.items():
            status[pipeline_id] = _human_readable_status(
                self.eclab.MeasureStatus(  # does not have fail state, no retrying
                    pipeline_dict["device_index"],
                    pipeline_dict["channel_index"],
                ),
            )

        return status

    def load_settings(self, pipeline: str, settings_file: str | Path) -> None:
        """Load a protocol onto a pipeline."""
        settings_file = Path(settings_file).resolve()
        if not settings_file.exists():
            raise FileNotFoundError

        dev_idx, channel_idx = self._get_pipeline_indices(pipeline)
        self._olecom_select_channel(dev_idx, channel_idx)
        self._olecom_load_settings(dev_idx, channel_idx, str(settings_file))

    def run_channel(self, pipeline: str, output_path: str | Path) -> None:
        """Run the protocol on the given pipeline."""
        self._assert_online(pipeline)
        output_path = Path(output_path).resolve()
        if output_path.is_dir():
            msg = "Must provide a full file path, not directory."
            raise ValueError(msg)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dev_idx, channel_idx = self._get_pipeline_indices(pipeline)
        self._olecom_select_channel(dev_idx, channel_idx)
        self._olecom_run_channel(dev_idx, channel_idx, str(output_path))

    def start(self, pipeline: str, input_file: str | Path, output_file: str | Path) -> None:
        """Load and start a protocol on a pipeline."""
        self.load_settings(pipeline, input_file)
        self.run_channel(pipeline, output_file)

    def stop(self, pipeline: str) -> None:
        """Stop the cycling process on a pipeline."""
        self._assert_online(pipeline)
        dev_idx, channel_idx = self._get_pipeline_indices(pipeline)
        self._olecom_stop_channel(dev_idx, channel_idx)

    def get_experiment_info(self, pipeline: str) -> tuple[str, str, str, tuple[str | None]]:
        """Return various experiment info for the job running on the pipeline."""
        dev_idx, channel_idx = self._get_pipeline_indices(pipeline)
        self._olecom_select_channel(dev_idx, channel_idx)
        return self._olecom_get_experiment_infos(dev_idx, channel_idx)

    def get_job_id(
        self, pipeline_ids: str | list[str] | None, *, show_offline: bool = False
    ) -> dict[str, str | None]:
        """Get job IDs of selected channels.

        The job ID is the folder name if the job is running, None if it is finished.

        Args:
            pipeline_ids (list[str] | None): List of pipeline IDs to get status from.
                If None, will use the full channel map.
            show_offline (bool, default: False): Also show offline devices.

        Returns:
            dict: A dictionary with pipeline IDs as keys and Job IDs as values.

        """
        if not pipeline_ids:
            if show_offline:
                pipeline_ids = list(self.pipelines.keys())
            else:
                pipeline_ids = [k for k, v in self.pipelines.items() if v["is_online"]]
        else:
            if isinstance(pipeline_ids, str):
                pipeline_ids = [pipeline_ids]
            pipeline_ids = [pid for pid in pipeline_ids if pid in self.pipelines]

        # Get experiment info is slow - first check running channels with status
        status = self.get_status(pipeline_ids)
        job_ids: dict[str, str | None] = {}
        for pid in pipeline_ids:
            if status[pid].get("Status", {}) in ["Run", "Pause", "Sync", "Pause_rec"]:
                start, end, folder, _ = self.get_experiment_info(pid)
                job_ids[pid] = (
                    folder.split("\\")[-2] if (start is not None and end is None) else None
                )
            else:
                job_ids[pid] = None
        return job_ids
