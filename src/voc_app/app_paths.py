"""系统配置与运行期数据目录解析。

设计目标：把**运行期可变状态**（系统配置、通道配置、采集日志）从代码 release
目录中剥离出来。升级时 LoadportInstaller 只做 ``releases/loadport-<version>``
目录 + ``current`` 软链切换，如果这些文件继续写在源码目录里，现场设置会在每次
升级后丢失。

定位规则（优先级从高到低）：

系统配置文件
    1. 环境变量 ``VOC_SYSTEM_CONFIG``（绝对路径，测试/开发常用）
    2. ``<数据目录>/system_config.json``（首次启动由包内默认配置生成）
    3. 包内默认 ``src/voc_app/system_config.json``

数据目录
    1. 环境变量 ``VOC_DATA_DIR``
    2. 配置项 ``paths.data_directory``
    3. 用户数据目录 ``$XDG_DATA_HOME/voc``（缺省 ``~/.local/share/voc``）

注意：数据目录的"引导位置"由 ``VOC_DATA_DIR`` 或用户数据目录决定，用于定位用户
配置文件；配置项 ``paths.data_directory`` 只决定数据（通道配置、日志）落在哪里，
不再反向影响配置文件自身的查找位置，避免循环依赖。
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from voc_app.logging_config import get_logger

logger = get_logger(__name__)

PACKAGE_DIR = Path(__file__).resolve().parent
BUNDLED_CONFIG_PATH = PACKAGE_DIR / "system_config.json"
CONFIG_FILE_NAME = "system_config.json"
CHANNEL_CONFIG_FILE_NAME = "channel_config.json"
LEGACY_CHANNEL_CONFIG_PATH = PACKAGE_DIR / "gui" / CHANNEL_CONFIG_FILE_NAME
LOG_DIR_NAME = "Log"

DATA_DIR_ENV = "VOC_DATA_DIR"
CONFIG_PATH_ENV = "VOC_SYSTEM_CONFIG"

_config_cache: Optional[Dict[str, Any]] = None


def _expand(value: str) -> Path:
    return Path(value).expanduser()


def default_data_directory() -> Path:
    """用户数据目录：``$XDG_DATA_HOME/voc``，缺省 ``~/.local/share/voc``。"""
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    base = _expand(xdg) if xdg else Path.home() / ".local" / "share"
    return (base / "voc").resolve()


def bootstrap_directory() -> Path:
    """数据目录的引导位置，同时决定去哪里找用户 ``system_config.json``。"""
    env_value = os.environ.get(DATA_DIR_ENV, "").strip()
    if env_value:
        return _expand(env_value).resolve()
    return default_data_directory()


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"读取配置失败 {path}: {exc}")
        return {}
    return data if isinstance(data, dict) else {}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """递归合并：用户配置覆盖包内默认值，缺失的分区/键继续沿用默认值。"""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_system_config_path() -> Path:
    """返回当前生效的系统配置文件路径。"""
    env_value = os.environ.get(CONFIG_PATH_ENV, "").strip()
    if env_value:
        return _expand(env_value).resolve()
    candidate = bootstrap_directory() / CONFIG_FILE_NAME
    if candidate.exists():
        return candidate
    return BUNDLED_CONFIG_PATH


def load_config(refresh: bool = False) -> Dict[str, Any]:
    """加载系统配置：包内默认值 + 用户配置覆盖（结果被缓存）。"""
    global _config_cache
    if _config_cache is not None and not refresh:
        return _config_cache

    bundled = _read_json(BUNDLED_CONFIG_PATH)
    config_path = get_system_config_path()
    if config_path == BUNDLED_CONFIG_PATH:
        _config_cache = bundled
        return _config_cache

    user_config = _read_json(config_path)
    _config_cache = _deep_merge(bundled, user_config) if user_config else bundled
    return _config_cache


def reset_cache() -> None:
    """清除配置缓存（测试与热加载场景使用）。"""
    global _config_cache
    _config_cache = None


def get_data_directory() -> Path:
    """运行期数据目录（通道配置、采集日志等）。"""
    env_value = os.environ.get(DATA_DIR_ENV, "").strip()
    if env_value:
        return _expand(env_value).resolve()
    configured = str(get_value("paths", "data_directory", "") or "").strip()
    if configured:
        return _expand(configured).resolve()
    return bootstrap_directory()


def get_log_directory() -> Path:
    """采集日志与 CSV 浏览根目录（位于数据目录下）。"""
    return get_data_directory() / LOG_DIR_NAME


def get_section(name: str) -> Dict[str, Any]:
    """读取配置分区，非字典时返回空字典。"""
    section = load_config().get(name)
    return section if isinstance(section, dict) else {}


def get_value(section: str, key: str, default: Any = None) -> Any:
    """读取配置项，缺失或为 ``None`` 时返回默认值。"""
    value = get_section(section).get(key, default)
    return default if value is None else value


def ensure_data_directory() -> Path:
    """确保数据目录存在。"""
    directory = get_data_directory()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_user_config() -> Optional[Path]:
    """首次运行时用包内默认配置生成用户配置，返回新建的路径。

    显式指定 ``VOC_SYSTEM_CONFIG`` 时不生成，以免覆盖调用方指定的文件。
    """
    if os.environ.get(CONFIG_PATH_ENV, "").strip():
        return None
    target = bootstrap_directory() / CONFIG_FILE_NAME
    if target.exists() or not BUNDLED_CONFIG_PATH.exists():
        return None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(BUNDLED_CONFIG_PATH, target)
    except OSError as exc:
        logger.warning(f"生成用户系统配置失败 {target}: {exc}")
        return None
    logger.info(f"已生成用户系统配置: {target}")
    reset_cache()
    return target


def migrate_legacy_channel_config() -> Optional[Path]:
    """把旧的包内 ``channel_config.json`` 迁移到数据目录（仅当目标不存在）。"""
    target = get_data_directory() / CHANNEL_CONFIG_FILE_NAME
    if target.exists() or not LEGACY_CHANNEL_CONFIG_PATH.exists():
        return None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(LEGACY_CHANNEL_CONFIG_PATH, target)
    except OSError as exc:
        logger.warning(f"迁移旧通道配置失败: {exc}")
        return None
    logger.info(f"已迁移旧通道配置到数据目录: {target}")
    return target


def prepare_runtime_paths() -> Path:
    """应用启动时调用：准备数据目录、生成用户配置、迁移旧状态。"""
    ensure_data_directory()
    try:
        get_log_directory().mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning(f"创建日志目录失败: {exc}")
    ensure_user_config()
    migrate_legacy_channel_config()
    return get_data_directory()
