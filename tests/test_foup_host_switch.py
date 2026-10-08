"""修改 FOUP IP 后必须放弃旧设备连接与身份（R20）。

R20：已有 `_e84_communicator` 时修改 host，随后 `_ensure_e84_connected()`
返回的仍是原连接；界面 IP 已改变，但 E84 控制命令仍可能发往旧地址。
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.foup_acquisition import FoupAcquisitionController  # noqa: E402


class FakeCommunicator:
    created: list["FakeCommunicator"] = []

    def __init__(self, host, port, timeout=None) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.closed = False
        FakeCommunicator.created.append(self)

    def send(self, data: bytes) -> None:
        return None

    def recv(self, size: int) -> bytes:
        return b""

    def close(self) -> None:
        self.closed = True


def _controller(host: str = "10.0.0.1") -> FoupAcquisitionController:
    FakeCommunicator.created = []
    return FoupAcquisitionController(series_models=[], host=host, port=1234)


def test_host_change_closes_stale_e84_connection() -> None:
    with patch(
        "voc_app.gui.foup_acquisition.SocketCommunicator", FakeCommunicator
    ):
        controller = _controller()
        first = controller._ensure_e84_connected()
        assert first.host == "10.0.0.1"

        controller.host = "10.0.0.2"

        assert first.closed is True, "切换 IP 后必须关闭旧控制连接"
        assert controller._e84_communicator is None

        second = controller._ensure_e84_connected()
        assert second is not first
        assert second.host == "10.0.0.2", "新连接必须指向新地址"


def test_host_change_clears_stale_identity() -> None:
    with patch(
        "voc_app.gui.foup_acquisition.SocketCommunicator", FakeCommunicator
    ):
        controller = _controller()
        controller._server_version = "1.0.0"
        controller._command_prefix = "VOC"

        controller.host = "10.0.0.2"

        assert controller._server_version == ""
        assert controller._command_prefix == ""


def test_host_change_while_running_is_ignored() -> None:
    with patch(
        "voc_app.gui.foup_acquisition.SocketCommunicator", FakeCommunicator
    ):
        controller = _controller()
        first = controller._ensure_e84_connected()
        controller._running = True

        controller.host = "10.0.0.9"

        assert controller.host == "10.0.0.1", "采集中不允许切换 IP"
        assert first.closed is False
        assert controller._e84_communicator is first


def test_running_guard_does_not_close_on_invalid_host() -> None:
    with patch(
        "voc_app.gui.foup_acquisition.SocketCommunicator", FakeCommunicator
    ):
        controller = _controller()
        first = controller._ensure_e84_connected()

        controller.host = "   "

        assert controller.host == "10.0.0.1"
        assert first.closed is False
