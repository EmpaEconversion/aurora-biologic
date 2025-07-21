"""Python API for Biologic EC-lab potentiostats.

Contains the class BiologicAPI that provides methods to interact with the EC-lab
potentiostats.
"""

import json
import logging
import subprocess
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
config_dir = Path(user_config_dir(APP_NAME))
config_path = config_dir / CONFIG_FILENAME
if not config_path.exists():
    config_dir.mkdir(parents=True, exist_ok=True)
    default_config = {
        "serial_to_name": {
            12345: "example_device_1",
            12346: "example_device_2",
        },
    }
    with config_path.open("w") as f:
        json.dump(default_config, f, indent=4)
    logger.warning(
        "Config file created at %s. You must put serial number: device name pairs in the file.",
        config_dir,
    )

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


class BiologicAPI:
    """Class to interact with Biologic EC-lab potentiostats."""

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

        self.eclab.EnableMessagesWindows(0)
        try:
            self.pipelines: dict[str, dict] = self.get_all_pipelines()
        except ValueError:
            sleep(1)  # In case ec-lab needs time to initialize devices
            self.pipelines: dict[str, dict] = self.get_all_pipelines()

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

    def get_all_pipelines(self) -> dict[str, dict]:
        """Get all pipelines (device+channel) connected to EC-lab.

        Returns:
            dict: A dictionary with pipeline IDs as keys and their properties as values.

        """
        devices = {}
        for i in range(17):  # TODO: is there a way to get the total number of devices?
            sn, channel_sns, success = self.eclab.GetDeviceSN(i)
            if not success:
                continue
            if not sn:
                msg = (
                    "Found a device with serial number 0. "
                    "The device or EC-lab may not be properly initialized."
                )
                logger.warning(msg)
                continue
            device_name = serial_to_name.get(sn)
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
                }
        return devices

    def get_pipeline(self, pipeline: str) -> dict[str, dict]:
        """Get a specific pipeline by its ID. Raise ValueError if not found."""
        pipeline_dict = self.pipelines.get(pipeline)
        if not pipeline_dict:
            msg = (
                f"'{pipeline}' not known as a pipeline. Try 'biologic pipelines' to see available."
            )
            raise ValueError(msg)
        return pipeline_dict

    def select_pipeline(self, pipeline: str) -> None:
        """Switch EC-lab to the pipeline."""
        pipeline_dict = self.get_pipeline(pipeline)
        result = self.eclab.SelectChannel(
            pipeline_dict["device_index"],
            pipeline_dict["channel_index"],
        )
        if result != 1:
            msg = "Failed to switch channel"
            raise ValueError(msg)
        sleep(0.05)

    def get_status(self, pipeline_ids: list[str] | None = None) -> dict[str, dict]:
        """Get the status of the cycling process for all or selected pipelines.

        Args:
            pipeline_ids (list[str] | None): List of pipeline IDs to get status from.
                If None, will use the full channel map.

        Returns:
            dict: A dictionary with pipeline IDs as keys and their status as values.

        """
        if not pipeline_ids:
            pipeline_dicts = self.pipelines
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
                self.eclab.MeasureStatus(
                    pipeline_dict["device_index"],
                    pipeline_dict["channel_index"],
                ),
            )

        return status

    def load_settings(self, pipeline: str, settings_file: str | Path) -> None:
        """Load a protocol onto a pipeline."""
        settings_file = Path(settings_file)
        if not settings_file.exists():
            raise FileNotFoundError

        pipeline_dict = self.get_pipeline(pipeline)
        self.select_pipeline(pipeline)
        result = self.eclab.LoadSettings(
            pipeline_dict["device_index"],
            pipeline_dict["channel_index"],
            str(settings_file),
        )
        if result != 1:
            msg = "Failed to load settings."
            raise ValueError(msg)

    def run_channel(self, pipeline: str, output_path: str | Path) -> None:
        """Run the protocol on the given pipeline."""
        output_path = Path(output_path)
        pipeline_dict = self.get_pipeline(pipeline)
        self.select_pipeline(pipeline)
        result = self.eclab.RunChannel(
            pipeline_dict["device_index"],
            pipeline_dict["channel_index"],
            str(output_path),
        )

        if result != 1:
            msg = "Failed to start measurement."
            raise ValueError(msg)

    def start(self, pipeline: str, input_file: str | Path, output_file: str | Path) -> None:
        """Load and start a protocol on a pipeline."""
        self.load_settings(pipeline, input_file)
        self.run_channel(pipeline, output_file)

    def stop(self, pipeline: str) -> None:
        """Stop the cycling process on a pipeline."""
        pipeline_dict = self.get_pipeline(pipeline)
        self.select_pipeline(pipeline)
        result = self.eclab.StopChannel(
            pipeline_dict["device_index"],
            pipeline_dict["channel_index"],
        )

        if result != 1:
            msg = "Failed to stop measurement."
            raise ValueError(msg)

    def get_experiment_info(self, pipeline: str) -> tuple[str, str, str, tuple[str | None]]:
        """Return various experiment info for the job running on the pipeline."""
        pipeline_dict = self.get_pipeline(pipeline)
        self.select_pipeline(pipeline)
        # start, end, folder, files, result, mode
        start, end, folder, files, result = self.eclab.GetExperimentInfos(
            pipeline_dict["device_index"],
            pipeline_dict["channel_index"],
        )
        return start, end, folder, files

    def get_job_id(self, pipeline_ids: str | list[str] | None) -> dict[str, str | None]:
        """Get job IDs of selected channels.

        The job ID is the folder name if the job is running, None if it is finished.
        """
        if not pipeline_ids:
            pipeline_ids = list(self.pipelines.keys())
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
