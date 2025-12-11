"""通道配置管理模块

负责服务端类型预设、通道配置的持久化管理。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List


class ServerType(Enum):
    """服务端类型枚举"""

    UNKNOWN = "unknown"
    VOC = "voc"
    NOISE = "noise"


@dataclass
class ChannelPreset:
    """单个通道的预设配置"""

    title: str
    unit: str
    ooc_upper: float
    ooc_lower: float
    oos_upper: float
    oos_lower: float
    target: float
    show_ooc_upper: bool = True
    show_ooc_lower: bool = True
    show_oos_upper: bool = True
    show_oos_lower: bool = True
    show_target: bool = True


@dataclass
class ServerTypePreset:
    """服务端类型的预设配置"""

    server_type: ServerType
    display_name: str
    channel_count: int
    channels: List[ChannelPreset]

    def get_channel_preset(self, channel_idx: int) -> ChannelPreset:
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
            )
        )


class ServerTypeRegistry:
    """服务端类型注册表"""

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
                    show_ooc_lower=False,
                    show_oos_lower=False,
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
                    show_ooc_lower=False,
                    show_oos_lower=False,
                ),
                ChannelPreset(
                    title="Temperature",
                    unit="℃",
                    ooc_upper=25.0,
                    ooc_lower=15.0,
                    oos_upper=30.0,
                    oos_lower=10.0,
                    target=20.0,
                ),
                ChannelPreset(
                    title="Humidity",
                    unit="%",
                    ooc_upper=50.0,
                    ooc_lower=30.0,
                    oos_upper=60.0,
                    oos_lower=20.0,
                    target=40.0,
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
                ),
            ],
        ),
    }

    _CHANNEL_COUNT_MAP: Dict[int, ServerType] = {
        1: ServerType.VOC,
        3: ServerType.NOISE,
    }

    @classmethod
    def get_preset(cls, server_type: ServerType) -> ServerTypePreset:
        return cls._PRESETS.get(server_type, cls._PRESETS[ServerType.UNKNOWN])

    @classmethod
    def detect_by_channel_count(cls, channel_count: int) -> ServerType:
        return cls._CHANNEL_COUNT_MAP.get(channel_count, ServerType.UNKNOWN)


@dataclass
class ChannelConfig:
    """单个通道的配置数据"""

    title: str = ""
    unit: str = ""
    ooc_upper: float = 80.0
    ooc_lower: float = 20.0
    oos_upper: float = 90.0
    oos_lower: float = 10.0
    target: float = 50.0
    show_ooc_upper: bool = True
    show_ooc_lower: bool = True
    show_oos_upper: bool = True
    show_oos_lower: bool = True
    show_target: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChannelConfig:
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
    def from_preset(cls, preset: ChannelPreset) -> ChannelConfig:
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

    JSON 结构:
    {
        "voc": {"channel_0": {...}, "channel_1": {...}},
        "noise": {"channel_0": {...}}
    }
    """

    def __init__(self, config_path: Path | None = None) -> None:
        if config_path is None:
            config_path = Path(__file__).parent / "channel_config.json"
        self._config_path = config_path
        self._data: Dict[str, Dict[str, ChannelConfig]] = {}
        self._current_server_type: ServerType = ServerType.UNKNOWN
        self._load()

    def set_server_type(self, server_type: ServerType) -> None:
        self._current_server_type = server_type
        if server_type.value not in self._data:
            self._data[server_type.value] = {}

    def _load(self) -> None:
        if not self._config_path.exists():
            return
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for server_type, channels in raw.items():
                if not isinstance(channels, dict):
                    continue
                self._data[server_type] = {}
                for ch_key, ch_data in channels.items():
                    try:
                        self._data[server_type][ch_key] = ChannelConfig.from_dict(ch_data)
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            print(f"[WARN] ChannelConfigManager: 加载配置失败: {e}")

    def save(self) -> None:
        try:
            raw: Dict[str, Dict[str, Any]] = {}
            for server_type, channels in self._data.items():
                raw[server_type] = {k: v.to_dict() for k, v in channels.items()}
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] ChannelConfigManager: 保存配置失败: {e}")

    def get(self, channel_idx: int) -> ChannelConfig:
        st = self._current_server_type.value
        ch_key = f"channel_{channel_idx}"
        if st not in self._data:
            self._data[st] = {}
        if ch_key not in self._data[st]:
            self._data[st][ch_key] = ChannelConfig(title=f"FOUP 通道 {channel_idx + 1}")
        return self._data[st][ch_key]

    def set(self, channel_idx: int, config: ChannelConfig) -> None:
        st = self._current_server_type.value
        ch_key = f"channel_{channel_idx}"
        if st not in self._data:
            self._data[st] = {}
        self._data[st][ch_key] = config
        self.save()

    def update(self, channel_idx: int, **kwargs: Any) -> ChannelConfig:
        config = self.get(channel_idx)
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self.set(channel_idx, config)
        return config
