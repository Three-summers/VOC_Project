"""图表显示选项（R22 / R23）。

这两项行为容易随现场口径变化，因此从 ``system_config.json`` 的 ``chart``
分区读取，再通过上下文属性 ``chartOptions`` 注入 QML：

``alarm_color_sync_with_limits``
    图表数值颜色是否与后台越限判定严格一致。
    - ``true``（默认）：只对启用了显示开关的限界着色，与
      ``FoupAcquisitionController._check_channel_limits`` 完全一致；
    - ``false``：按原始限值着色，允许"界面红色提示、但不设后台报警"。

``y_axis_mode``
    Y 轴下界策略。
    - ``auto``（默认）：数据/限界含负值时显示负半轴，全正数据仍从 0 起；
    - ``zero``：保持历史行为，统一把下界截到 0。
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

DEFAULT_ALARM_COLOR_SYNC_WITH_LIMITS = True
DEFAULT_Y_AXIS_MODE = "auto"
Y_AXIS_MODES = ("auto", "zero")


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def chart_display_options(section: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """把 ``chart`` 配置分区规范化为 QML 可直接使用的选项字典。"""
    section = section or {}
    mode = str(section.get("y_axis_mode", DEFAULT_Y_AXIS_MODE) or "").strip().lower()
    if mode not in Y_AXIS_MODES:
        mode = DEFAULT_Y_AXIS_MODE
    return {
        "alarmColorSyncWithLimits": _as_bool(
            section.get("alarm_color_sync_with_limits"),
            DEFAULT_ALARM_COLOR_SYNC_WITH_LIMITS,
        ),
        "yAxisMode": mode,
    }
