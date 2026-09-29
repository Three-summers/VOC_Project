"""下载结果可见性测试（A5）。

覆盖三件事：
1. 下位机 CSV 的时间戳是 "YYYY-MM-DD HH:MM:SS.mmm" 字符串，必须能解析出数据点；
2. 下载完成后文件列表要能刷新（否则新日志必须重启才能看到）；
3. 一个文件都没下到时要报错，而不是静默"下载完成: 0 个文件"。
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.csv_model import CsvFileManager
from voc_app.gui.foup_acquisition import FoupAcquisitionController

DEVICE_CSV = (
    "timestamp, area_data, mark_data, AQ7PID, PM_AVG, PD_AVG, FM_AVG, PumpM_AVG\n"
    "2026-02-26 10:30:00.123,12,3,1.5,2.5,3.5,4.5,5.5\n"
    "2026-02-26 10:30:01.223,12,3,1.6,2.6,3.6,4.6,5.6\n"
)


class _PackedCommunicator:
    """下位机控制连接的最小替身（stop 命令会回 ACK）。"""

    def __init__(self, *args, **kwargs) -> None:
        self.sent: list[bytes] = []

    def send(self, data: bytes) -> None:
        self.sent.append(data)

    def recv(self, size: int) -> bytes:
        return b""

    def close(self) -> None:
        return None


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class DeviceCsvParsingTests(unittest.TestCase):
    def test_parse_device_csv_with_string_timestamp(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "Log"
            _write(log_dir / "csv_file" / "data202602261030.csv", DEVICE_CSV)
            manager = CsvFileManager(log_dir=log_dir)

            manager.parse_csv_file("csv_file/data202602261030.csv")

            model = manager.dataModel
            self.assertEqual(
                model.columnNames,
                ["area_data", "mark_data", "AQ7PID", "PM_AVG", "PD_AVG", "FM_AVG", "PumpM_AVG"],
            )
            points = model.get(0)["dataPoints"]
            self.assertEqual(len(points), 2, "设备格式 CSV 必须能解析出数据点")
            expected_x = datetime(2026, 2, 26, 10, 30, 0, 123000).timestamp() * 1000.0
            self.assertAlmostEqual(points[0]["x"], expected_x, places=3)
            self.assertAlmostEqual(points[0]["y"], 12.0, places=6)
            self.assertAlmostEqual(model.get(2)["dataPoints"][1]["y"], 1.6, places=6)

    def test_legacy_numeric_timestamp_still_supported(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "Log"
            _write(log_dir / "data1.csv", "Time,Value\n0,10\n1,12\n")
            manager = CsvFileManager(log_dir=log_dir)
            manager.parse_csv_file("data1.csv")
            points = manager.dataModel.get(0)["dataPoints"]
            self.assertEqual(len(points), 2)
            self.assertAlmostEqual(points[1]["x"], 1000.0, places=3)


class CsvRefreshTests(unittest.TestCase):
    def test_refresh_csv_files_detects_new_download(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "Log"
            (log_dir / "csv_file").mkdir(parents=True)
            manager = CsvFileManager(log_dir=log_dir)
            self.assertEqual(manager.csvFiles, [])

            changed: list[bool] = []
            manager.csvFilesChanged.connect(lambda: changed.append(True))

            _write(log_dir / "csv_file" / "data202602261030.csv", DEVICE_CSV)
            manager.refresh_csv_files()

            self.assertEqual(manager.csvFiles, ["csv_file/data202602261030.csv"])
            self.assertTrue(changed, "刷新后必须通知 QML 更新列表")

    def test_latest_csv_file_returns_newest(self) -> None:
        import os
        import tempfile
        import time

        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "Log"
            old = _write(log_dir / "data_old.csv", "Time,Value\n0,1\n")
            time.sleep(0.01)
            new = _write(log_dir / "csv_file" / "data_new.csv", DEVICE_CSV)
            os.utime(old, (time.time() - 60, time.time() - 60))

            manager = CsvFileManager(log_dir=log_dir)
            self.assertEqual(manager.latest_csv_file(), "csv_file/data_new.csv")
            self.assertNotEqual(manager.latest_csv_file(), "data_old.csv")


class DownloadOutcomeSignalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = FoupAcquisitionController(series_models=[])
        self.controller._apply_server_identity(prefix="VOC")
        self.errors: list[str] = []
        self.downloads: list[int] = []
        self.controller.errorOccurred.connect(self.errors.append)
        self.controller.logsDownloaded.connect(self.downloads.append)

    def _run_stop(self, saved_files: list[str]) -> bool:
        with patch(
            "voc_app.gui.foup_acquisition.SocketCommunicator", _PackedCommunicator
        ):
            with patch.object(
                self.controller, "_download_logs", return_value=saved_files
            ):
                return self.controller.e84StopDataCollectionForLoad()

    def test_reports_downloaded_file_count(self) -> None:
        ok = self._run_stop(["/data/Log/files/csv_file/data1.csv"])

        self.assertTrue(ok)
        self.assertEqual(self.downloads, [1])
        self.assertEqual(self.errors, [])

    def test_reports_error_when_nothing_downloaded(self) -> None:
        ok = self._run_stop([])

        self.assertTrue(ok, "传输本身完成，不应判定为命令失败")
        self.assertEqual(self.downloads, [0])
        self.assertTrue(self.errors, "0 个文件必须给出显式错误")
        self.assertIn("未下载到", self.errors[0])


if __name__ == "__main__":
    unittest.main()
