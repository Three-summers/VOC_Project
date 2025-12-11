"""FOUP 数据采集控制器

负责 TCP 连接、数据采集与分发。
"""

from __future__ import annotations

import struct
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer

from voc_app.gui.channel_config import (
    ServerType,
    ServerTypeRegistry,
    ChannelConfig,
    ChannelConfigManager,
)
from voc_app.gui.socket_client import SocketCommunicator, Client


class FoupAcquisitionController(QObject):
    """管理 FOUP 采集通道的 TCP 连接与数据分发。"""

    _COMMAND_SETS: Dict[ServerType, Dict[str, str]] = {
        ServerType.NOISE: {
            "sample_normal": "Noise_Hmulity_sample_type_normal",
            "sample_test": "Noise_Hmulity_sample_type_test",
            "start": "Noise_Hmulity_data_coll_ctrl_start",
            "stop": "Noise_Hmulity_data_coll_ctrl_stop",
        },
        ServerType.VOC: {
            "sample_normal": "voc_sample_type_normal",
            "sample_test": "voc_sample_type_test",
            "start": "voc_data_coll_ctrl_start",
            "stop": "voc_data_coll_ctrl_stop",
        },
    }
    _DEFAULT_COMMANDS: Dict[str, str] = {
        "sample_normal": "voc_sample_type_normal",
        "sample_test": "voc_sample_type_test",
        "start": "voc_data_coll_ctrl_start",
        "stop": "voc_data_coll_ctrl_stop",
    }

    # Signals
    runningChanged = Signal()
    statusMessageChanged = Signal()
    lastValueChanged = Signal()
    channelValuesChanged = Signal()
    errorOccurred = Signal(str)
    channelCountChanged = Signal()
    hostChanged = Signal()
    channelConfigChanged = Signal(int)
    serverTypeChanged = Signal()
    serverVersionChanged = Signal()
    operationModeChanged = Signal()
    normalModeRemotePathChanged = Signal()
    dataPointReceived = Signal(float, list)
    _serverTypeDetected = Signal(int)

    def __init__(
        self,
        series_models: Iterable[QObject],
        # host: str = "192.168.1.53",
        host: str = "127.0.0.1",
        port: int = 65432,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._series_models: List[QObject] = [m for m in series_models if m is not None]
        self._primary_series: QObject | None = self._series_models[0] if self._series_models else None

        # 线程安全锁
        self._lock = threading.Lock()

        # 受保护的共享状态
        self._host: str = host.strip() if host else "192.168.1.8"
        self._port: int = int(port)
        self._running: bool = False
        self._status: str = "未启动"
        self._last_value: float | None = None
        self._channel_values: List[float] = []
        self._channel_count: int = 0
        self._server_type: ServerType = ServerType.UNKNOWN
        self._server_version: str = ""
        self._operation_mode: str = "test"
        self._normal_mode_remote_path: str = "Log"

        # 线程管理
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._communicator: SocketCommunicator | None = None
        self._sample_index: int = 0
        self._last_timestamp_ms: float = 0.0
        self._server_type_detected: bool = False
        self._detected_channel_count: int = 0

        self._config_manager = ChannelConfigManager()

        self.dataPointReceived.connect(self._append_point_to_model)
        self._serverTypeDetected.connect(self._on_server_type_detected)

    # ---- Thread-safe property accessors ----

    @Property(bool, notify=runningChanged)
    def running(self) -> bool:
        with self._lock:
            return self._running

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        with self._lock:
            return self._status

    @Property(QObject, constant=True)
    def seriesModel(self) -> QObject | None:
        return self._primary_series

    @Property(float, notify=lastValueChanged)
    def lastValue(self) -> float:
        with self._lock:
            return float(self._last_value) if self._last_value is not None else float("nan")

    @Property(int, notify=channelCountChanged)
    def channelCount(self) -> int:
        with self._lock:
            return self._channel_count

    @Property(str, notify=hostChanged)
    def host(self) -> str:
        with self._lock:
            return self._host

    @host.setter
    def host(self, value: str) -> None:
        new_host = value.strip() if value else ""
        if not new_host:
            self.errorOccurred.emit("无效的 IP 地址")
            return
        emit_status = False
        emit_host = False
        with self._lock:
            if self._running:
                self._status = "采集中，停止后可修改 IP"
                emit_status = True
            elif new_host != self._host:
                self._host = new_host
                emit_host = True
        if emit_status:
            self.statusMessageChanged.emit()
        if emit_host:
            self.hostChanged.emit()

    @Property(str, notify=operationModeChanged)
    def operationMode(self) -> str:
        with self._lock:
            return self._operation_mode

    @operationMode.setter
    def operationMode(self, value: str) -> None:
        new_mode = (value or "test").strip().lower()
        if new_mode not in {"normal", "test"}:
            new_mode = "test"
        changed = False
        with self._lock:
            if new_mode != self._operation_mode:
                self._operation_mode = new_mode
                changed = True
        if changed:
            self.operationModeChanged.emit()

    @Property(str, notify=normalModeRemotePathChanged)
    def normalModeRemotePath(self) -> str:
        with self._lock:
            return self._normal_mode_remote_path

    @normalModeRemotePath.setter
    def normalModeRemotePath(self, value: str) -> None:
        path = value.strip() if value else "Log"
        changed = False
        with self._lock:
            if path != self._normal_mode_remote_path:
                self._normal_mode_remote_path = path
                changed = True
        if changed:
            self.normalModeRemotePathChanged.emit()

    @Property(str, notify=serverVersionChanged)
    def serverVersion(self) -> str:
        with self._lock:
            return self._server_version

    @Property(str, notify=serverTypeChanged)
    def serverType(self) -> str:
        with self._lock:
            return self._server_type.value

    @Property(str, notify=serverTypeChanged)
    def serverTypeDisplayName(self) -> str:
        with self._lock:
            preset = ServerTypeRegistry.get_preset(self._server_type)
            return preset.display_name

    # ---- Slots ----

    @Slot()
    def startAcquisition(self) -> None:
        emit_status = False
        with self._lock:
            if self._running or (self._worker and self._worker.is_alive()):
                return
            if not self._host:
                self._status = "请先配置采集 IP"
                emit_status = True
            elif self._operation_mode == "test" and not self._series_models:
                self._status = "无可用曲线"
                emit_status = True
            op_mode = self._operation_mode
        if emit_status:
            self.statusMessageChanged.emit()
            return

        if op_mode == "test":
            for model in self._series_models:
                try:
                    clear_fn = getattr(model, "clear", None)
                    if callable(clear_fn):
                        clear_fn()
                except Exception as exc:
                    print(f"[WARN] foup_acquisition: clear series failed: {exc!r}")
            self._sample_index = 0
            self._last_timestamp_ms = 0.0

        self._stop_event.clear()
        with self._lock:
            self._server_type_detected = False
            self._server_type = ServerType.UNKNOWN
            self._server_version = ""
            self._channel_count = 0
            self._detected_channel_count = 0

        target = self._run_normal_mode if op_mode == "normal" else self._run_test_mode
        self._set_status("准备下载日志" if op_mode == "normal" else "正在连接...")
        self._worker = threading.Thread(target=target, daemon=True)
        self._worker.start()

    @Slot()
    def stopAcquisition(self) -> None:
        self._stop_event.set()
        self._set_status("正在停止...")
        self._send_stop_command()
        QTimer.singleShot(500, self._cleanup)

    def _cleanup(self) -> None:
        """清理资源：关闭 socket 并等待线程结束"""
        self._close_socket()
        worker = self._worker
        if worker and worker.is_alive():
            worker.join(timeout=2.0)
        self._worker = None

    # ---- Internal implementation ----

    def _run_test_mode(self) -> None:
        try:
            with self._lock:
                host, port = self._host, self._port
            self._communicator = SocketCommunicator(host, port)
            self._set_running(True)
            self._set_status("采集中")
            self._perform_version_query()
            self._send_sample_type_command()
            start_cmd = self._select_command("start")
            if start_cmd:
                self._send_command(start_cmd)
            while not self._stop_event.is_set():
                message = self._recv_message()
                if message is None:
                    break
                self._handle_line(message)
        except Exception as exc:
            self.errorOccurred.emit(f"FOUP 采集异常: {exc}")
            self._set_status(f"异常: {exc}")
        finally:
            self._send_stop_command()
            self._close_socket()
            self._set_running(False)
            emit_status = False
            with self._lock:
                if not self._status.startswith("异常"):
                    self._status = "已停止"
                    emit_status = True
            if emit_status:
                self.statusMessageChanged.emit()
            self._stop_event.clear()

    def _run_normal_mode(self) -> None:
        try:
            with self._lock:
                host, port = self._host, self._port
            self._communicator = SocketCommunicator(host, port)
            self._set_running(True)
            self._set_status("查询版本...")
            self._perform_version_query()
            self._send_sample_type_command()
        except Exception as exc:
            self.errorOccurred.emit(f"FOUP 连接异常: {exc}")
            self._set_status(f"异常: {exc}")
        finally:
            self._close_socket()

        if self._stop_event.is_set():
            self._set_running(False)
            self._set_status("已停止")
            self._stop_event.clear()
            return

        try:
            self._set_status("正在下载日志...")
            saved_files = self._download_logs()
            if self._stop_event.is_set():
                self._set_status("已停止")
            else:
                self._set_status(f"下载完成: {len(saved_files)} 个文件")
        except Exception as exc:
            self.errorOccurred.emit(f"FOUP 下载异常: {exc}")
            self._set_status(f"异常: {exc}")
        finally:
            self._set_running(False)
            self._stop_event.clear()

    def _download_logs(self) -> List[str]:
        if self._stop_event.is_set():
            return []
        dest_root = Path(__file__).parent / "Log"
        dest_root.mkdir(parents=True, exist_ok=True)
        communicator: SocketCommunicator | None = None
        client: Client | None = None
        try:
            with self._lock:
                host, port = self._host, self._port
                remote_path = self._normal_mode_remote_path
            communicator = SocketCommunicator(host, port)
            client = Client(communicator)
            return client.get_file(remote_path, str(dest_root))
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

    def _perform_version_query(self) -> None:
        try:
            self._send_command("get_function_version_info")
        except Exception:
            return
        for _ in range(3):
            response = self._recv_message()
            if not response:
                break
            if response.strip().lower() == "ack":
                self._set_status("收到 ACK")
                continue
            detected_type, version = self._parse_version_response(response)
            if detected_type != ServerType.UNKNOWN or version:
                self._apply_server_identity(detected_type, version)
                break

    def _parse_version_response(self, response: str) -> tuple[ServerType, str]:
        cleaned = (response or "").strip()
        if not cleaned or not any(ch.isalpha() for ch in cleaned):
            return ServerType.UNKNOWN, ""
        parts = [part.strip() for part in cleaned.split(",") if part.strip()]
        type_token = parts[0] if parts else cleaned
        version = parts[1] if len(parts) > 1 else ""
        lower_token = type_token.lower()
        if "voc" in lower_token:
            return ServerType.VOC, version
        if "noise" in lower_token:
            return ServerType.NOISE, version
        return ServerType.UNKNOWN, version

    def _apply_server_identity(self, server_type: ServerType, version: str | None = None) -> None:
        emit_type = False
        emit_count = False
        emit_version = False
        preset_count = 0
        with self._lock:
            if server_type != ServerType.UNKNOWN and self._server_type != server_type:
                self._server_type = server_type
                preset = ServerTypeRegistry.get_preset(server_type)
                preset_count = preset.channel_count
                self._config_manager.set_server_type(server_type)
                if self._channel_count != preset_count:
                    self._channel_count = preset_count
                    emit_count = True
                emit_type = True
            if version is not None and version != self._server_version:
                self._server_version = version
                emit_version = True
        if emit_type:
            self._apply_preset_config(server_type, preset_count)
            self.serverTypeChanged.emit()
        if emit_count:
            self.channelCountChanged.emit()
        if emit_version:
            self.serverVersionChanged.emit()

    def _select_command(self, key: str) -> str | None:
        with self._lock:
            server_type = self._server_type
        commands = self._COMMAND_SETS.get(server_type)
        if not commands:
            commands = self._DEFAULT_COMMANDS
        return commands.get(key) or self._DEFAULT_COMMANDS.get(key)

    def _send_sample_type_command(self) -> None:
        with self._lock:
            op_mode = self._operation_mode
        cmd_key = "sample_normal" if op_mode == "normal" else "sample_test"
        cmd = self._select_command(cmd_key)
        if cmd:
            self._send_command(cmd)

    def _send_stop_command(self) -> None:
        if not self._communicator:
            return
        cmd = self._select_command("stop")
        if cmd:
            self._send_command(cmd)

    def _handle_line(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return

        if cleaned.lower() == "ack":
            self._set_status("收到 ACK")
            return

        parsed_type, version = self._parse_version_response(cleaned)
        if parsed_type != ServerType.UNKNOWN or version:
            self._apply_server_identity(parsed_type, version)
            if not all(ch in "0123456789.,-+ " for ch in cleaned):
                return

        values: List[float] = []
        if "," in cleaned:
            for token in cleaned.split(","):
                try:
                    values.append(float(token.strip()))
                except ValueError:
                    continue
        else:
            try:
                values.append(float(cleaned))
            except ValueError:
                return

        if not values:
            return

        detected_count = len(values)
        if self._detected_channel_count != detected_count:
            self._detected_channel_count = detected_count
            self._serverTypeDetected.emit(detected_count)

        emit_count = False
        with self._lock:
            if self._channel_count != detected_count:
                self._channel_count = detected_count
                emit_count = True
            self._channel_values = values.copy()
            self._last_value = values[0]

        if emit_count:
            self.channelCountChanged.emit()
        self.channelValuesChanged.emit()
        self.lastValueChanged.emit()

        self._sample_index += 1
        timestamp_ms = time.time() * 1000.0
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1.0
        self._last_timestamp_ms = timestamp_ms

        self.dataPointReceived.emit(timestamp_ms, values)

    def _on_server_type_detected(self, channel_count: int) -> None:
        new_type = ServerTypeRegistry.detect_by_channel_count(channel_count)
        emit_type = False
        with self._lock:
            if self._server_type != new_type:
                self._server_type = new_type
                self._config_manager.set_server_type(new_type)
                emit_type = True
        if emit_type:
            self._apply_preset_config(new_type, channel_count)
            self.serverTypeChanged.emit()
            print(f"[INFO] 检测到服务端类型: {new_type.value} (通道数: {channel_count})")
        else:
            self._apply_preset_config(new_type, channel_count)

    def _apply_preset_config(self, server_type: ServerType, channel_count: int) -> None:
        preset = ServerTypeRegistry.get_preset(server_type)
        self._config_manager.set_server_type(server_type)
        total = max(channel_count, preset.channel_count)
        for channel_idx in range(total):
            channel_preset = preset.get_channel_preset(channel_idx)
            config = ChannelConfig.from_preset(channel_preset)
            self._config_manager.set(channel_idx, config)
            self.channelConfigChanged.emit(channel_idx)

    def _append_point_to_model(self, x: float, y_values: list) -> None:
        try:
            for channel_idx, y_value in enumerate(y_values):
                if channel_idx < len(self._series_models):
                    model = self._series_models[channel_idx]
                    if model is not None:
                        model.append_point(x, y_value)  # type: ignore
        except Exception as exc:
            print(f"[ERROR] foup_acquisition: _append_point_to_model: {exc!r}")

    def _set_running(self, value: bool) -> None:
        changed = False
        with self._lock:
            if self._running != value:
                self._running = value
                changed = True
        if changed:
            self.runningChanged.emit()

    def _set_status(self, message: str) -> None:
        changed = False
        with self._lock:
            if self._status != message:
                self._status = message
                changed = True
        if changed:
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
            try:
                chunk = self._communicator.recv(remaining)
            except Exception as exc:
                print(f"[WARN] foup_acquisition: recv exception {exc}")
                return None
            if not chunk:
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _send_command(self, text: str) -> None:
        if not self._communicator:
            return
        try:
            payload = text.encode("utf-8")
            header = struct.pack(">I", len(payload))
            self._communicator.send(header + payload)
        except Exception as exc:
            print(f"FOUP: send_command error {exc}")

    # ---- Channel config slots ----

    @Slot(int, result="QVariant")
    def getChannelConfig(self, channel_idx: int) -> Dict[str, Any]:
        return self._config_manager.get(channel_idx).to_dict()

    @Slot(int, str)
    def setChannelTitle(self, channel_idx: int, title: str) -> None:
        self._config_manager.update(channel_idx, title=title)
        self.channelConfigChanged.emit(channel_idx)

    @Slot(int, float, float, float, float, float)
    def setChannelLimits(
        self,
        channel_idx: int,
        ooc_upper: float,
        ooc_lower: float,
        oos_upper: float,
        oos_lower: float,
        target: float,
    ) -> None:
        self._config_manager.update(
            channel_idx,
            ooc_upper=ooc_upper,
            ooc_lower=ooc_lower,
            oos_upper=oos_upper,
            oos_lower=oos_lower,
            target=target,
        )
        self.channelConfigChanged.emit(channel_idx)

    @Slot(int, "QVariant")
    def setChannelConfig(self, channel_idx: int, config_dict: Dict[str, Any]) -> None:
        config = ChannelConfig.from_dict(config_dict)
        self._config_manager.set(channel_idx, config)
        self.channelConfigChanged.emit(channel_idx)

    @Slot(int, result=str)
    def getChannelTitle(self, channel_idx: int) -> str:
        return self._config_manager.get(channel_idx).title

    @Slot(int, result=float)
    def getOocUpper(self, channel_idx: int) -> float:
        return self._config_manager.get(channel_idx).ooc_upper

    @Slot(int, result=float)
    def getOocLower(self, channel_idx: int) -> float:
        return self._config_manager.get(channel_idx).ooc_lower

    @Slot(int, result=float)
    def getOosUpper(self, channel_idx: int) -> float:
        return self._config_manager.get(channel_idx).oos_upper

    @Slot(int, result=float)
    def getOosLower(self, channel_idx: int) -> float:
        return self._config_manager.get(channel_idx).oos_lower

    @Slot(int, result=float)
    def getTarget(self, channel_idx: int) -> float:
        return self._config_manager.get(channel_idx).target

    @Slot(int, result=str)
    def getUnit(self, channel_idx: int) -> str:
        return self._config_manager.get(channel_idx).unit

    @Slot(int, str)
    def setChannelUnit(self, channel_idx: int, unit: str) -> None:
        self._config_manager.update(channel_idx, unit=unit)
        self.channelConfigChanged.emit(channel_idx)

    @Slot(int, result=float)
    def getChannelValue(self, channel_idx: int) -> float:
        with self._lock:
            if 0 <= channel_idx < len(self._channel_values):
                return self._channel_values[channel_idx]
        return float("nan")

    @Slot(int, result=bool)
    def getShowOocUpper(self, channel_idx: int) -> bool:
        return self._config_manager.get(channel_idx).show_ooc_upper

    @Slot(int, result=bool)
    def getShowOocLower(self, channel_idx: int) -> bool:
        return self._config_manager.get(channel_idx).show_ooc_lower

    @Slot(int, result=bool)
    def getShowOosUpper(self, channel_idx: int) -> bool:
        return self._config_manager.get(channel_idx).show_oos_upper

    @Slot(int, result=bool)
    def getShowOosLower(self, channel_idx: int) -> bool:
        return self._config_manager.get(channel_idx).show_oos_lower

    @Slot(int, result=bool)
    def getShowTarget(self, channel_idx: int) -> bool:
        return self._config_manager.get(channel_idx).show_target

    @Slot(int, bool, bool, bool, bool, bool)
    def setShowLimits(
        self,
        channel_idx: int,
        show_ooc_upper: bool,
        show_ooc_lower: bool,
        show_oos_upper: bool,
        show_oos_lower: bool,
        show_target: bool,
    ) -> None:
        self._config_manager.update(
            channel_idx,
            show_ooc_upper=show_ooc_upper,
            show_ooc_lower=show_ooc_lower,
            show_oos_upper=show_oos_upper,
            show_oos_lower=show_oos_lower,
            show_target=show_target,
        )
        self.channelConfigChanged.emit(channel_idx)
