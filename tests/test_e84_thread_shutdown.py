"""R17：QThread 先退出，排队的控制器清理可能没有执行。

复现口径（审查报告）：工作线程正在处理 120ms 模拟任务时调用 ``stop()``，实测
线程已结束但 worker 仍持有控制器、refresh timer 仍 active，并产生跨线程停止
定时器警告。原因是排队 ``stop_controller`` 后立即 ``quit()``。

修复要求：等待 worker 清理完成后再退出线程，并有界等待、明确销毁顺序。
"""

from __future__ import annotations

import sys
import time
import types
from pathlib import Path

import pytest
from PySide6.QtCore import (
    QObject,
    QTimer,
    Qt,
    Signal,
    qInstallMessageHandler,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class _FakeRPiGPIO(types.ModuleType):
    BCM = "BCM"
    IN = "IN"
    OUT = "OUT"
    PUD_UP = "PUD_UP"
    PUD_DOWN = "PUD_DOWN"
    HIGH = 1
    LOW = 0

    def __init__(self) -> None:
        super().__init__("RPi.GPIO")

    def setmode(self, mode) -> None:  # noqa: D102
        pass

    def setup(self, *args, **kwargs) -> None:  # noqa: D102
        pass

    def output(self, *args, **kwargs) -> None:  # noqa: D102
        pass

    def input(self, *args, **kwargs) -> int:  # noqa: D102
        return 0

    def cleanup(self) -> None:  # noqa: D102
        pass


class _FakeRPi(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("RPi")
        self.GPIO = _FakeRPiGPIO()


if "RPi" not in sys.modules:
    sys.modules["RPi"] = _FakeRPi()
    sys.modules["RPi.GPIO"] = sys.modules["RPi"].GPIO  # type: ignore[attr-defined]

from voc_app.loadport import e84_thread  # noqa: E402


class FakeController(QObject):
    state_changed = Signal(str)
    warning = Signal(str)
    fatal_error = Signal(str)
    all_keys_set = Signal()
    data_collection_start = Signal()
    data_collection_stop = Signal()

    instances: list["FakeController"] = []

    def __init__(self, **_kwargs) -> None:
        super().__init__()
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.stop_called = False
        self.timer_active_after_stop: bool | None = None
        self.stop_thread_name = ""
        FakeController.instances.append(self)

    def start(self) -> None:  # noqa: D102
        self.timer.start()

    def stop(self) -> None:
        # 模拟真实清理耗时：排队的 stop_controller 必须有机会跑完
        time.sleep(0.12)
        self.stop_called = True
        self.timer.stop()
        self.timer_active_after_stop = self.timer.isActive()
        import threading

        self.stop_thread_name = threading.current_thread().name


def _wait_events(app, predicate, timeout: float = 3.0) -> bool:
    end_at = time.time() + timeout
    while time.time() < end_at:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    app.processEvents()
    return predicate()


@pytest.fixture()
def fake_controller(monkeypatch):
    FakeController.instances = []
    monkeypatch.setattr(e84_thread, "E84Controller", FakeController)
    return FakeController


def test_stop_waits_for_worker_cleanup(qapp, fake_controller) -> None:
    messages: list[str] = []
    previous = qInstallMessageHandler(
        lambda mode, context, message: messages.append(message)
    )
    try:
        controller_thread = e84_thread.E84ControllerThread()
        stopped_count = {"n": 0}
        controller_thread.stopped_controller.connect(
            lambda: stopped_count.__setitem__("n", stopped_count["n"] + 1)
        )
        controller_thread.start()
        assert _wait_events(qapp, lambda: controller_thread._controller is not None)

        controller = controller_thread._controller
        controller_thread.stop()

        assert not controller_thread._thread.isRunning(), "线程必须已退出"
        assert controller_thread._worker.controller is None, "worker 必须释放控制器"
        assert controller.stop_called is True, "排队的 stop_controller 必须执行"
        assert controller.timer_active_after_stop is False, "refresh timer 必须停止"
        assert stopped_count["n"] == 1, "stopped_controller 只能发一次"
    finally:
        qInstallMessageHandler(previous)

    assert not any("Timers cannot be stopped" in m or "killTimer" in m for m in messages), (
        f"出现跨线程定时器警告: {messages}"
    )


def test_stop_before_start_does_not_hang(qapp, fake_controller) -> None:
    controller_thread = e84_thread.E84ControllerThread()
    controller_thread.stop()
    assert not controller_thread._thread.isRunning()


def test_stop_is_idempotent(qapp, fake_controller) -> None:
    controller_thread = e84_thread.E84ControllerThread()
    stopped_count = {"n": 0}
    controller_thread.stopped_controller.connect(
        lambda: stopped_count.__setitem__("n", stopped_count["n"] + 1)
    )
    controller_thread.start()
    assert _wait_events(qapp, lambda: controller_thread._controller is not None)

    controller_thread.stop()
    controller_thread.stop()
    _wait_events(qapp, lambda: False, timeout=0.1)

    assert stopped_count["n"] == 1


def test_start_again_after_stop_creates_new_controller(qapp, fake_controller) -> None:
    controller_thread = e84_thread.E84ControllerThread()
    controller_thread.start()
    assert _wait_events(qapp, lambda: controller_thread._controller is not None)
    first = controller_thread._controller
    controller_thread.stop()
    assert first.stop_called is True

    controller_thread.start()
    assert _wait_events(
        qapp,
        lambda: controller_thread._controller is not None
        and controller_thread._controller is not first,
    )
    controller_thread.stop()
    assert FakeController.instances[-1].stop_called is True
