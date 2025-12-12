"""
性能配置模块 - 用于优化不同环境下的渲染性能

此模块提供环境检测和 Qt 性能优化配置，特别针对 WSL2 环境。

使用方法:
    在 app.py 的 import 语句之后、创建 QApplication 之前调用:

    from voc_app.gui.performance_config import apply_performance_settings
    apply_performance_settings()
"""
import os
import sys
from pathlib import Path

from voc_app.logging_config import get_logger

logger = get_logger(__name__)


def detect_environment() -> dict:
    """
    检测当前运行环境

    Returns:
        包含环境信息的字典:
        - is_wsl: 是否在 WSL 中运行
        - is_wsl2: 是否在 WSL2 中运行
        - has_gpu: 是否有 GPU 加速 (WSL2 /dev/dxg)
        - display_type: 显示类型 (wayland/x11/unknown)
    """
    info = {
        "is_wsl": False,
        "is_wsl2": False,
        "has_gpu": False,
        "display_type": "unknown",
    }

    # 检测 WSL
    try:
        with open("/proc/version", "r") as f:
            version = f.read().lower()
            if "microsoft" in version or "wsl" in version:
                info["is_wsl"] = True
                if "wsl2" in version or Path("/dev/dxg").exists():
                    info["is_wsl2"] = True
    except (FileNotFoundError, PermissionError):
        pass

    # 检测 GPU 加速 (WSL2)
    if Path("/dev/dxg").exists():
        info["has_gpu"] = True

    # 检测显示类型
    if os.environ.get("WAYLAND_DISPLAY"):
        info["display_type"] = "wayland"
    elif os.environ.get("DISPLAY"):
        info["display_type"] = "x11"

    return info


def apply_performance_settings(force_software: bool = False) -> dict:
    """
    应用性能优化设置

    根据检测到的环境自动配置 Qt 性能参数。

    Args:
        force_software: 强制使用软件渲染（用于调试）

    Returns:
        应用的设置字典
    """
    env_info = detect_environment()
    settings = {}

    logger.info(f"检测到环境: {env_info}")

    # ========== 通用优化 ==========

    # 使用 OpenGL 作为 RHI 后端（已在 app.py 中设置）
    if "QSG_RHI_BACKEND" not in os.environ:
        os.environ["QSG_RHI_BACKEND"] = "opengl"
        settings["QSG_RHI_BACKEND"] = "opengl"

    # ========== WSL2 特定优化 ==========

    if env_info["is_wsl2"]:
        logger.info("检测到 WSL2 环境，应用特定优化...")

        # 强制使用 X11 (xcb) 而不是 Wayland，避免 Wayland 插件警告
        if "QT_QPA_PLATFORM" not in os.environ:
            os.environ["QT_QPA_PLATFORM"] = "xcb"
            settings["QT_QPA_PLATFORM"] = "xcb"

        # 禁用 Wayland 相关输出
        os.environ["QT_LOGGING_RULES"] = "qt.qpa.wayland=false"
        settings["QT_LOGGING_RULES"] = "qt.qpa.wayland=false"

        if env_info["has_gpu"] and not force_software:
            # WSL2 有 GPU 加速，使用硬件渲染
            logger.info("检测到 WSL2 GPU 支持 (/dev/dxg)")

            # 启用 threaded 渲染循环（可能在某些情况下提升性能）
            if "QSG_RENDER_LOOP" not in os.environ:
                os.environ["QSG_RENDER_LOOP"] = "threaded"
                settings["QSG_RENDER_LOOP"] = "threaded"
        else:
            # 无 GPU 或强制软件渲染
            logger.info("使用软件渲染模式")
            os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
            os.environ["QSG_RENDER_LOOP"] = "basic"
            settings["LIBGL_ALWAYS_SOFTWARE"] = "1"
            settings["QSG_RENDER_LOOP"] = "basic"

    # ========== 强制软件渲染 ==========

    if force_software:
        os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
        os.environ["QSG_RENDER_LOOP"] = "basic"
        settings["LIBGL_ALWAYS_SOFTWARE"] = "1"
        settings["QSG_RENDER_LOOP"] = "basic"
        logger.info("已强制启用软件渲染")

    logger.info(f"已应用性能设置: {settings}")
    return settings


# 频谱图推荐配置 - 根据环境返回建议的效果设置
def get_spectrum_config_for_env() -> dict:
    """
    根据当前环境返回频谱图的推荐配置

    Returns:
        频谱图组件的推荐属性设置
    """
    env_info = detect_environment()

    # 默认配置（高性能环境）
    config = {
        "glowEnabled": True,
        "reflectionEnabled": True,
        "scanLineEnabled": False,
        "borderGlowEnabled": True,
        "showPeakHold": True,
    }

    # WSL2 环境 - 降低效果以提升性能
    if env_info["is_wsl2"]:
        config = {
            "glowEnabled": False,        # 禁用发光 - 最大性能影响
            "reflectionEnabled": False,  # 禁用倒影 - 中等性能影响
            "scanLineEnabled": False,
            "borderGlowEnabled": True,   # 保留边框发光 - 影响小
            "showPeakHold": True,
        }
        logger.info("WSL2 环境: 建议禁用 glowEnabled 和 reflectionEnabled 以提升性能")

    return config


if __name__ == "__main__":
    # 测试环境检测
    print("=== 环境检测 ===")
    env = detect_environment()
    for k, v in env.items():
        print(f"  {k}: {v}")

    print("\n=== 推荐频谱配置 ===")
    config = get_spectrum_config_for_env()
    for k, v in config.items():
        print(f"  {k}: {v}")
