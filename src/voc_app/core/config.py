"""统一配置管理（JSON + 环境变量）。

特性：
1) 支持 JSON 文件与环境变量两种配置源
2) 支持配置合并与覆盖：JSON < 环境变量 < set() 覆盖
3) 支持配置变更通知机制（监听器）
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from voc_app.core.interfaces import ConfigProvider
from voc_app.logging_config import get_logger
from voc_app.utils import ConfigError

logger = get_logger(__name__)


@dataclass(frozen=True)
class ConfigChangeEvent:
    """配置变更事件。"""

    key: str
    old_value: Any
    new_value: Any
    source: str


_MISSING = object()


def _deep_merge(left: dict[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """递归合并字典（right 覆盖 left）。"""
    merged: dict[str, Any] = dict(left)
    for key, value in right.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, Mapping)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _get_by_path(data: Mapping[str, Any], path: str, default: Any = _MISSING) -> Any:
    if not path:
        return data
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _set_by_path(target: dict[str, Any], path: str, value: Any) -> None:
    if not path:
        raise ConfigError("配置 key 不能为空")
    cur: dict[str, Any] = target
    parts = path.split(".")
    for part in parts[:-1]:
        next_node = cur.get(part)
        if not isinstance(next_node, dict):
            next_node = {}
            cur[part] = next_node
        cur = next_node
    cur[parts[-1]] = value


def _flatten(data: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            result.update(_flatten(value, full_key))
        else:
            result[full_key] = value
    return result


def _parse_env_value(raw: str) -> Any:
    """尽力将环境变量字符串解析为 JSON 值。"""
    raw_strip = raw.strip()
    try:
        return json.loads(raw_strip)
    except Exception:  # noqa: BLE001
        return raw


class AppConfig(ConfigProvider):
    """统一配置管理实现（JSON 文件 + 环境变量）。"""

    def __init__(
        self,
        *,
        json_path: Optional[str | Path] = None,
        env_prefix: str = "VOC_",
        env_separator: str = "__",
    ) -> None:
        self._lock = threading.RLock()
        self._json_path = Path(json_path) if json_path is not None else None
        self._env_prefix = env_prefix
        self._env_separator = env_separator

        self._file_config: dict[str, Any] = {}
        self._env_config: dict[str, Any] = {}
        self._overrides: dict[str, Any] = {}
        self._listeners: list[Callable[[ConfigChangeEvent], None]] = []

    # ------------------------------------------------------------------
    # 监听器
    # ------------------------------------------------------------------
    def add_listener(self, callback: Callable[[ConfigChangeEvent], None]) -> None:
        """添加配置变更监听器。"""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[ConfigChangeEvent], None]) -> None:
        """移除配置变更监听器。"""
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    # ------------------------------------------------------------------
    # ConfigProvider 接口
    # ------------------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            effective = self._effective_config_locked()
            value = _get_by_path(effective, key, default=_MISSING)
            return default if value is _MISSING else value

    def set(self, key: str, value: Any) -> None:
        events: list[ConfigChangeEvent]
        with self._lock:
            old_effective = self._effective_config_locked()
            _set_by_path(self._overrides, key, value)
            new_effective = self._effective_config_locked()
            events = self._diff_events(old_effective, new_effective, source="set")
        self._emit_events(events)

    def load(self) -> None:
        events: list[ConfigChangeEvent]
        with self._lock:
            old_effective = self._effective_config_locked()
            self._file_config = self._load_json_locked()
            self._env_config = self._load_env_locked()
            new_effective = self._effective_config_locked()
            events = self._diff_events(old_effective, new_effective, source="load")
        self._emit_events(events)

    def save(self) -> None:
        with self._lock:
            if self._json_path is None:
                raise ConfigError("未配置 json_path，无法保存配置")
            data_to_save = _deep_merge(self._file_config, self._overrides)
            self._json_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(self._json_path, "w", encoding="utf-8") as f:
                    json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            except OSError as exc:
                raise ConfigError(
                    "保存配置文件失败",
                    context={"path": str(self._json_path), "error": str(exc)},
                ) from exc

    # ------------------------------------------------------------------
    # 扩展能力
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """获取当前生效配置（深拷贝语义的浅实现：返回新 dict）。"""
        with self._lock:
            return dict(self._effective_config_locked())

    def clear_overrides(self) -> None:
        """清空 set() 覆盖层。"""
        events: list[ConfigChangeEvent]
        with self._lock:
            old_effective = self._effective_config_locked()
            self._overrides.clear()
            new_effective = self._effective_config_locked()
            events = self._diff_events(old_effective, new_effective, source="clear_overrides")
        self._emit_events(events)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    def _effective_config_locked(self) -> dict[str, Any]:
        merged = _deep_merge(self._file_config, self._env_config)
        merged = _deep_merge(merged, self._overrides)
        return merged

    def _load_json_locked(self) -> dict[str, Any]:
        if self._json_path is None:
            return {}
        if not self._json_path.exists():
            return {}
        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                "配置文件 JSON 解析失败",
                context={"path": str(self._json_path), "error": str(exc)},
            ) from exc
        except OSError as exc:
            raise ConfigError(
                "读取配置文件失败",
                context={"path": str(self._json_path), "error": str(exc)},
            ) from exc

        if not isinstance(data, dict):
            raise ConfigError("配置文件根节点必须为 JSON object", context={"path": str(self._json_path)})
        return data

    def _load_env_locked(self) -> dict[str, Any]:
        env_data: dict[str, Any] = {}
        prefix = self._env_prefix
        for env_key, raw_value in os.environ.items():
            if prefix and not env_key.startswith(prefix):
                continue
            key = env_key[len(prefix) :] if prefix else env_key
            key = key.strip()
            if not key:
                continue
            # 约定：双下划线表示层级分隔
            key_path = key.lower().replace(self._env_separator, ".")
            _set_by_path(env_data, key_path, _parse_env_value(raw_value))
        return env_data

    def _diff_events(
        self,
        old_cfg: Mapping[str, Any],
        new_cfg: Mapping[str, Any],
        *,
        source: str,
    ) -> list[ConfigChangeEvent]:
        old_flat = _flatten(old_cfg)
        new_flat = _flatten(new_cfg)
        events: list[ConfigChangeEvent] = []
        all_keys = set(old_flat.keys()) | set(new_flat.keys())
        for key in sorted(all_keys):
            old_val = old_flat.get(key, _MISSING)
            new_val = new_flat.get(key, _MISSING)
            if old_val != new_val:
                events.append(
                    ConfigChangeEvent(
                        key=key,
                        old_value=None if old_val is _MISSING else old_val,
                        new_value=None if new_val is _MISSING else new_val,
                        source=source,
                    )
                )
        return events

    def _emit_events(self, events: list[ConfigChangeEvent]) -> None:
        if not events:
            return
        with self._lock:
            listeners = list(self._listeners)
        for event in events:
            for listener in listeners:
                try:
                    listener(event)
                except Exception as exc:  # noqa: BLE001
                    logger.error(f"配置监听器执行失败: {exc}", exc_info=True)
