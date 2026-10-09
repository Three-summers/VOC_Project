"""正常模式手动会话：开始采集下发 start，停止采集先下载再 stop。

背景：正常模式原先只做"置标志 + 下载"，既不发 start 也不发 stop，与真实 E84
路径不一致。现在与 E84 对齐：

    开始采集 → {P}_sample_type_normal + {P}_data_coll_ctrl_start
              → 下位机写入自身存储，界面不显示实时曲线
    停止采集 → **先**下载日志，**再**发 {P}_data_coll_ctrl_stop

两条硬约束都由下位机源码决定（voc_251028）：

1. 下位机收到 stop 后 5 秒反挂载 SD 分区（``VOC_cmd_deal.c`` 的
   ``end_collect_data``），所以顺序必须是"下载 → stop"。
2. 下位机 socket 服务（``socket_cmd_server.c``）在 EPOLLET 下一直 read 到
   EAGAIN **或 EOF**；只要在同一轮 read 里读到 FIN，就会走
   ``if (done) { close(fd); }`` 分支并且**不调用** ``process_client_message``，
   已收到的命令被整批丢弃。因此客户端**发完命令不能立刻关闭连接**：
   - ``start`` 没有 ACK → 连接必须保留到停止阶段；
   - ``stop`` 有 ACK → 读到 ACK 再关闭。
"""

from __future__ import annotations

import struct
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.foup_acquisition import FoupAcquisitionController  # noqa: E402

QML_DIR = SRC_DIR / "voc_app" / "gui" / "qml"
CONFIG_COMMANDS_QML = QML_DIR / "commands" / "Config_foupCommands.qml"


# ---------------------------------------------------------------------------
# 替身
# ---------------------------------------------------------------------------


def _pack_message(text: str) -> bytes:
    payload = text.encode("utf-8")
    return struct.pack(">I", len(payload)) + payload


def _unpack_command(frame: bytes) -> str:
    (size,) = struct.unpack(">I", frame[:4])
    return frame[4 : 4 + size].decode("utf-8")


class _RecordingComm:
    """长度前缀协议的最小替身：记录 send / recv / close 的顺序。"""

    def __init__(
        self,
        responses: list[str] | None = None,
        events: list[str] | None = None,
        label: str = "c0",
    ) -> None:
        self._buffer = bytearray()
        for message in responses or []:
            self._buffer.extend(_pack_message(message))
        self._events = events
        self._label = label
        self.sent: list[str] = []
        self.closed = False

    def _record(self, what: str) -> None:
        if self._events is not None:
            self._events.append(f"{self._label}:{what}")

    def send(self, data: bytes) -> None:
        command = _unpack_command(data)
        self.sent.append(command)
        self._record(f"send:{command}")

    def recv(self, size: int) -> bytes:
        if not self._buffer:
            return b""
        chunk = bytes(self._buffer[:size])
        del self._buffer[:size]
        if chunk:
            self._record("recv")
        return chunk

    def close(self) -> None:
        self.closed = True
        self._record("close")


class _SeriesSpy:
    def __init__(self) -> None:
        self.points: list[tuple[float, float]] = []

    def append_point(self, x, y) -> None:  # noqa: ANN001
        self.points.append((float(x), float(y)))

    def clear(self) -> None:
        self.points.clear()


def _wait_until(predicate, timeout: float = 5.0) -> bool:  # noqa: ANN001
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _worker_finished(controller: FoupAcquisitionController) -> bool:
    worker = controller._worker
    return worker is None or not worker.is_alive()


def _make_factory(communicators: list[_RecordingComm], events: list[str]):
    """第 1 条连接回版本号，之后的连接回 ACK（stop 的应答）。"""

    def factory(host, port, timeout=None):  # noqa: ANN001, ARG001
        index = len(communicators)
        responses = ["VOC,V1.0.0"] if index == 0 else ["ACK"]
        comm = _RecordingComm(responses=responses, events=events, label=f"c{index}")
        communicators.append(comm)
        return comm

    return factory


