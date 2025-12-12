"""VOC 应用统一日志配置模块

提供统一的日志记录功能，替代分散的 print() 调用。

使用方法:
    from voc_app.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("应用启动")
    logger.warning("警告信息")
    logger.error("错误信息", exc_info=True)

配置日志级别:
    from voc_app.logging_config import configure_levels, set_level

    # 方式1: 设置全局级别
    set_level(logging.DEBUG)

    # 方式2: 按模块配置不同级别
    configure_levels({
        "voc_app": "INFO",           # 全局默认 INFO
        "voc_app.gui": "WARNING",    # gui 模块只显示 WARNING 及以上
        "voc_app.loadport": "DEBUG", # loadport 模块显示 DEBUG
    })

    # 方式3: 从配置文件加载
    configure_from_file("logging_config.json")
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Union


# 默认日志格式
_DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_SIMPLE_FORMAT = "%(levelname)s - %(message)s"
_DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s"

# 全局日志器缓存
_loggers: dict[str, logging.Logger] = {}
_initialized = False

# 模块级别配置
_module_levels: Dict[str, int] = {}

# 级别名称到数值的映射
_LEVEL_MAP: Dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
    "FATAL": logging.CRITICAL,
    "NOTSET": logging.NOTSET,
}


def _parse_level(level: Union[int, str]) -> int:
    """解析日志级别（支持字符串或整数）"""
    if isinstance(level, int):
        return level
    level_upper = level.upper().strip()
    if level_upper in _LEVEL_MAP:
        return _LEVEL_MAP[level_upper]
    # 尝试解析数字字符串
    try:
        return int(level)
    except ValueError:
        return logging.INFO


def setup_logging(
    level: Union[int, str] = logging.INFO,
    log_file: Optional[Path] = None,
    console: bool = True,
    format_string: str = _DEFAULT_FORMAT,
) -> logging.Logger:
    """初始化日志系统

    Args:
        level: 日志级别，默认 INFO。支持字符串 ("DEBUG", "INFO" 等) 或整数
        log_file: 可选的日志文件路径
        console: 是否输出到控制台，默认 True
        format_string: 日志格式字符串

    Returns:
        根日志器实例
    """
    global _initialized

    level_int = _parse_level(level)

    # 获取根日志器
    root_logger = logging.getLogger("voc_app")
    root_logger.setLevel(level_int)

    # 避免重复添加 handler
    if _initialized:
        return root_logger

    formatter = logging.Formatter(format_string)

    # 控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level_int)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level_int)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _initialized = True
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器

    Args:
        name: 日志器名称，通常使用 __name__

    Returns:
        日志器实例

    Example:
        logger = get_logger(__name__)
        logger.info("消息")
    """
    if name in _loggers:
        return _loggers[name]

    # 确保根日志器已初始化
    if not _initialized:
        setup_logging()

    # 创建子日志器
    if name.startswith("voc_app"):
        logger = logging.getLogger(name)
    else:
        logger = logging.getLogger(f"voc_app.{name}")

    # 应用模块特定级别（如果已配置）
    _apply_module_level(logger)

    _loggers[name] = logger
    return logger


def _apply_module_level(logger: logging.Logger) -> None:
    """为日志器应用模块特定级别"""
    if not _module_levels:
        return

    logger_name = logger.name

    # 查找最匹配的模块配置（最长前缀匹配）
    best_match = ""
    best_level = None

    for module_prefix, level in _module_levels.items():
        if logger_name == module_prefix or logger_name.startswith(module_prefix + "."):
            if len(module_prefix) > len(best_match):
                best_match = module_prefix
                best_level = level

    if best_level is not None:
        logger.setLevel(best_level)


def set_level(level: Union[int, str]) -> None:
    """动态设置全局日志级别

    Args:
        level: 日志级别 (logging.DEBUG, logging.INFO, etc.) 或字符串 ("DEBUG", "INFO" 等)
    """
    level_int = _parse_level(level)
    root_logger = logging.getLogger("voc_app")
    root_logger.setLevel(level_int)
    for handler in root_logger.handlers:
        handler.setLevel(level_int)


