import struct
import threading
from functools import partial
from typing import Iterable, List

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer

from voc_app.gui.socket_client import SocketCommunicator


class FoupAcquisitionController(QObject):
    """管理 FOUP 采集通道的 TCP 连接与数据分发。

    约定：采集服务器通过 127.0.0.1:65432 提供简单文本流，一次发送一个浮点字符串
    （例如 "10.1"，可选换行/空格分隔）。本控制器读取前一个可解析值并使用样本序号
    作为 X 轴，将数据推送到 SeriesTableModel。"""

    runningChanged = Signal()
    statusMessageChanged = Signal()
    lastValueChanged = Signal()
    errorOccurred = Signal(str)
    # 新增信号：用于跨线程传递数据点到主线程
    dataPointReceived = Signal(float, float)  # x, y

    def __init__(
        self,
        series_models: Iterable[QObject],
        host: str = "192.168.1.8",
        # host: str = "127.0.0.1",
        port: int = 65432,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._series_models = [model for model in series_models if model is not None]
        self._primary_series = self._series_models[0] if self._series_models else None
        self._host = host
        self._port = int(port)
        self._running = False
        self._status = "未启动"
        self._last_value: float | None = None
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._communicator: SocketCommunicator | None = None
        self._sample_index = 0

        # 连接信号到槽，确保跨线程调用安全
        self.dataPointReceived.connect(self._append_point_to_model)

    # ---- 公共属性 ----

    @Property(bool, notify=runningChanged)
    def running(self) -> bool:
        return self._running

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status

    @Property(QObject, constant=True)
    def seriesModel(self) -> QObject | None:
        return self._primary_series

    @Property(float, notify=lastValueChanged)
    def lastValue(self) -> float:
        return float(self._last_value) if self._last_value is not None else float("nan")

    # ---- 槽函数 ----

    @Slot()
    def startAcquisition(self) -> None:
        if self._running or (self._worker and self._worker.is_alive()):
            return
        if not self._series_models:
            self._set_status("无可用曲线")
            return
        for model in self._series_models:
            try:
                clear_fn = getattr(model, "clear", None)
                if callable(clear_fn):
                    clear_fn()
            except Exception as exc:
                print(f"[WARN] foup_acquisition: clear series failed: {exc!r}")
        self._sample_index = 0
        self._stop_event.clear()
        self._set_status("正在连接...")
        self._worker = threading.Thread(target=self._run_loop, daemon=True)
        self._worker.start()

    @Slot()
    def stopAcquisition(self) -> None:
        self._stop_event.set()
        self._set_status("正在停止...")
        # self._send_command("power off")
        self._send_command("voc_data_coll_ctrl_stop")
        self._close_socket()

    # ---- 内部实现 ----

    def _run_loop(self) -> None:
        try:
            self._communicator = SocketCommunicator(self._host, self._port)
            self._set_running(True)
            self._set_status("采集中")
            # self._send_command("power on")
            self._send_command("voc_data_coll_ctrl_start")
            while not self._stop_event.is_set():
                message = self._recv_message()
                if message is None:
                    break
                self._handle_line(message)
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(f"FOUP 采集异常: {exc}")
            self._set_status(f"异常: {exc}")
        finally:
            self._close_socket()
            self._set_running(False)
            if not self._status.startswith("异常"):
                self._set_status("已停止")
            self._stop_event.clear()

    def _handle_line(self, text: str) -> None:
        cleaned = text.strip().replace(",", " ")
        if not cleaned:
            return
        token = cleaned.split()[0]
        try:
            value = float(token)
        except ValueError:
            return
        self._last_value = value
        self.lastValueChanged.emit()
        self._sample_index += 1
        x_value = float(self._sample_index)

        # 使用信号机制安全地跨线程传递数据
        self.dataPointReceived.emit(x_value, value)

    def _append_point_to_model(self, x: float, y: float) -> None:
        try:
            model = self._series_models[0]
            model.append_point(x, y)
        except Exception as exc:
            print(f"[ERROR] foup_acquisition: Exception in _append_point_to_model(): {exc!r}")

    def _set_running(self, value: bool) -> None:
        if self._running != value:
            self._running = value
            self.runningChanged.emit()

    def _set_status(self, message: str) -> None:
        if self._status != message:
            self._status = message
            self.statusMessageChanged.emit()

    def _close_socket(self) -> None:
        comm = self._communicator
        self._communicator = None
        if comm is None:
            return
        try:
            comm.close()
        except Exception:
            pass

    def _recv_message(self) -> str | None:
        if not self._communicator:
            return None
        header = self._recv_exact(4)
        if not header:
            return None
        (length,) = struct.unpack(">I", header)
        if length == 0:
            return ""
        payload = self._recv_exact(length)
        if payload is None:
            return None
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def _recv_exact(self, size: int) -> bytes | None:
        if not self._communicator:
            return None
        chunks: List[bytes] = []
        remaining = size
        while remaining > 0:
            chunk = self._communicator.recv(remaining)
            if not chunk:
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _post(self, fn) -> None:
        QTimer.singleShot(0, fn)

    def _send_command(self, text: str) -> None:
        if not self._communicator:
            return
        try:
            payload = text.encode("utf-8")
            header = struct.pack(">I", len(payload))
            # self._communicator.send(header + payload + b"\n")
            self._communicator.send(header + payload)
        except Exception as exc:
            print(f"FOUP: send_command error {exc}")