def _sends(events: list[str]) -> list[str]:
    return [event for event in events if ":send:" in event]


@pytest.fixture()
def normal_controller(qapp):  # noqa: ARG001
    series = _SeriesSpy()
    controller = FoupAcquisitionController(
        series_models=[series], host="127.0.0.1", port=65432
    )
    controller.operationMode = "normal"
    controller.normalModeRemotePath = "/home/root/files"
    yield controller, series
    controller.shutdown()


# ---------------------------------------------------------------------------
# 开始采集
# ---------------------------------------------------------------------------


def test_normal_start_declares_normal_then_starts(normal_controller) -> None:
    """先声明 normal 再 start：下位机 VOC_Sample_Type 是全局标志。"""
    controller, _series = normal_controller
    events: list[str] = []
    communicators: list[_RecordingComm] = []

    with patch(
        "voc_app.gui.foup_acquisition.SocketCommunicator",
        side_effect=_make_factory(communicators, events),
    ):
        controller.startAcquisition()
        assert _wait_until(lambda: controller._normal_session_active), (
            controller.statusMessage
        )

    assert _sends(events) == [
        "c0:send:get_function_version_info",
        "c0:send:VOC_sample_type_normal",
        "c0:send:VOC_data_coll_ctrl_start",
    ]
    assert controller.running is True, "会话进行中界面必须显示采集中"
    assert "正常模式" in controller.statusMessage


def test_normal_start_keeps_connection_open(normal_controller) -> None:
    """start 没有 ACK：发完立刻关闭会让服务端把命令整批丢弃。

    下位机 socket 服务在同一轮 read 里读到 FIN 时会跳过 process_client_message，
    因此"发完就关"是这条命令丢失的直接原因。
    """
    controller, _series = normal_controller
    events: list[str] = []
    communicators: list[_RecordingComm] = []

    with patch(
        "voc_app.gui.foup_acquisition.SocketCommunicator",
        side_effect=_make_factory(communicators, events),
    ):
        controller.startAcquisition()
        assert _wait_until(lambda: controller._normal_session_active)

    assert "c0:close" not in events, (
        "start 之后不得立刻关闭连接，否则下位机收不到 start"
    )
    assert communicators[0].closed is False


def test_normal_start_does_not_fill_realtime_curves(normal_controller) -> None:
    """正常模式没有实时数据可供显示。"""
    controller, series = normal_controller
    events: list[str] = []
    communicators: list[_RecordingComm] = []

    with patch(
        "voc_app.gui.foup_acquisition.SocketCommunicator",
        side_effect=_make_factory(communicators, events),
    ):
        controller.startAcquisition()
        assert _wait_until(lambda: controller._normal_session_active)

    assert series.points == [], "正常模式不应向实时曲线写入数据点"


def test_normal_start_reports_error_when_start_send_fails(normal_controller) -> None:
    """命令发不出去必须报错，不能静默显示"采集中"。"""
    controller, _series = normal_controller
    events: list[str] = []

    class _FailOnStart(_RecordingComm):
        def send(self, data: bytes) -> None:
            super().send(data)
            if self.sent[-1].endswith("_data_coll_ctrl_start"):
                raise OSError("broken pipe")

    def factory(host, port, timeout=None):  # noqa: ANN001, ARG001
        return _FailOnStart(responses=["VOC,V1.0.0"], events=events, label="c0")

    with patch("voc_app.gui.foup_acquisition.SocketCommunicator", side_effect=factory):
        controller.startAcquisition()
        assert _wait_until(lambda: _worker_finished(controller))

    assert controller._normal_session_active is False
    assert controller.running is False
    assert "启动采集命令发送失败" in controller.statusMessage


# ---------------------------------------------------------------------------
# 停止采集
# ---------------------------------------------------------------------------


