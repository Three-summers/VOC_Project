"""硬件抽象层 + GUI 注入集成测试（使用 Mock）。"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.core.interfaces import HardwareController
from voc_app.hardware.factory import HardwareControllerFactory
from voc_app.hardware.loadport.e84_controller import Signal
from voc_app.gui.app import LoadportBridge, build_container


class MockHardwareController(HardwareController):
    """用于集成测试的 Mock 控制器。"""

    def __init__(self) -> None:
        self.started_controller = Signal()
        self.stopped_controller = Signal()
        self.error = Signal()
        self.e84_state_changed = Signal()
        self.e84_warning = Signal()
        self.e84_fatal_error = Signal()
        self.all_keys_set = Signal()

        self._running = False

    def start(self) -> None:
        self._running = True
        self.started_controller.emit()

    def stop(self) -> None:
        self._running = False
        self.stopped_controller.emit()

    def is_running(self) -> bool:
        return self._running


class DummyAlarmStore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def addAlarm(self, timestamp: str, message: str) -> None:
        self.calls.append((timestamp, message))


class TestGuiInjection(unittest.TestCase):
    def setUp(self) -> None:
        self._old_env = dict(os.environ)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._old_env)

    def test_container_can_resolve_mock_hardware_controller(self) -> None:
        os.environ["VOC_HARDWARE__LOADPORT__TYPE"] = "mock"
        container = build_container()

        factory = container.resolve(HardwareControllerFactory)
        factory.register("mock", MockHardwareController, overwrite=True, validate=True)

        controller = container.resolve(HardwareController)
        self.assertIsInstance(controller, MockHardwareController)

    def test_loadport_bridge_uses_constructor_injection(self) -> None:
        controller = MockHardwareController()
        alarm_store = DummyAlarmStore()

        bridge = LoadportBridge(
            controller=controller,
            alarm_store=alarm_store,
            title_panel=None,
            foup_controller=None,
        )

        bridge.start()
        self.assertTrue(controller.is_running())

        controller.e84_warning.emit("warn")
        controller.e84_fatal_error.emit("fatal")
        controller.error.emit("err")

        self.assertGreaterEqual(len(alarm_store.calls), 1)

        bridge.shutdown()
        self.assertFalse(controller.is_running())


if __name__ == "__main__":
    unittest.main()

