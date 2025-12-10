import json
import struct
import threading
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Iterable, List, Dict, Any
import time

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer

from voc_app.gui.socket_client import SocketCommunicator, Client


class ServerType(Enum):
    """服务端类型枚举"""

    UNKNOWN = "unknown"
    VOC = "voc"  # 1 个点
    NOISE = "noise"  # 3 个点
    # 未来可扩展更多类型
    # TEMPERATURE = "temperature"
    # PRESSURE = "pressure"


@dataclass
class ChannelPreset:
    """单个通道的预设配置"""

    title: str
    unit: str  # Y轴单位，如 ppb, dB, ℃, %
    ooc_upper: float
    ooc_lower: float
    oos_upper: float
    oos_lower: float
    target: float
    show_ooc_upper: bool = True  # 是否显示OOC上界
    show_ooc_lower: bool = True  # 是否显示OOC下界
    show_oos_upper: bool = True  # 是否显示OOS上界
    show_oos_lower: bool = True  # 是否显示OOS下界
    show_target: bool = True  # 是否显示Target线


@dataclass
class ServerTypePreset:
    """服务端类型的预设配置，包含所有通道的默认值"""

    server_type: ServerType
    display_name: str
    channel_count: int
    channels: List[ChannelPreset]

    def get_channel_preset(self, channel_idx: int) -> ChannelPreset:
        """获取指定通道的预设，越界时返回最后一个通道的配置"""
        if channel_idx < len(self.channels):
            return self.channels[channel_idx]
        return (
            self.channels[-1]
            if self.channels
            else ChannelPreset(
                title=f"通道 {channel_idx + 1}",
                unit="",
                ooc_upper=80.0,
                ooc_lower=20.0,
                oos_upper=90.0,
                oos_lower=10.0,
                target=50.0,
                show_ooc_upper=True,
                show_ooc_lower=True,
                show_oos_upper=True,
                show_oos_lower=True,
                show_target=True,
            )
        )