def set_module_level(module: str, level: Union[int, str]) -> None:
    """设置特定模块的日志级别

    Args:
        module: 模块名称（如 "voc_app.gui", "voc_app.loadport"）
        level: 日志级别

    Example:
        # 只显示 gui 模块的 WARNING 及以上级别
        set_module_level("voc_app.gui", "WARNING")

        # 显示 loadport 模块的所有日志
        set_module_level("voc_app.loadport", "DEBUG")
    """
    level_int = _parse_level(level)
    _module_levels[module] = level_int

    # 更新已存在的日志器
    logger = logging.getLogger(module)
    logger.setLevel(level_int)

    # 更新缓存中相关的日志器
    for name, cached_logger in _loggers.items():
        if name == module or name.startswith(module + "."):
            _apply_module_level(cached_logger)


def configure_levels(config: Dict[str, Union[int, str]]) -> None:
    """批量配置模块日志级别

    Args:
        config: 模块到级别的映射字典

    Example:
        configure_levels({
            "voc_app": "INFO",           # 全局默认
            "voc_app.gui": "WARNING",    # gui 模块
            "voc_app.loadport": "DEBUG", # loadport 模块
        })
    """
    global _module_levels
    _module_levels.clear()

    for module, level in config.items():
        level_int = _parse_level(level)
        _module_levels[module] = level_int

        # 立即应用到对应日志器
        logger = logging.getLogger(module)
        logger.setLevel(level_int)

    # 更新所有缓存的日志器
    for cached_logger in _loggers.values():
        _apply_module_level(cached_logger)


def configure_from_file(config_path: Union[str, Path]) -> bool:
    """从 JSON 配置文件加载日志级别配置

    配置文件格式:
    {
        "levels": {
            "voc_app": "INFO",
            "voc_app.gui": "WARNING",
            "voc_app.loadport": "DEBUG"
        },
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }

    Args:
        config_path: 配置文件路径

    Returns:
        是否成功加载配置
    """
    config_path = Path(config_path)
    if not config_path.exists():
        return False

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 应用级别配置
        if "levels" in config and isinstance(config["levels"], dict):
            configure_levels(config["levels"])

        # 应用格式配置（需要重新初始化）
        if "format" in config:
            global _initialized
            root_logger = logging.getLogger("voc_app")
            formatter = logging.Formatter(config["format"])
            for handler in root_logger.handlers:
                handler.setFormatter(formatter)

        return True
    except (json.JSONDecodeError, IOError, KeyError):
        return False


def configure_from_env() -> None:
    """从环境变量加载日志配置

    支持的环境变量:
        VOC_LOG_LEVEL: 全局日志级别 (DEBUG, INFO, WARNING, ERROR)
        VOC_LOG_FILE: 日志文件路径
        VOC_LOG_FORMAT: 日志格式 (default, simple, detailed)
    """
    # 全局级别
    env_level = os.environ.get("VOC_LOG_LEVEL")
    if env_level:
        set_level(env_level)

    # 日志文件
    env_file = os.environ.get("VOC_LOG_FILE")
    if env_file and _initialized:
        root_logger = logging.getLogger("voc_app")
        file_path = Path(env_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(root_logger.level)
        file_handler.setFormatter(root_logger.handlers[0].formatter if root_logger.handlers else logging.Formatter(_DEFAULT_FORMAT))
        root_logger.addHandler(file_handler)

    # 日志格式
    env_format = os.environ.get("VOC_LOG_FORMAT", "").lower()
    format_map = {
        "simple": _SIMPLE_FORMAT,
        "detailed": _DETAILED_FORMAT,
        "default": _DEFAULT_FORMAT,
    }
    if env_format in format_map and _initialized:
        root_logger = logging.getLogger("voc_app")
        formatter = logging.Formatter(format_map[env_format])
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)


def get_current_config() -> Dict[str, Union[str, Dict[str, str]]]:
    """获取当前日志配置

    Returns:
        包含当前配置的字典
    """
    root_logger = logging.getLogger("voc_app")
    level_name = logging.getLevelName(root_logger.level)

    module_levels_str = {
        module: logging.getLevelName(level)
        for module, level in _module_levels.items()
    }

    return {
        "global_level": level_name,
        "module_levels": module_levels_str,
        "initialized": _initialized,
        "handlers": [type(h).__name__ for h in root_logger.handlers],
    }


def reset() -> None:
    """重置日志配置（主要用于测试）"""
    global _initialized, _module_levels, _loggers

    root_logger = logging.getLogger("voc_app")
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)

    _initialized = False
    _module_levels.clear()
    _loggers.clear()


# 便捷的日志级别常量
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

# 便捷的格式常量
FORMAT_DEFAULT = _DEFAULT_FORMAT
FORMAT_SIMPLE = _SIMPLE_FORMAT
FORMAT_DETAILED = _DETAILED_FORMAT
