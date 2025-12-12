"""VOC 应用统一日志配置模块

提供统一的日志记录功能，替代分散的 print() 调用。

使用方法:
    from voc_app.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("应用启动")
    logger.warning("警告信息")
    logger.error("错误信息", exc_info=True)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


# 默认日志格式
_DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_SIMPLE_FORMAT = "%(levelname)s - %(message)s"

# 全局日志器缓存
_loggers: dict[str, logging.Logger] = {}
_initialized = False


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    console: bool = True,
    format_string: str = _DEFAULT_FORMAT,
) -> logging.Logger:
    """初始化日志系统

    Args:
        level: 日志级别，默认 INFO
        log_file: 可选的日志文件路径
        console: 是否输出到控制台，默认 True
        format_string: 日志格式字符串

    Returns:
        根日志器实例
    """
    global _initialized

    # 获取根日志器
    root_logger = logging.getLogger("voc_app")
    root_logger.setLevel(level)

    # 避免重复添加 handler
    if _initialized:
        return root_logger

    formatter = logging.Formatter(format_string)

    # 控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
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

    _loggers[name] = logger
    return logger


def set_level(level: int) -> None:
    """动态设置日志级别

    Args:
        level: 日志级别 (logging.DEBUG, logging.INFO, etc.)
    """
    root_logger = logging.getLogger("voc_app")
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)


# 便捷的日志级别常量
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