class ServerTypeRegistry:
    """服务端类型注册表，管理所有预设配置"""

    # 预设配置定义
    _PRESETS: Dict[ServerType, ServerTypePreset] = {
        ServerType.VOC: ServerTypePreset(
            server_type=ServerType.VOC,
            display_name="VOC 监测",
            channel_count=1,
            channels=[
                ChannelPreset(
                    title="VOC",
                    unit="ppb",
                    ooc_upper=3000.0,
                    ooc_lower=0.0,
                    oos_upper=5000.0,
                    oos_lower=0.0,
                    target=1000.0,
                    show_ooc_upper=True,
                    show_ooc_lower=False,
                    show_oos_upper=True,
                    show_oos_lower=False,
                    show_target=True,
                ),
            ],
        ),
        ServerType.NOISE: ServerTypePreset(
            server_type=ServerType.NOISE,
            display_name="Noise 监测",
            channel_count=3,
            channels=[
                ChannelPreset(
                    title="Noise CH1",
                    unit="dB",
                    ooc_upper=70.0,
                    ooc_lower=70.0,
                    oos_upper=80.0,
                    oos_lower=80.0,
                    target=60.0,
                    show_ooc_upper=True,
                    show_ooc_lower=False,
                    show_oos_upper=True,
                    show_oos_lower=False,
                    show_target=True,
                ),
                ChannelPreset(
                    title="Temperature",
                    unit="℃",
                    ooc_upper=25.0,
                    ooc_lower=15.0,
                    oos_upper=30.0,
                    oos_lower=10.0,
                    target=20.0,
                    show_ooc_upper=True,
                    show_ooc_lower=True,
                    show_oos_upper=True,
                    show_oos_lower=True,
                    show_target=True,
                ),
                ChannelPreset(
                    title="Humidity",
                    unit="%",
                    ooc_upper=50.0,
                    ooc_lower=30.0,
                    oos_upper=60.0,
                    oos_lower=20.0,
                    target=40.0,
                    show_ooc_upper=True,
                    show_ooc_lower=True,
                    show_oos_upper=True,
                    show_oos_lower=True,
                    show_target=True,
                ),
            ],
        ),
        ServerType.UNKNOWN: ServerTypePreset(
            server_type=ServerType.UNKNOWN,
            display_name="未知类型",
            channel_count=1,
            channels=[
                ChannelPreset(
                    title="通道 1",
                    unit="",
                    ooc_upper=80.0,
                    ooc_lower=20.0,
                    oos_upper=90.0,
                    oos_lower=10.0,
                    target=50.0,
                    show_ooc_upper=True,
                    show_ooc_lower=True,
                    show_oos_upper=True,
                    show_oos_lower=True,
                    show_target=True,
                ),
            ],
        ),
    }

    # 通道数到服务端类型的映射（当前的检测策略）,考虑删除，完全从服务器响应检测
    _CHANNEL_COUNT_MAP: Dict[int, ServerType] = {
        1: ServerType.VOC,
        3: ServerType.NOISE,
    }

    @classmethod
    def get_preset(cls, server_type: ServerType) -> ServerTypePreset:
        """获取指定服务端类型的预设配置"""
        return cls._PRESETS.get(server_type, cls._PRESETS[ServerType.UNKNOWN])

    @classmethod
    def detect_by_channel_count(cls, channel_count: int) -> ServerType:
        """根据通道数检测服务端类型（当前策略）"""
        return cls._CHANNEL_COUNT_MAP.get(channel_count, ServerType.UNKNOWN)

    @classmethod
    def detect_by_server_response(cls, response: str) -> ServerType:
        """
        根据服务端响应检测类型（未来扩展）

        预留接口：未来服务端支持类型查询时，可以通过此方法解析响应
        例如服务端返回 "SERVER_TYPE:PID" 或 JSON 格式的类型信息
        """
        # 未来实现示例：
        # if response.startswith("SERVER_TYPE:"):
        #     type_str = response.split(":")[1].strip().lower()
        #     for st in ServerType:
        #         if st.value == type_str:
        #             return st
        return ServerType.UNKNOWN

    @classmethod
    def register_preset(cls, preset: ServerTypePreset) -> None:
        """注册新的服务端类型预设（支持运行时扩展）"""
        cls._PRESETS[preset.server_type] = preset

    @classmethod
    def register_channel_count_mapping(
        cls, channel_count: int, server_type: ServerType
    ) -> None:
        """注册通道数到服务端类型的映射"""
        cls._CHANNEL_COUNT_MAP[channel_count] = server_type


@dataclass
class ChannelConfig:
    """单个通道的配置数据"""

    title: str = ""
    unit: str = ""  # Y轴单位，如 ppb, dB, ℃, %
    ooc_upper: float = 80.0
    ooc_lower: float = 20.0
    oos_upper: float = 90.0
    oos_lower: float = 10.0
    target: float = 50.0
    show_ooc_upper: bool = True  # 是否显示OOC上界
    show_ooc_lower: bool = True  # 是否显示OOC下界
    show_oos_upper: bool = True  # 是否显示OOS上界
    show_oos_lower: bool = True  # 是否显示OOS下界
    show_target: bool = True  # 是否显示Target线

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChannelConfig":
        return cls(
            title=data.get("title", ""),
            unit=data.get("unit", ""),
            ooc_upper=float(data.get("ooc_upper", 80.0)),
            ooc_lower=float(data.get("ooc_lower", 20.0)),
            oos_upper=float(data.get("oos_upper", 90.0)),
            oos_lower=float(data.get("oos_lower", 10.0)),
            target=float(data.get("target", 50.0)),
            show_ooc_upper=bool(data.get("show_ooc_upper", True)),
            show_ooc_lower=bool(data.get("show_ooc_lower", True)),
            show_oos_upper=bool(data.get("show_oos_upper", True)),
            show_oos_lower=bool(data.get("show_oos_lower", True)),
            show_target=bool(data.get("show_target", True)),
        )

    @classmethod
    def from_preset(cls, preset: ChannelPreset) -> "ChannelConfig":
        """从预设创建配置"""
        return cls(
            title=preset.title,
            unit=preset.unit,
            ooc_upper=preset.ooc_upper,
            ooc_lower=preset.ooc_lower,
            oos_upper=preset.oos_upper,
            oos_lower=preset.oos_lower,
            target=preset.target,
            show_ooc_upper=preset.show_ooc_upper,
            show_ooc_lower=preset.show_ooc_lower,
            show_oos_upper=preset.show_oos_upper,
            show_oos_lower=preset.show_oos_lower,
            show_target=preset.show_target,
        )


