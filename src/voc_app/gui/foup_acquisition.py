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
    PrefixRegistry,
    DEFAULT_PREFIX_BY_CHANNEL,
    ChannelConfig,
    ChannelConfigManager,
)
from voc_app.gui.spectrum_model import SpectrumDataModel, SpectrumSimulator
from voc_app.gui.socket_client import SocketCommunicator, Client
from voc_app.logging_config import get_logger

logger = get_logger(__name__)


class FoupAcquisitionController(QObject):
    """管理 FOUP 采集通道的 TCP 连接与数据分发。

    命令动态生成规则：{prefix}_{action}
    - sample_test: {prefix}_sample_type_test
    - sample_normal: {prefix}_sample_type_normal
    - start: {prefix}_data_coll_ctrl_start
    - stop: {prefix}_data_coll_ctrl_stop
    """

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
    spectrumFrameReceived = Signal(list)
    _channelCountDetected = Signal(int)

    def __init__(
        self,
        series_models: Iterable[QObject],
        host: str = "192.168.1.53",
        # host: str = "127.0.0.1",
        port: int = 65432,
        spectrum_model: SpectrumDataModel | None = None,
        spectrum_simulator: SpectrumSimulator | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._series_models: List[QObject] = [m for m in series_models if m is not None]
        self._primary_series: QObject | None = (
            self._series_models[0] if self._series_models else None
        )
        self._spectrum_model = spectrum_model
        self._spectrum_simulator = spectrum_simulator
        self._external_spectrum_seen = False

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
        self._server_version: str = ""
        self._command_prefix: str = ""  # 从服务器响应解析的命令前缀（大写）
        self._operation_mode: str = "test"
        self._normal_mode_remote_path: str = "Log"

        # 线程管理
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._communicator: SocketCommunicator | None = None
        self._sample_index: int = 0
        self._last_timestamp_ms: float = 0.0
        self._detected_channel_count: int = 0

        self._config_manager = ChannelConfigManager()

        self.dataPointReceived.connect(self._append_point_to_model)
        self.spectrumFrameReceived.connect(self._on_spectrum_frame_received)
        self._channelCountDetected.connect(self._on_channel_count_detected)

    @staticmethod
    def _is_spectrum_prefix(prefix: str) -> bool:
        return prefix.upper() in {"SPEC"}

    @staticmethod
    def _normalize_spectrum_bins(values: list[float]) -> list[float]:
        """将频谱数据归一化到 0.0~1.0（适配 uint32 等大整数输入）。"""
        if not values:
            return []
        max_v = max(values)
        if max_v <= 0:
            return [0.0 for _ in values]
        return [max(0.0, float(v) / float(max_v)) for v in values]

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
            return (
                float(self._last_value)
                if self._last_value is not None
                else float("nan")
            )

    @Property(int, notify=channelCountChanged)
    def channelCount(self) -> int:
        with self._lock:
            return self._channel_count

    @Property(str, notify=hostChanged)
    def host(self) -> str:  # pyright: ignore
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
    def operationMode(self) -> str:  # pyright: ignore
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
    def normalModeRemotePath(self) -> str:  # pyright: ignore
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
        """返回服务器类型（大写前缀）"""
        with self._lock:
            return self._command_prefix

    @Property(str, notify=serverTypeChanged)
    def serverTypeDisplayName(self) -> str:
        with self._lock:
            prefix = self._command_prefix
        if not prefix:
            return "未知类型"
        preset = PrefixRegistry.get_preset(prefix)
        # 如果是默认预设（未注册的前缀），直接显示前缀名
        if preset.prefix == "UNKNOWN":
            return prefix
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
                    logger.warning(f"clear series failed: {exc!r}")
            self._sample_index = 0
            self._last_timestamp_ms = 0.0

        self._stop_event.clear()
        with self._lock:
            self._server_version = ""
            self._command_prefix = ""
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
            try:
                self.errorOccurred.emit(f"FOUP 采集异常: {exc}")
            except RuntimeError:
                pass
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
                try:
                    self.statusMessageChanged.emit()
                except RuntimeError:
                    pass
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
            try:
                self.errorOccurred.emit(f"FOUP 连接异常: {exc}")
            except RuntimeError:
                pass
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
            try:
                self.errorOccurred.emit(f"FOUP 下载异常: {exc}")
            except RuntimeError:
                pass
            self._set_status(f"异常: {exc}")
        finally:
            self._set_running(False)
            self._stop_event.clear()

    def _download_logs(self) -> List[str]:
        if self._stop_event.is_set():
            return []
        dest_root = Path(__file__).parent / "Log"
        dest_root.mkdir(parents=True, exist_ok=True)

        with self._lock:
            host, port = self._host, self._port
            remote_path = self._normal_mode_remote_path

        communicator: SocketCommunicator | None = None
        try:
            communicator = SocketCommunicator(host, port)
            client = Client(communicator)
            return client.get_file(remote_path, str(dest_root))
        except Exception as exc:
            logger.error(f"下载日志失败: {exc}")
            raise
        finally:
            # 确保 communicator 被关闭（无论 client 是否创建成功）
            if communicator is not None:
                try:
                    communicator.close()
                except Exception as e:
                    logger.debug(f"关闭 communicator 时异常: {e}")

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
            version, prefix = self._parse_version_response(response)
            if version or prefix:
                self._apply_server_identity(version, prefix)
                break

    def _parse_version_response(self, response: str) -> tuple[str, str]:
        """解析版本响应，返回 (version, prefix)，prefix 统一大写"""
        cleaned = (response or "").strip()
        if not cleaned or not any(ch.isalpha() for ch in cleaned):
            return "", ""
        parts = [part.strip() for part in cleaned.split(",") if part.strip()]
        type_token = parts[0] if parts else cleaned
        version = parts[1] if len(parts) > 1 else ""
        # prefix 统一转大写
        prefix = type_token.upper()
        return version, prefix

    def _apply_server_identity(
        self, version: str | None = None, prefix: str | None = None
    ) -> None:
        emit_type = False
        emit_version = False
        with self._lock:
            if prefix and prefix != self._command_prefix:
                self._command_prefix = prefix
                emit_type = True
            if version is not None and version != self._server_version:
                self._server_version = version
                emit_version = True
        # 配置初始化延迟到通道数确定时，见 _init_config_if_ready
        self._init_config_if_ready()
        if emit_type:
            self.serverTypeChanged.emit()
        if emit_version:
            self.serverVersionChanged.emit()

    def _init_config_if_ready(self) -> None:
        """当 prefix 和 channel_count 都确定时，初始化或加载配置"""
        with self._lock:
            prefix = self._command_prefix
            channel_count = self._channel_count
        if not prefix or channel_count <= 0:
            return
        # 只有当配置管理器当前 prefix 不同时才切换
        if self._config_manager.get_prefix() != prefix:
            self._config_manager.set_prefix(prefix, channel_count)

    def _on_spectrum_frame_received(self, values: list) -> None:
        """将频谱帧转发给 SpectrumDataModel（在 Qt 主线程执行）。"""
        model = self._spectrum_model
        if model is None:
            return
        try:
            model.updateSpectrum(values)  # type: ignore[arg-type]
        except Exception as exc:
            logger.warning(f"updateSpectrum failed: {exc!r}")
            return

        if self._external_spectrum_seen:
            return
        self._external_spectrum_seen = True
        simulator = self._spectrum_simulator
        if simulator is None:
            return
        try:
            if getattr(simulator, "running", False):
                simulator.stop()
        except Exception as exc:
            logger.debug(f"stop spectrum simulator failed: {exc!r}")

    def _select_command(self, key: str) -> str:
        """动态生成命令: {prefix}_{action}

        优先级: 服务器返回前缀 > 配置文件保存前缀 > 通道数默认前缀
        """
        with self._lock:
            prefix = self._command_prefix
            channel_count = self._channel_count
        if not prefix:
            prefix = self._config_manager.get_prefix()
        if not prefix:
            prefix = DEFAULT_PREFIX_BY_CHANNEL.get(channel_count, "VOC")
        actions = {
            "sample_test": "sample_type_test",
            "sample_normal": "sample_type_normal",
            "start": "data_coll_ctrl_start",
            "stop": "data_coll_ctrl_stop",
        }
        return f"{prefix}_{actions.get(key, key)}"

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

        # 频谱数据（每包带 prefix）：Noise_Spectrum,<float>,<float>...（256 点）
        # 注意：频谱前缀不应覆盖命令前缀（serverType），避免影响 FOUP 曲线与命令生成。
        if "," in cleaned and any(ch.isalpha() for ch in cleaned):
            parts = [part.strip() for part in cleaned.split(",")]
            if parts and parts[0] and self._is_spectrum_prefix(parts[0]):
                spectrum_values: List[float] = []
                for token in parts[1:]:
                    if not token:
                        continue
                    try:
                        spectrum_values.append(float(token))
                    except ValueError:
                        spectrum_values = []
                        break
                if spectrum_values:
                    # 兼容：SPEC,<timestamp>,<256 bins...>
                    bins = spectrum_values
                    if len(bins) == 257 and bins[0] > 1_000_000:
                        bins = bins[1:]

                    # 频谱图组件期望 0.0~1.0；如果输入是 uint32 等大数，做每帧归一化避免爆表。
                    if bins and (max(bins) > 1.0 or min(bins) < 0.0):
                        bins = self._normalize_spectrum_bins(bins)

                    self.spectrumFrameReceived.emit(bins)
                return

        version, prefix = self._parse_version_response(cleaned)
        if version or prefix:
            self._apply_server_identity(version, prefix)
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
            self._channelCountDetected.emit(detected_count)

        emit_count = False
        with self._lock:
            if self._channel_count != detected_count:
                self._channel_count = detected_count
                emit_count = True
            self._channel_values = values.copy()
            self._last_value = values[0]

        if emit_count:
            self.channelCountChanged.emit()
            self._init_config_if_ready()
        self.channelValuesChanged.emit()
        self.lastValueChanged.emit()

        self._sample_index += 1
        timestamp_ms = time.time() * 1000.0
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1.0
        self._last_timestamp_ms = timestamp_ms

        self.dataPointReceived.emit(timestamp_ms, values)

    def _on_channel_count_detected(self, channel_count: int) -> None:
        """当检测到通道数时，如果还没有 prefix，则使用默认前缀"""
        with self._lock:
            has_prefix = bool(self._command_prefix)
        if not has_prefix:
            default_prefix = PrefixRegistry.get_default_prefix(channel_count)
            self._apply_server_identity(prefix=default_prefix)
            logger.info(f"使用默认前缀: {default_prefix} (通道数: {channel_count})")

    def _append_point_to_model(self, x: float, y_values: list) -> None:
        try:
            for channel_idx, y_value in enumerate(y_values):
                if channel_idx < len(self._series_models):
                    model = self._series_models[channel_idx]
                    if model is not None:
                        model.append_point(x, y_value)  # type: ignore
        except Exception as exc:
            logger.error(f"_append_point_to_model: {exc!r}")

    def _set_running(self, value: bool) -> None:
        changed = False
        with self._lock:
            if self._running != value:
                self._running = value
                changed = True
        if changed:
            try:
                self.runningChanged.emit()
            except RuntimeError:
                # 对象已被删除，忽略
                pass

    def _set_status(self, message: str) -> None:
        changed = False
        with self._lock:
            if self._status != message:
                self._status = message
                changed = True
        if changed:
            try:
                self.statusMessageChanged.emit()
            except RuntimeError:
                # 对象已被删除，忽略
                pass

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
        """
        接收 size 字节的数据
        """
        if not self._communicator:
            return None
        chunks: List[bytes] = []
        remaining = size
        while remaining > 0:
            try:
                chunk = self._communicator.recv(remaining)
            except Exception as exc:
                logger.warning(f"recv exception: {exc}")
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
            logger.error(f"send_command error: {exc}")

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
