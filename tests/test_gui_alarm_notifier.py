"""GUI 报警与下载通知器测试（A4/A5 接线）。

采集侧信号从工作线程发出，必须由主线程的 QObject 槽接收后再写报警列表、
标题栏消息区与 CSV 列表，避免跨线程操作 QML 对象。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtCore import Property, QObject

from voc_app.gui.app import GuiAlarmNotifier


class FakeAlarmStore:
    def __init__(self) -> None:
        self.alarms: list[tuple[str, str]] = []

    def addAlarm(self, timestamp: str, message: str) -> None:  # noqa: N802
        self.alarms.append((timestamp, message))


class FakeTitlePanel(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._message = ""

    def _get_message(self) -> str:
        return self._message

    def _set_message(self, value: str) -> None:
        self._message = value

    systemMessage = Property(str, _get_message, _set_message)


class FakeCsvFileManager:
    def __init__(self, latest: str = "csv_file/data1.csv") -> None:
        self.refreshed = 0
        self.parsed: list[str] = []
        self._latest = latest

    def refresh_csv_files(self) -> None:
        self.refreshed += 1

    def latest_csv_file(self) -> str:
        return self._latest

    def parse_csv_file(self, name: str) -> None:
        self.parsed.append(name)


class GuiAlarmNotifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alarm_store = FakeAlarmStore()
        self.title_panel = FakeTitlePanel()
        self.csv_manager = FakeCsvFileManager()
        self.notifier = GuiAlarmNotifier(
            alarm_store=self.alarm_store,
            title_panel=self.title_panel,
            csv_file_manager=self.csv_manager,
        )

    def test_limit_violation_writes_alarm_and_message_bar(self) -> None:
        self.notifier.onLimitViolation("OOS", "VOC 高于上限 90 ppb")

        self.assertEqual(len(self.alarm_store.alarms), 1)
        _timestamp, message = self.alarm_store.alarms[0]
        self.assertEqual(message, "[OOS] VOC 高于上限 90 ppb")
        self.assertEqual(self.title_panel.systemMessage, "[OOS] VOC 高于上限 90 ppb")

    def test_acquisition_error_writes_alarm_and_message_bar(self) -> None:
        self.notifier.onError("FOUP 采集中断: 接收超时")

        self.assertEqual(len(self.alarm_store.alarms), 1)
        self.assertEqual(
            self.alarm_store.alarms[0][1], "[ERROR] FOUP 采集中断: 接收超时"
        )
        self.assertTrue(self.title_panel.systemMessage.startswith("[ERROR]"))

    def test_downloaded_logs_refresh_list_and_open_latest(self) -> None:
        self.notifier.onLogsDownloaded(2)

        self.assertEqual(self.csv_manager.refreshed, 1)
        self.assertEqual(self.csv_manager.parsed, ["csv_file/data1.csv"])
        self.assertEqual(self.alarm_store.alarms, [])

    def test_downloaded_zero_files_does_not_parse(self) -> None:
        self.notifier.onLogsDownloaded(0)

        self.assertEqual(self.csv_manager.refreshed, 1)
        self.assertEqual(self.csv_manager.parsed, [])

    def test_missing_title_panel_is_tolerated(self) -> None:
        notifier = GuiAlarmNotifier(
            alarm_store=self.alarm_store,
            title_panel=None,
            csv_file_manager=self.csv_manager,
        )
        notifier.onError("boom")
        self.assertEqual(len(self.alarm_store.alarms), 1)


if __name__ == "__main__":
    unittest.main()
