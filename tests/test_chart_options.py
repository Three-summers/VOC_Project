"""图表显示选项的配置解析（R22 / R23）。

R22 需要能配置"界面红色是否与后台报警一致"，R23 需要能配置 Y 轴范围策略。
两项都放在 ``system_config.json`` 的 ``chart`` 分区，并有安全默认值。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.chart_options import chart_display_options  # noqa: E402


def test_defaults_when_section_missing() -> None:
    assert chart_display_options(None) == {
        "alarmColorSyncWithLimits": True,
        "yAxisMode": "auto",
    }
    assert chart_display_options({}) == {
        "alarmColorSyncWithLimits": True,
        "yAxisMode": "auto",
    }


def test_reads_explicit_values() -> None:
    options = chart_display_options(
        {"alarm_color_sync_with_limits": False, "y_axis_mode": "zero"}
    )
    assert options == {"alarmColorSyncWithLimits": False, "yAxisMode": "zero"}


def test_invalid_y_axis_mode_falls_back_to_auto() -> None:
    options = chart_display_options({"y_axis_mode": "something-else"})
    assert options["yAxisMode"] == "auto"


def test_string_boolean_is_accepted() -> None:
    options = chart_display_options({"alarm_color_sync_with_limits": "false"})
    assert options["alarmColorSyncWithLimits"] is False


def test_bundled_system_config_exposes_chart_section() -> None:
    config = json.loads(
        (SRC_DIR / "voc_app" / "system_config.json").read_text(encoding="utf-8")
    )
    chart = config.get("chart")
    assert isinstance(chart, dict), "system_config.json 必须包含 chart 分区"
    assert "alarm_color_sync_with_limits" in chart
    assert chart["y_axis_mode"] in ("auto", "zero")
