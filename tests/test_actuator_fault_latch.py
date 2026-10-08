"""执行机构本机通信异常必须进入 E84 故障锁存（R03）。

R03：`insert.move_to_step()` 抛 OSError 时只产生 actionFailed 与报警，
LoadportBridge 的故障锁存仍是 False、E84 的 set_ready_low_for_error 调用为 0。
设备主动上报的 `error:` 已经会锁存，本机连接/写入异常也必须走同一入口。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtCore import QObject, Signal  # noqa: E402

from voc_app.gui.app import LoadportActuatorController, LoadportBridge  # noqa: E402


class FakeSerialClient:
    def __init__(self, fail_actions=()) -> None:
        self.is_connected = True
        self.fail_actions = set(fail_actions)
        self.calls: list[str] = []
        self.callback = None

    def set_message_callback(self, callback) -> None:
        self.callback = callback

    def connect(self) -> None:
        self.is_connected = True

    def _do(self, name: str) -> None:
        self.calls.append(name)
        if name in self.fail_actions:
            raise OSError("USB write failed")

    def set_unlock(self) -> None:
        self._do("set_unlock")

    def set_lock(self) -> None:
        self._do("set_lock")

    def reset(self) -> None:
        self._do("reset")

    def move_to_step(self, step: int) -> None:
        self._do(f"move_to_step({step})")


class UnconnectableClient(FakeSerialClient):
    def __init__(self) -> None:
        super().__init__()
        self.is_connected = False

    def connect(self) -> None:
        raise OSError("no such device")


class FakeWorker(QObject):
    started_controller = Signal()
    stopped_controller = Signal()
    error = Signal(str)
    e84_warning = Signal(str)
    e84_fatal_error = Signal(str)
    e84_state_changed = Signal(str)
    controller_ready = Signal(object)
    all_keys_set = Signal()


class FakeAlarmStore:
    def __init__(self) -> None:
        self.alarms: list[str] = []

    def addAlarm(self, timestamp: str, message: str) -> None:  # noqa: N802
        self.alarms.append(message)


def _controller(lock=None, insert=None, **kwargs) -> LoadportActuatorController:
    return LoadportActuatorController(
        lock_client=lock or FakeSerialClient(),
        insert_client=insert or FakeSerialClient(),
        **kwargs,
    )


def test_insert_write_failure_emits_fault_signal() -> None:
    insert = FakeSerialClient(fail_actions={"move_to_step(4)"})
    controller = _controller(insert=insert)
    faults: list[tuple[str, str]] = []
    failures: list[str] = []
    controller.serialErrorDetected.connect(lambda s, p: faults.append((s, p)))
    controller.actionFailed.connect(failures.append)

    assert controller.run_insert_for_load() is False

    assert failures and "USB write failed" in failures[0]
    assert faults, "本机写入失败必须发出与设备错误相同的故障信号"
    assert faults[0][0] == "insert"
    assert "USB write failed" in faults[0][1]


def test_connect_failure_emits_fault_signal() -> None:
    controller = _controller(lock=UnconnectableClient())
    faults: list[tuple[str, str]] = []
    controller.serialErrorDetected.connect(lambda s, p: faults.append((s, p)))

    assert controller.run_unlock_only() is False

    assert faults and faults[0][0] == "lock"
    assert "no such device" in faults[0][1]


def test_multi_step_action_failure_is_latched_too() -> None:
    insert = FakeSerialClient(fail_actions={"move_to_step(8)"})
    controller = _controller(insert=insert)
    faults: list[tuple[str, str]] = []
    controller.serialErrorDetected.connect(lambda s, p: faults.append((s, p)))

    assert controller.run_unlock_for_unload() is False

    assert faults and faults[0][0] == "insert"


def test_fault_signal_can_be_disabled_by_config() -> None:
    insert = FakeSerialClient(fail_actions={"move_to_step(4)"})
    controller = _controller(insert=insert, emit_fault_on_failure=False)
    faults: list[tuple[str, str]] = []
    failures: list[str] = []
    controller.serialErrorDetected.connect(lambda s, p: faults.append((s, p)))
    controller.actionFailed.connect(failures.append)

    assert controller.run_insert_for_load() is False

    assert failures, "关闭联锁信号后仍要报告动作失败"
    assert faults == []


def test_device_reported_error_still_emits_fault_signal() -> None:
    lock = FakeSerialClient()
    controller = _controller(lock=lock)
    faults: list[tuple[str, str]] = []
    controller.serialErrorDetected.connect(lambda s, p: faults.append((s, p)))

    lock.callback("error: motor stuck")

    assert faults == [("lock", "error: motor stuck")]


def test_bridge_latches_e84_when_local_actuator_fails() -> None:
    insert = FakeSerialClient(fail_actions={"move_to_step(4)"})
    actuator = _controller(insert=insert)
    bridge = LoadportBridge(
        worker=FakeWorker(),
        alarm_store=FakeAlarmStore(),
        title_panel=None,
        actuator_controller=actuator,
    )

    assert actuator.run_insert_for_load() is False

    assert (
        bridge._pending_ready_low_due_to_error is True
        or bridge._actuator_error_latched is True
    ), "本机执行机构失败必须进入 E84 故障锁存流程"
