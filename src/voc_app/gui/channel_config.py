"""通道配置管理模块

负责基于前缀的预设配置、通道配置的持久化管理。
前缀（prefix）是服务器类型的唯一标识，统一使用大写形式。
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from voc_app.logging_config import get_logger

logger = get_logger(__name__)


# 默认前缀映射（通道数 -> 大写前缀），用于服务器未返回前缀时的后备
DEFAULT_PREFIX_BY_CHANNEL: Dict[int, str] = {
    1: "VOC",
    3: "NOISE_HUMILITY",
}


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
class PrefixPreset:
    """前缀类型的预设配置"""

    prefix: str  # 大写前缀，如 "VOC", "NOISE_HUMILITY"
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


class PrefixRegistry:
    """前缀类型注册表，以大写 prefix 为键"""

    _PRESETS: Dict[str, PrefixPreset] = {
        "VOC": PrefixPreset(
            prefix="VOC",
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
        "NOISE_HUMILITY": PrefixPreset(
            prefix="NOISE_HUMILITY",
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
    }

    # 通道数到默认前缀的映射
    _CHANNEL_COUNT_MAP: Dict[int, str] = {
        1: "VOC",
        3: "NOISE_HUMILITY",
    }

    # 默认预设（用于未知前缀）
    _DEFAULT_PRESET = PrefixPreset(
        prefix="UNKNOWN",
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
    )

    @classmethod
    def get_preset(cls, prefix: str) -> PrefixPreset:
        """根据前缀获取预设，prefix 会被转为大写匹配"""
        return cls._PRESETS.get(prefix.upper(), cls._DEFAULT_PRESET)

    @classmethod
    def get_preset_by_channel_count(cls, channel_count: int) -> PrefixPreset:
        """根据通道数获取默认预设"""
        prefix = cls._CHANNEL_COUNT_MAP.get(channel_count)
        if prefix:
            return cls._PRESETS.get(prefix, cls._DEFAULT_PRESET)
        return cls._DEFAULT_PRESET

    @classmethod
    def get_default_prefix(cls, channel_count: int) -> str:
        """根据通道数获取默认前缀"""
        return cls._CHANNEL_COUNT_MAP.get(channel_count, "UNKNOWN")


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

    JSON 结构（以 prefix 为键）:
    {
        "VOC": {
            "_meta": {"channel_count": 1},
            "channel_0": {...}
        },
        "NOISE_HUMILITY": {
            "_meta": {"channel_count": 3},
            "channel_0": {...}, "channel_1": {...}, "channel_2": {...}
        }
    }

    特性:
    - 防抖保存：频繁修改时延迟写入，减少 I/O
    - 线程安全：支持多线程访问
    - 自动备份：保存前备份旧文件
    """

    # 防抖延迟时间（秒）
    SAVE_DELAY: float = 1.0

    def __init__(self, config_path: Optional[Path] = None) -> None:
        if config_path is None:
            config_path = Path(__file__).parent / "channel_config.json"
        self._config_path = config_path
        self._backup_path = config_path.with_suffix(".json.bak")
        self._data: Dict[str, Dict[str, ChannelConfig]] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._current_prefix: str = ""

        # 防抖保存相关
        self._save_timer: Optional[threading.Timer] = None
        self._save_lock = threading.Lock()
        self._dirty = False  # 标记是否有未保存的更改

        self._load()

    def set_prefix(self, prefix: str, channel_count: int) -> None:
        """设置当前前缀（大写），如果不存在则创建默认配置"""
        prefix = prefix.upper()  # 统一大写
        self._current_prefix = prefix
        if prefix not in self._data:
            self._data[prefix] = {}
            self._meta[prefix] = {"channel_count": channel_count}
            # 应用默认预设
            preset = PrefixRegistry.get_preset(prefix)
            for i in range(channel_count):
                ch_preset = preset.get_channel_preset(i)
                self._data[prefix][f"channel_{i}"] = ChannelConfig.from_preset(ch_preset)
            self._schedule_save()

    def get_prefix(self) -> str:
        return self._current_prefix

    def has_prefix(self, prefix: str) -> bool:
        return prefix.upper() in self._data

    def _load(self) -> None:
        """从文件加载配置"""
        if not self._config_path.exists():
            logger.debug(f"配置文件不存在，将使用默认配置: {self._config_path}")
            return
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for raw_prefix, content in raw.items():
                if not isinstance(content, dict):
                    continue
                # 兼容旧配置：统一转为大写
                prefix = raw_prefix.upper()
                self._data[prefix] = {}
                self._meta[prefix] = {}
                for key, value in content.items():
                    if key == "_meta" and isinstance(value, dict):
                        self._meta[prefix] = value
                    elif key.startswith("channel_"):
                        try:
                            self._data[prefix][key] = ChannelConfig.from_dict(value)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"解析通道配置失败 [{prefix}/{key}]: {e}")
                            continue
            logger.info(f"已加载配置文件: {self._config_path}")
        except json.JSONDecodeError as e:
            logger.error(f"配置文件 JSON 格式错误: {e}")
        except Exception as e:
            logger.error(f"加载配置失败: {e}", exc_info=True)

    def _schedule_save(self) -> None:
        """调度延迟保存（防抖机制）"""
        with self._save_lock:
            self._dirty = True
            # 取消之前的定时器
            if self._save_timer is not None:
                self._save_timer.cancel()
            # 创建新的定时器
            self._save_timer = threading.Timer(self.SAVE_DELAY, self._do_save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def _do_save(self) -> None:
        """执行实际的保存操作"""
        with self._save_lock:
            if not self._dirty:
                return
            self._dirty = False
            self._save_timer = None

        try:
            # 备份旧文件
            if self._config_path.exists():
                try:
                    self._config_path.rename(self._backup_path)
                except OSError:
                    pass  # 备份失败不影响保存

            raw: Dict[str, Dict[str, Any]] = {}
            all_prefixes = set(self._data.keys()) | set(self._meta.keys())
            for prefix in all_prefixes:
                raw[prefix] = {}
                if prefix in self._meta and self._meta[prefix]:
                    raw[prefix]["_meta"] = self._meta[prefix]
                if prefix in self._data:
                    for k, v in self._data[prefix].items():
                        raw[prefix][k] = v.to_dict()

            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False, indent=2)
            logger.debug(f"配置已保存: {self._config_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}", exc_info=True)
            # 尝试恢复备份
            if self._backup_path.exists():
                try:
                    self._backup_path.rename(self._config_path)
                    logger.info("已从备份恢复配置文件")
                except OSError:
                    pass

    def save(self) -> None:
        """立即保存配置（跳过防抖）"""
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None
            self._dirty = True
        self._do_save()

    def flush(self) -> None:
        """确保所有待保存的更改已写入磁盘"""
        self.save()

    def get(self, channel_idx: int) -> ChannelConfig:
        """获取指定通道的配置"""
        prefix = self._current_prefix
        ch_key = f"channel_{channel_idx}"
        if prefix not in self._data:
            self._data[prefix] = {}
        if ch_key not in self._data[prefix]:
            self._data[prefix][ch_key] = ChannelConfig(title=f"通道 {channel_idx + 1}")
        return self._data[prefix][ch_key]

    def set(self, channel_idx: int, config: ChannelConfig) -> None:
        """设置指定通道的配置"""
        prefix = self._current_prefix
        ch_key = f"channel_{channel_idx}"
        if prefix not in self._data:
            self._data[prefix] = {}
        self._data[prefix][ch_key] = config
        self._schedule_save()

    def update(self, channel_idx: int, **kwargs: Any) -> ChannelConfig:
        """更新指定通道的部分配置"""
        config = self.get(channel_idx)
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self.set(channel_idx, config)
        return config