class ChannelConfigManager:
    """管理所有通道配置的持久化

    配置键格式：{server_type}_{channel_idx}，例如 "pid_0", "noise_1"
    这样不同服务端类型的通道配置不会互相覆盖
    """

    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            config_path = Path(__file__).parent / "channel_config.json"
        self._config_path = config_path
        self._configs: Dict[str, ChannelConfig] = (
            {}
        )  # 键格式: "{server_type}_{channel_idx}"
        self._current_server_type: ServerType = ServerType.UNKNOWN
        self._load()

    def _make_key(self, channel_idx: int) -> str:
        """生成配置键"""
        return f"{self._current_server_type.value}_{channel_idx}"

    def set_server_type(self, server_type: ServerType) -> None:
        """设置当前服务端类型"""
        self._current_server_type = server_type

    def _load(self) -> None:
        """从 JSON 文件加载配置"""
        if not self._config_path.exists():
            return
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, value in data.items():
                try:
                    self._configs[key] = ChannelConfig.from_dict(value)
                except (ValueError, TypeError):
                    continue
        except Exception as e:
            print(f"[WARN] ChannelConfigManager: 加载配置失败: {e}")

    def save(self) -> None:
        """保存配置到 JSON 文件"""
        try:
            data = {k: v.to_dict() for k, v in self._configs.items()}
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] ChannelConfigManager: 保存配置失败: {e}")

    def get(self, channel_idx: int) -> ChannelConfig:
        """获取指定通道的配置，不存在则返回默认配置"""
        key = self._make_key(channel_idx)
        if key not in self._configs:
            self._configs[key] = ChannelConfig(title=f"FOUP 通道 {channel_idx + 1}")
        return self._configs[key]

    def set(self, channel_idx: int, config: ChannelConfig) -> None:
        """设置指定通道的配置并保存"""
        key = self._make_key(channel_idx)
        self._configs[key] = config
        self.save()

    def update(self, channel_idx: int, **kwargs) -> ChannelConfig:
        """更新指定通道的部分配置并保存"""
        config = self.get(channel_idx)
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        config_key = self._make_key(channel_idx)
        self._configs[config_key] = config
        self.save()
        return config