def test_normal_stop_downloads_before_stop(normal_controller) -> None:
    """停止顺序必须是"下载 → stop"，否则 SD 已反挂载。"""
    controller, _series = normal_controller
    events: list[str] = []
    communicators: list[_RecordingComm] = []

    def fake_download() -> list[str]:
        events.append("download")
        return ["/tmp/fake_log.csv"]

    with patch(
        "voc_app.gui.foup_acquisition.SocketCommunicator",
        side_effect=_make_factory(communicators, events),
    ):
        with patch.object(controller, "_download_logs", side_effect=fake_download):
            controller.startAcquisition()
            assert _wait_until(lambda: controller._normal_session_active)

            events.clear()  # 只核对停止阶段
            controller.stopAcquisition()
            assert _wait_until(lambda: not controller.running), controller.statusMessage

    assert events[0] == "c0:close", "停止阶段先释放会话连接"
    assert events[1] == "download", "必须先下载"
    assert "c1:send:VOC_data_coll_ctrl_stop" in events, "下载之后才发 stop"
    assert "c1:recv" in events, "stop 有 ACK，必须等 ACK 回来"
    assert events.index("c1:recv") < events.index("c1:close"), (
        "必须读到 stop 的 ACK 再关闭连接，否则 stop 会被服务端丢弃"
    )
    assert controller.running is False
    assert controller._normal_session_active is False
    assert "下载完成" in controller.statusMessage


def test_normal_stop_still_sends_stop_when_download_fails(normal_controller) -> None:
    """下载失败也要尽力停止采集，否则下位机持续写文件、不关文件。"""
    controller, _series = normal_controller
    events: list[str] = []
    communicators: list[_RecordingComm] = []

    with patch(
        "voc_app.gui.foup_acquisition.SocketCommunicator",
        side_effect=_make_factory(communicators, events),
    ):
        with patch.object(
            controller, "_download_logs", side_effect=RuntimeError("download broken")
        ):
            controller.startAcquisition()
            assert _wait_until(lambda: controller._normal_session_active)

            events.clear()
            controller.stopAcquisition()
            assert _wait_until(lambda: not controller.running)

    assert "c1:send:VOC_data_coll_ctrl_stop" in events
    assert controller.running is False


def test_stop_downloads_even_if_mode_switched_mid_session(normal_controller) -> None:
    """会话进行中切回 test 模式，停止仍须走"先下载再 stop"。"""
    controller, _series = normal_controller
    events: list[str] = []
    communicators: list[_RecordingComm] = []

    def fake_download() -> list[str]:
        events.append("download")
        return ["/tmp/fake_log.csv"]

    with patch(
        "voc_app.gui.foup_acquisition.SocketCommunicator",
        side_effect=_make_factory(communicators, events),
    ):
        with patch.object(controller, "_download_logs", side_effect=fake_download):
            controller.startAcquisition()
            assert _wait_until(lambda: controller._normal_session_active)

            controller.operationMode = "test"  # 操作员中途切了模式
            events.clear()
            controller.stopAcquisition()
            assert _wait_until(lambda: not controller.running), controller.statusMessage

    assert events[0] == "c0:close"
    assert events[1] == "download"
    assert "c1:send:VOC_data_coll_ctrl_stop" in events


def test_shutdown_does_not_download_or_stop(normal_controller) -> None:
    """退出应用时不能触发下载/停止：下载线程会随进程被杀掉。"""
    controller, _series = normal_controller
    events: list[str] = []
    communicators: list[_RecordingComm] = []

    with patch(
        "voc_app.gui.foup_acquisition.SocketCommunicator",
        side_effect=_make_factory(communicators, events),
    ):
        controller.startAcquisition()
        assert _wait_until(lambda: controller._normal_session_active)
        events.clear()

        controller.shutdown()

    assert _sends(events) == [], "退出不应再下发任何命令"
    assert "download" not in events
    assert controller.running is False


