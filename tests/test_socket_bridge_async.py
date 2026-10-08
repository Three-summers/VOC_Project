"""R33：通用异步 Socket 桥接执行一次后永久 busy。

复现口径（审查报告）：第一次异步操作已返回 ok，主 Qt 事件循环持续处理 500ms 后
``busy`` 仍为 True；第二次操作被"上一个操作尚未完成"拒绝。

根因：``QTimer.singleShot()`` 在 Python 工作线程中没有接收上下文的投递目标，
回调不会回到主线程，清除 busy 的收尾永远不执行。

修复要求：用绑定到主线程 QObject 的队列信号把异步收尾投递回主线程。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Signal, Slot

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.qml_socket_client_bridge import QmlSocketClientBridge


class FakeCommunicator:
    def __init__(self, host, port, timeout=None) -> None:
        self.host = host
        self.port = port
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeClient:
    def __init__(self, communicator, max_message_size=None) -> None:
        self.communicator = communicator

    def run_shell(self, command: str) -> str:
        return f"ran:{command}"

    def get_file(self, remote_path: str, dest_root=None) -> list:
        return [f"{dest_root or '/tmp'}/downloaded"]

    def close(self) -> None:
        self.communicator.close()


class Receiver(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.shell: list[str] = []
        self.files: list[list] = []
        self.errors: list[str] = []

    @Slot(str)
    def on_shell(self, output: str) -> None:  # noqa: D102
        self.shell.append(output)

    @Slot(list)
    def on_file(self, paths: list) -> None:  # noqa: D102
        self.files.append(list(paths))

    @Slot(str)
    def on_error(self, message: str) -> None:  # noqa: D102
        self.errors.append(message)


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
def bridge(qapp):
    instance = QmlSocketClientBridge(FakeClient, FakeCommunicator)
    assert instance.connectSocket("127.0.0.1", 12345) is True
    yield instance, qapp
    instance.close()
    qapp.processEvents()


def test_async_shell_clears_busy_and_allows_second_operation(bridge) -> None:
    instance, app = bridge
    receiver = Receiver()
    instance.runShellFinished.connect(receiver.on_shell)

    instance.runShellAsync("first")
    assert instance.busy is True

    assert _wait_events(app, lambda: instance.busy is False), (
        "异步操作结束后 busy 必须回到 False"
    )
    assert receiver.shell == ["ran:first"]

    instance.runShellAsync("second")
    assert _wait_events(app, lambda: len(receiver.shell) == 2), (
        "busy 未清除导致第二次操作被拒绝"
    )
    assert receiver.shell == ["ran:first", "ran:second"]
    assert receiver.errors == []


def test_async_failure_clears_busy_and_reports_error(bridge) -> None:
    instance, app = bridge
    receiver = Receiver()
    instance.errorOccurred.connect(receiver.on_error)

    def boom(_command: str) -> str:
        raise RuntimeError("remote exploded")

    instance._client.run_shell = boom  # type: ignore[assignment]
    instance.runShellAsync("bad")

    assert _wait_events(app, lambda: instance.busy is False)
    assert receiver.errors == ["remote exploded"]


def test_async_get_file_clears_busy(bridge) -> None:
    instance, app = bridge
    receiver = Receiver()
    instance.getFileFinished.connect(receiver.on_file)

    instance.getFileAsync("/remote/log")

    assert _wait_events(app, lambda: instance.busy is False)
    assert receiver.files == [["/tmp/downloaded"]]


def test_second_operation_rejected_only_while_busy(bridge) -> None:
    """确认 busy 语义仍然有效：真正并发时拒绝，完成后接受。"""
    instance, app = bridge
    receiver = Receiver()
    instance.runShellFinished.connect(receiver.on_shell)

    instance.runShellAsync("slow")
    assert instance.busy is True

    assert _wait_events(app, lambda: instance.busy is False)
    instance.runShellAsync("after")
    assert _wait_events(app, lambda: len(receiver.shell) == 2)