class FoupAcquisitionController(QObject):
    """管理 FOUP 采集通道的 TCP 连接与数据分发。

    约定：采集服务器通过 127.0.0.1:65432 提供简单文本流，一次发送一个浮点字符串
    （例如 "10.1"，可选换行/空格分隔）。本控制器读取前一个可解析值并使用毫秒时间戳
    作为 X 轴，将数据推送到 SeriesTableModel。

    服务端类型检测策略：
    - 当前：根据数据点数量自动检测（1点=PID, 3点=NOISE）
    - 未来：可通过 socket 查询服务端类型
    """

    # 命令集合定义，按类型拆分
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

    runningChanged = Signal()
    statusMessageChanged = Signal()
    lastValueChanged = Signal()
    channelValuesChanged = Signal()  # 各通道值变更信号
    errorOccurred = Signal(str)
    channelCountChanged = Signal()
    hostChanged = Signal()
    channelConfigChanged = Signal(int)  # 通道配置变更信号，参数为通道索引
    serverTypeChanged = Signal()  # 服务端类型变更信号
    serverVersionChanged = Signal()
    operationModeChanged = Signal()
    normalModeRemotePathChanged = Signal()
    # 新增信号：用于跨线程传递数据点到主线程（支持多通道）
    dataPointReceived = Signal(float, list)  # x, [y1, y2, y3, ...]
    # 内部信号：用于跨线程触发服务端类型检测
    _serverTypeDetected = Signal(int)  # channel_count

    def __init__(
        self,
        series_models: Iterable[QObject],
        # host: str = "192.168.1.8",
        host: str = "127.0.0.1",
        port: int = 65432,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._series_models = [model for model in series_models if model is not None]
        self._primary_series = self._series_models[0] if self._series_models else None
        # 默认 IP，防止传入空值
        self._host = host.strip() if host else "192.168.1.8"
        self._port = int(port)
        self._running = False
        self._status = "未启动"
        self._last_value: float | None = None
        self._channel_values: List[float] = []  # 各通道当前值
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._communicator: SocketCommunicator | None = None
        self._sample_index = 0
        self._last_timestamp_ms = 0.0
        self._channel_count = 0  # 初始为 0，表示未检测
        self._server_type: ServerType = ServerType.UNKNOWN
        self._server_version: str = ""
        self._operation_mode: str = "test"  # normal/test
        self._normal_mode_remote_path: str = "Log"  # normal 模式远端路径，默认 Log
        self._server_type_detected: bool = False
        self._detected_channel_count: int = 0  # 记录已检测到的通道数，用于动态调整

        # 通道配置管理器
        self._config_manager = ChannelConfigManager()

        # 连接信号到槽，确保跨线程调用安全
        self.dataPointReceived.connect(self._append_point_to_model)
        self._serverTypeDetected.connect(self._on_server_type_detected)

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

    @Property(int, notify=channelCountChanged)
    def channelCount(self) -> int:
        return self._channel_count

    @Property(str, notify=hostChanged)
    def host(self) -> str: # type: ignore
        return self._host

    @host.setter
    def host(self, value: str) -> None:
        """允许 QML 动态调整采集 IP，运行中禁止修改。"""
        new_host = value.strip() if value else ""
        if not new_host:
            self.errorOccurred.emit("无效的 IP 地址")
            return
        if self._running:
            self._set_status("采集中，停止后可修改 IP")
            return
        if new_host == self._host:
            return
        self._host = new_host
        self.hostChanged.emit()

    @Property(str, notify=operationModeChanged)
    def operationMode(self) -> str: # type: ignore
        """返回当前采集模式：normal/test"""
        return self._operation_mode

    @operationMode.setter
    def operationMode(self, value: str) -> None:
        new_mode = (value or "test").strip().lower()
        if new_mode not in {"normal", "test"}:
            new_mode = "test"
        if new_mode != self._operation_mode:
            self._operation_mode = new_mode
            self.operationModeChanged.emit()

    @Property(str, notify=normalModeRemotePathChanged)
    def normalModeRemotePath(self) -> str: # type: ignore
        """normal 模式下载的远端路径（默认 Log）"""
        return self._normal_mode_remote_path

    @normalModeRemotePath.setter
    def normalModeRemotePath(self, value: str) -> None:
        path = value.strip() if value else "Log"
        if path != self._normal_mode_remote_path:
            self._normal_mode_remote_path = path
            self.normalModeRemotePathChanged.emit()

    @Property(str, notify=serverVersionChanged)
    def serverVersion(self) -> str:
        """返回最近一次 get_function_version_info 的版本号"""
        return self._server_version

    @Property(str, notify=serverTypeChanged)
    def serverType(self) -> str:
        """返回当前检测到的服务端类型名称"""
        return self._server_type.value

    @Property(str, notify=serverTypeChanged)
    def serverTypeDisplayName(self) -> str:
        """返回当前服务端类型的显示名称"""
        preset = ServerTypeRegistry.get_preset(self._server_type)
        return preset.display_name

    # ---- 槽函数 ----

    @Slot()
    def startAcquisition(self) -> None:
        if self._running or (self._worker and self._worker.is_alive()):
            return
        if not self._host:
            self._set_status("请先配置采集 IP")
            return
        if self._operation_mode == "test" and not self._series_models:
            self._set_status("无可用曲线")
            return

        # 清空历史数据
        if self._operation_mode == "test":
            for model in self._series_models:
                try:
                    clear_fn = getattr(model, "clear", None)
                    # 检查 clear 方法是否存在并可调用
                    if callable(clear_fn):
                        clear_fn()
                except Exception as exc:
                    print(f"[WARN] foup_acquisition: clear series failed: {exc!r}")
            self._sample_index = 0
            self._last_timestamp_ms = 0.0

        self._stop_event.clear()
        self._server_type_detected = False
        self._server_type = ServerType.UNKNOWN
        self._server_version = ""
        self._channel_count = 0
        self._detected_channel_count = 0

        # 选择运行目标
        target = (
            self._run_normal_mode
            if self._operation_mode == "normal"
            else self._run_test_mode
        )
        self._set_status(
            "准备下载日志" if self._operation_mode == "normal" else "正在连接..."
        )
        self._worker = threading.Thread(target=target, daemon=True)
        self._worker.start()

    @Slot()
    def stopAcquisition(self) -> None:
        self._stop_event.set()
        self._set_status("正在停止...")
        self._send_stop_command()
        QTimer.singleShot(500, self._close_socket)

    # ---- 内部实现 ----

    def _run_test_mode(self) -> None:
        try:
            self._communicator = SocketCommunicator(self._host, self._port)
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
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(f"FOUP 采集异常: {exc}")
            self._set_status(f"异常: {exc}")
        finally:
            self._send_stop_command()
            self._close_socket()
            self._set_running(False)
            if not self._status.startswith("异常"):
                self._set_status("已停止")
            self._stop_event.clear()

    def _run_normal_mode(self) -> None:
        """normal 模式：查询版本并下载日志目录"""
        try:
            self._communicator = SocketCommunicator(self._host, self._port)
            self._set_running(True)
            self._set_status("查询版本...")
            self._perform_version_query()
            self._send_sample_type_command()
        except Exception as exc:  # noqa: BLE001
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
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(f"FOUP 下载异常: {exc}")
            self._set_status(f"异常: {exc}")
        finally:
            self._set_running(False)
            self._stop_event.clear()

    def _download_logs(self) -> List[str]:
        """使用单独连接下载远端目录到本地 Log"""
        if self._stop_event.is_set():
            return []
        dest_root = Path(__file__).parent / "Log"
        dest_root.mkdir(parents=True, exist_ok=True)
        communicator: SocketCommunicator | None = None
        client: Client | None = None
        try:
            communicator = SocketCommunicator(self._host, self._port)
            client = Client(communicator)
            return client.get_file(self._normal_mode_remote_path, str(dest_root))
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

    def _perform_version_query(self) -> None:
        """发送版本查询并根据响应设置类型/版本"""
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
        if not cleaned:
            return ServerType.UNKNOWN, ""
        if not any(ch.isalpha() for ch in cleaned):
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

    def _apply_server_identity(
        self, server_type: ServerType, version: str | None = None
    ) -> None:
        """根据版本响应更新服务端类型与版本"""
        if server_type != ServerType.UNKNOWN and self._server_type != server_type:
            self._server_type = server_type
            preset = ServerTypeRegistry.get_preset(server_type)
            self._config_manager.set_server_type(server_type)
            self._apply_preset_config(server_type, preset.channel_count)
            if self._channel_count != preset.channel_count:
                self._channel_count = preset.channel_count
                self.channelCountChanged.emit()
            self.serverTypeChanged.emit()
        if version is not None and version != self._server_version:
            self._server_version = version
            self.serverVersionChanged.emit()

    def _select_command(self, key: str) -> str | None:
        """按当前服务端类型返回对应命令"""
        commands = self._COMMAND_SETS.get(self._server_type)
        if not commands:
            commands = self._DEFAULT_COMMANDS
        return commands.get(key) or self._DEFAULT_COMMANDS.get(key)

    def _send_sample_type_command(self) -> None:
        """根据模式发送采样类型命令"""
        cmd_key = "sample_normal" if self._operation_mode == "normal" else "sample_test"
        cmd = self._select_command(cmd_key)
        if cmd:
            self._send_command(cmd)

    def _send_stop_command(self) -> None:
        """发送当前类型对应的停止命令"""
        if not self._communicator:
            return
        cmd = self._select_command("stop")
        if cmd:
            self._send_command(cmd)

    def _handle_line(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return

        lower_text = cleaned.lower()
        if lower_text == "ack":
            # 控制命令的简单应答
            self._set_status("收到 ACK")
            return

        parsed_type, version = self._parse_version_response(cleaned)
        if parsed_type != ServerType.UNKNOWN or version:
            self._apply_server_identity(parsed_type, version)
            # 非纯数字的版本行不再当作数据处理
            if not all(ch in "0123456789.,-+ " for ch in cleaned):
                return

        # 解析逗号分隔的数据
        values = []
        if "," in cleaned:
            # 多通道数据：12.1,123.4,65.1,75.2
            tokens = cleaned.split(",")
            for token in tokens:
                try:
                    value = float(token.strip())
                    values.append(value)
                except ValueError:
                    continue
        else:
            # 单通道数据：1.23（向后兼容）
            try:
                value = float(cleaned)
                values.append(value)
            except ValueError:
                return

        if not values:
            return

        # 通道数变化时，根据通道数检测/更新服务端类型与配置
        detected_count = len(values)
        if self._detected_channel_count != detected_count:
            self._detected_channel_count = detected_count
            # 使用信号在主线程中处理类型检测和配置应用
            self._serverTypeDetected.emit(detected_count)

        # 更新通道数量
        if self._channel_count != detected_count:
            self._channel_count = detected_count
            self.channelCountChanged.emit()

        # 更新各通道值
        self._channel_values = values.copy()
        self._last_value = values[0]
        self.channelValuesChanged.emit()
        self.lastValueChanged.emit()

        self._sample_index += 1
        timestamp_ms = time.time() * 1000.0
        # 避免同一毫秒内多次触发导致时间戳重复
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1.0
        self._last_timestamp_ms = timestamp_ms

        # 使用信号机制安全地跨线程传递数据（传递所有通道的值）
        self.dataPointReceived.emit(timestamp_ms, values)

    def _on_server_type_detected(self, channel_count: int) -> None:
        """
        处理服务端类型检测结果（在主线程中执行）

        当前策略：根据通道数检测服务端类型
        未来扩展：可以在连接时先查询服务端类型
        """
        # 根据通道数检测服务端类型
        new_type = ServerTypeRegistry.detect_by_channel_count(channel_count)

        if self._server_type != new_type:
            self._server_type = new_type
            # 更新配置管理器的服务端类型
            self._config_manager.set_server_type(new_type)
            # 应用预设配置到所有通道（使用实际通道数保证标题/单位同步）
            self._apply_preset_config(new_type, channel_count)
            self.serverTypeChanged.emit()
            print(
                f"[INFO] 检测到服务端类型: {new_type.value} (通道数: {channel_count})"
            )
        else:
            # 即便类型未变更，也要在通道数变化时刷新配置，保证标题/单位覆盖新通道
            self._apply_preset_config(new_type, channel_count)

    def _apply_preset_config(self, server_type: ServerType, channel_count: int) -> None:
        """应用预设配置到所有通道"""
        preset = ServerTypeRegistry.get_preset(server_type)
        # 设置配置管理器的服务端类型，确保配置键正确
        self._config_manager.set_server_type(server_type)

        # 以实际检测到的通道数为准，缺省时使用预设末尾作为默认
        total = max(channel_count, preset.channel_count)
        for channel_idx in range(total):
            channel_preset = preset.get_channel_preset(channel_idx)
            # 使用预设创建配置并保存
            config = ChannelConfig.from_preset(channel_preset)
            self._config_manager.set(channel_idx, config)
            # 通知 QML 配置已变更
            self.channelConfigChanged.emit(channel_idx)

    def _append_point_to_model(self, x: float, y_values: list) -> None:
        """将多通道数据添加到对应的series models中"""
        try:
            # 遍历所有接收到的值，添加到对应的series model
            for channel_idx, y_value in enumerate(y_values):
                if channel_idx < len(self._series_models):
                    model = self._series_models[channel_idx]
                    if model is not None:
                        model.append_point(x, y_value) # type: ignore
        except Exception as exc:
            print(
                f"[ERROR] foup_acquisition: Exception in _append_point_to_model(): {exc!r}"
            )

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
            try:
                chunk = self._communicator.recv(remaining)
            except Exception as exc:  # 包括 socket.timeout
                # 超时或收取异常时视为断开，返回 None
                print(f"[WARN] foup_acquisition: recv exception {exc}")
                return None
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
            # 停止阶段可能 socket 已关闭，避免抛出 Bad file descriptor
            print(f"FOUP: send_command error {exc}")

    # ---- 通道配置相关槽函数（供 QML 调用）----

    @Slot(int, result="QVariant") # type: ignore
    def getChannelConfig(self, channel_idx: int) -> Dict[str, Any]:
        """获取指定通道的配置，返回字典供 QML 使用"""
        config = self._config_manager.get(channel_idx)
        return config.to_dict()

    @Slot(int, str)
    def setChannelTitle(self, channel_idx: int, title: str) -> None:
        """设置指定通道的标题"""
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
        """设置指定通道的 OOC/OOS/Target 限制"""
        self._config_manager.update(
            channel_idx,
            ooc_upper=ooc_upper,
            ooc_lower=ooc_lower,
            oos_upper=oos_upper,
            oos_lower=oos_lower,
            target=target,
        )
        self.channelConfigChanged.emit(channel_idx)

    @Slot(int, "QVariant") # type: ignore
    def setChannelConfig(self, channel_idx: int, config_dict: Dict[str, Any]) -> None:
        """设置指定通道的完整配置"""
        config = ChannelConfig.from_dict(config_dict)
        self._config_manager.set(channel_idx, config)
        self.channelConfigChanged.emit(channel_idx)

    @Slot(int, result=str)
    def getChannelTitle(self, channel_idx: int) -> str:
        """获取指定通道的标题"""
        return self._config_manager.get(channel_idx).title

    @Slot(int, result=float)
    def getOocUpper(self, channel_idx: int) -> float:
        """获取指定通道的 OOC 上界"""
        return self._config_manager.get(channel_idx).ooc_upper

    @Slot(int, result=float)
    def getOocLower(self, channel_idx: int) -> float:
        """获取指定通道的 OOC 下界"""
        return self._config_manager.get(channel_idx).ooc_lower

    @Slot(int, result=float)
    def getOosUpper(self, channel_idx: int) -> float:
        """获取指定通道的 OOS 上界"""
        return self._config_manager.get(channel_idx).oos_upper

    @Slot(int, result=float)
    def getOosLower(self, channel_idx: int) -> float:
        """获取指定通道的 OOS 下界"""
        return self._config_manager.get(channel_idx).oos_lower

    @Slot(int, result=float)
    def getTarget(self, channel_idx: int) -> float:
        """获取指定通道的目标值"""
        return self._config_manager.get(channel_idx).target

    @Slot(int, result=str)
    def getUnit(self, channel_idx: int) -> str:
        """获取指定通道的Y轴单位"""
        return self._config_manager.get(channel_idx).unit

    @Slot(int, str)
    def setChannelUnit(self, channel_idx: int, unit: str) -> None:
        """设置指定通道的Y轴单位"""
        self._config_manager.update(channel_idx, unit=unit)
        self.channelConfigChanged.emit(channel_idx)

    @Slot(int, result=float)
    def getChannelValue(self, channel_idx: int) -> float:
        """获取指定通道的当前值"""
        if 0 <= channel_idx < len(self._channel_values):
            return self._channel_values[channel_idx]
        return float("nan")

    @Slot(int, result=bool)
    def getShowOocUpper(self, channel_idx: int) -> bool:
        """获取指定通道是否显示OOC上界"""
        return self._config_manager.get(channel_idx).show_ooc_upper

    @Slot(int, result=bool)
    def getShowOocLower(self, channel_idx: int) -> bool:
        """获取指定通道是否显示OOC下界"""
        return self._config_manager.get(channel_idx).show_ooc_lower

    @Slot(int, result=bool)
    def getShowOosUpper(self, channel_idx: int) -> bool:
        """获取指定通道是否显示OOS上界"""
        return self._config_manager.get(channel_idx).show_oos_upper

    @Slot(int, result=bool)
    def getShowOosLower(self, channel_idx: int) -> bool:
        """获取指定通道是否显示OOS下界"""
        return self._config_manager.get(channel_idx).show_oos_lower

    @Slot(int, result=bool)
    def getShowTarget(self, channel_idx: int) -> bool:
        """获取指定通道是否显示Target线"""
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
        """设置指定通道的限制线显示配置"""
        self._config_manager.update(
            channel_idx,
            show_ooc_upper=show_ooc_upper,
            show_ooc_lower=show_ooc_lower,
            show_oos_upper=show_oos_upper,
            show_oos_lower=show_oos_lower,
            show_target=show_target,
        )
        self.channelConfigChanged.emit(channel_idx)
