"""Fake EC-Lab OLE-COM object used for testing."""


class FakeECLab:
    """Fake COM object for testing."""

    simulate_unselectable = False
    simulate_bad_channel = False

    def EnableMessagesWindows(self, enable: bool) -> None:
        return

    def GetDeviceSN(self, index: int) -> tuple[int, tuple, int]:
        if index == 0:
            return (
                123,
                (6001, 6002, 6003, 6004, 6005, 6006, 6007, 6008, 6009, 6010),
                1,
            )
        if index == 1:
            return (
                999,
                (7001, 7002, 7003, 7004, 7005),
                1,
            )
        if index == 2:
            return (0, (0, 0, 0), 1)
        return (0, (0, 0, 0, 0), 0)

    def SelectChannel(self, dev_idx: int, channel_idx: int) -> int:
        if self.simulate_unselectable:
            return 0
        return 1

    def LoadSettings(self, dev_idx: int, channel_idx: int, input_path: str) -> int:
        if self.simulate_bad_channel:
            return 0
        return 1

    def RunChannel(self, dev_idx: int, channel_idx: int, output_path: str) -> int:
        if self.simulate_bad_channel:
            return 0
        return 1

    def StopChannel(self, dev_idx: int, channel_idx: int) -> int:
        if self.simulate_bad_channel:
            return 0
        return 1

    def GetExperimentInfos(self, dev_idx: int, channel_idx: int) -> tuple:
        if self.simulate_bad_channel:
            return None, None, None, (*[None] * 20,), 0
        start = "2025-11-10 15:22:09.494"
        end = None
        folder = "some\\folder\\location\\thisisthejob\\"
        files = ("file1.mpr", "file2.mpr", "file3.mpr", *[None] * 17)  # seems to always give 20
        result = 1
        return start, end, folder, files, result

    def MeasureStatus(self, dev_idx: int, channel_idx: int) -> tuple:
        if dev_idx == 2:
            return (*[0.0] * 32,)
        return (
            1.0,
            1.0,
            1.0,
            1.0,
            5.0,
            4.0,
            2.0,
            30.0,
            2.0,
            2.0,
            3.0,
            0.0,
            0.0,
            0.0,
            38.0,
            5097814.5,
            3.616943597793579,
            -0.0009127054363489151,
            4.174654006958008,
            -0.5903541445732117,
            0.8317033648490906,
            -0.000252805941272527,
            -0.0012308506993576884,
            0.001,
            0.0,
            0.0,
            -1.0,
            61.0,
            61.0,
            0.0,
            0.0,
            0.0,
        )
