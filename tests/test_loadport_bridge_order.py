"""LoadportBridge 业务时序测试。

覆盖 E84 Unload 阶段"先让 FOUP 开始采集，再断开对插/解锁"的顺序要求：
对插连接器同时承载到 FOUP 的网络通道，先执行 move_to_step(8) 会让 START 命令
发不到下位机（详见 docs/e84.md 的"关键点1"与下位机 socket_cmd_server.c）。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtCore import QObject, Signal

from voc_app.gui.app import LoadportBridge


class FakeWorker(QObject):
    """只提供 LoadportBridge 需要连接的信号。"""

    started_controller = Signal()
    stopped_controller = Signal()
    error = Signal(str)
    e84_warning = Signal(str)
    e84_fatal_error = Signal(str)
    e84_state_changed = Signal(str)


class FakeAlarmStore:
    def __init__(self) -> None:
        self.alarms: list[str] = []

    def addAlarm(self, timestamp: str, message: str) -> None:  # noqa: N802
        self.alarms.append(message)


class FakeActuatorController(QObject):
    serialErrorDetected = Signal(str, str)
    requestE84ErrorRecovery = Signal()

    def __init__(self, log: list[str], ok: bool = True) -> None:
        super().__init__()
        self.log = log
        self.ok = ok

    def run_unlock_for_unload(self) -> bool:
        self.log.append("actuator:unlock_for_unload")
        return self.ok

    def run_lock_for_load(self) -> bool:
        self.log.append("actuator:lock_for_load")
        return self.ok


class FakeFoupController:
    def __init__(self, log: list[str], ok: bool = True) -> None:
        self.log = log
        self.ok = ok

    def e84StartDataCollectionForUnload(self) -> bool:  # noqa: N802
        self.log.append("foup:start_collection")
        return self.ok

    def e84StopDataCollectionForLoad(self) -> bool:  # noqa: N802
        self.log.append("foup:stop_collection")
        return self.ok


class LoadportBridgeOrderTests(unittest.TestCase):
    def _build_bridge(self, log: list[str], foup_ok: bool = True, actuator_ok: bool = True):
        alarms = FakeAlarmStore()
        bridge = LoadportBridge(
            worker=FakeWorker(),
            alarm_store=alarms,
            title_panel=None,
            foup_controller=FakeFoupController(log, ok=foup_ok),
            actuator_controller=FakeActuatorController(log, ok=actuator_ok),
        )
        return bridge, alarms

    def test_unload_starts_collection_before_releasing_the_connector(self) -> None:
        log: list[str] = []
        bridge, _alarms = self._build_bridge(log)

        bridge._on_data_collection_start()

        self.assertEqual(
            log,
            ["foup:start_collection", "actuator:unlock_for_unload"],
        )

    def test_unload_still_releases_connector_when_start_command_fails(self) -> None:
        """START 失败也必须继续机械动作，否则 FOUP 被夹住无法被天车取走。"""
        log: list[str] = []
        bridge, alarms = self._build_bridge(log, foup_ok=False)

        bridge._on_data_collection_start()

        self.assertEqual(
            log,
            ["foup:start_collection", "actuator:unlock_for_unload"],
        )
        self.assertTrue(any("采集启动" in message for message in alarms.alarms))

    def test_load_mates_connector_before_stopping_and_downloading(self) -> None:
        log: list[str] = []
        bridge, _alarms = self._build_bridge(log)

        bridge._on_data_collection_stop()

        self.assertEqual(
            log,
            ["actuator:lock_for_load", "foup:stop_collection"],
        )


if __name__ == "__main__":
    unittest.main()
