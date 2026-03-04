"""AlarmStore 告警去重与时间窗口测试。"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from voc_app.gui.alarm_store import AlarmStore


class AlarmStoreTests(unittest.TestCase):
    def test_duplicate_alarm_is_suppressed_within_window(self) -> None:
        store = AlarmStore(duplicate_window_seconds=60.0)
        with patch("voc_app.gui.alarm_store.time.monotonic", side_effect=[100.0, 130.0]):
            store.addAlarm("2026-02-28 10:00:00", "[ERROR] same alarm")
            store.addAlarm("2026-02-28 10:00:30", "[ERROR] same alarm")
        self.assertEqual(store.alarmModel.rowCount(), 1)

    def test_duplicate_alarm_is_allowed_after_window(self) -> None:
        store = AlarmStore(duplicate_window_seconds=60.0)
        with patch("voc_app.gui.alarm_store.time.monotonic", side_effect=[100.0, 161.0]):
            store.addAlarm("2026-02-28 10:00:00", "[ERROR] same alarm")
            store.addAlarm("2026-02-28 10:01:01", "[ERROR] same alarm")
        self.assertEqual(store.alarmModel.rowCount(), 2)

    def test_clear_resets_duplicate_suppression_state(self) -> None:
        store = AlarmStore(duplicate_window_seconds=60.0)
        with patch("voc_app.gui.alarm_store.time.monotonic", return_value=100.0):
            store.addAlarm("2026-02-28 10:00:00", "[ERROR] same alarm")
        store.clearAlarms()
        with patch("voc_app.gui.alarm_store.time.monotonic", return_value=110.0):
            store.addAlarm("2026-02-28 10:00:10", "[ERROR] same alarm")
        self.assertEqual(store.alarmModel.rowCount(), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