# ---------------------------------------------------------------------------
# 界面：正常模式下"开始采集"必须可点
# ---------------------------------------------------------------------------


class _FakeAcquisition(QObject):
    channelCountChanged = Signal()
    hostChanged = Signal()
    operationModeChanged = Signal()
    runningChanged = Signal()
    statusMessageChanged = Signal()
    channelConfigChanged = Signal(int)

    def __init__(self, mode: str = "normal", running: bool = False) -> None:
        super().__init__()
        self._mode = mode
        self._running = running

    @Property(int, notify=channelCountChanged)
    def channelCount(self) -> int:  # noqa: D102
        return 1

    @Property(str, notify=hostChanged)
    def host(self) -> str:  # noqa: D102
        return "127.0.0.1"

    @Property(str, notify=operationModeChanged)
    def operationMode(self) -> str:  # noqa: D102
        return self._mode

    @Property(bool, notify=runningChanged)
    def running(self) -> bool:  # noqa: D102
        return self._running

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:  # noqa: D102
        return "idle"

    @Slot(int, result=str)
    def getUnit(self, idx: int) -> str:  # noqa: D102
        return f"unit{idx}"

    @Slot(int, result=float)
    def getOocUpper(self, idx: int) -> float:  # noqa: D102
        return 70.0 + idx

    @Slot(int, result=float)
    def getOocLower(self, idx: int) -> float:  # noqa: D102
        return 20.0 + idx

    @Slot(int, result=float)
    def getOosUpper(self, idx: int) -> float:  # noqa: D102
        return 80.0 + idx

    @Slot(int, result=float)
    def getOosLower(self, idx: int) -> float:  # noqa: D102
        return 10.0 + idx

    @Slot(int, result=float)
    def getTarget(self, idx: int) -> float:  # noqa: D102
        return 50.0 + idx

    @Slot(int, str)
    def setChannelUnit(self, idx: int, unit: str) -> None:  # noqa: D102, ARG002
        return None

    @Slot(int, float, float, float, float, float)
    def setChannelLimits(self, idx, a, b, c, d, e) -> None:  # noqa: D102, ARG002
        return None

    @Slot()
    def startAcquisition(self) -> None:  # noqa: D102
        return None

    @Slot()
    def stopAcquisition(self) -> None:  # noqa: D102
        return None


def _build_config_commands(app, holder: list, mode: str, running: bool):
    _ = app
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    acquisition = _FakeAcquisition(mode=mode, running=running)
    engine.rootContext().setContextProperty("foupAcquisition", acquisition)
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(CONFIG_COMMANDS_QML)))
    assert component.status() != QQmlComponent.Status.Error, [
        error.toString() for error in component.errors()
    ]
    root = component.create()
    assert root is not None
    # engine / component / acquisition 都必须保持存活：context property 不接管
    # Python 对象的所有权，被回收后 QML 里会读成 undefined；component 被回收时
    # 它创建的 QML 对象也会被一并销毁（findChild 会报 object already deleted）。
    holder.extend([engine, component, acquisition])
    return root


def test_start_button_enabled_in_normal_mode(qapp) -> None:
    """正常模式下"开始采集"不能被禁用（此前只允许 test 模式）。"""
    holder: list = []
    root = _build_config_commands(qapp, holder, mode="normal", running=False)

    button = root.findChild(QObject, "foupStartButton")
    assert button is not None, "未找到开始采集按钮"
    assert button.property("enabled") is True


def test_stop_button_label_mentions_download_in_normal_mode(qapp) -> None:
    holder: list = []
    root = _build_config_commands(qapp, holder, mode="normal", running=True)

    start = root.findChild(QObject, "foupStartButton")
    stop = root.findChild(QObject, "foupStopButton")
    assert start is not None and stop is not None
    assert start.property("enabled") is False, "采集进行中不能重复开始"
    assert "下载" in str(stop.property("text"))
