"""R22 / R23：图表限界颜色与 Y 轴范围的真实组件回归。

R22：图表报警颜色忽略了限界显示开关。后台 ``_check_channel_limits`` 只检查
     ``show_oos_upper/show_oos_lower/show_ooc_*`` 为真的限界；界面颜色却只看数值，
    于是"正常值 60、OOS 下限 80、OOC 下限 70 且下限显示关闭"时仍显示报警红。

R23：Y 轴下界被统一截到 0。CSV 含 -10/-5 时轴范围变成 [0, 1]，负值数据完全
     不可见；实时路径同样如此。

两个行为都由 ``system_config.json`` 的 ``chart`` 分区控制：
``alarm_color_sync_with_limits`` 决定界面红色是否与后台判定严格一致；
``y_axis_mode`` 决定轴范围策略（``auto`` / ``zero``）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl, Slot
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

QML_DIR = ROOT_DIR / "src" / "voc_app" / "gui" / "qml"
CHART_CARD_QML = QML_DIR / "components" / "ChartCard.qml"

SUCCESS = "#16a34a"
WARNING = "#f59e0b"
ALARM = "#e11d48"


class _LegendHelper(QObject):
    @Slot("QVariant", "QVariant")
    def hideSeriesInLegend(self, chart, series) -> None:  # noqa: D102
        pass


def _load_component(engine: QQmlApplicationEngine, url: Path):
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(url)))
    assert component.status() != QQmlComponent.Status.Error, [
        error.toString() for error in component.errors()
    ]
    obj = component.create()
    assert obj is not None, "QML 组件创建失败"
    return obj, component


# QQmlComponent 创建的对象由组件/QML 引擎管理；组件被 GC 会连带删除对象，
# 因此测试期间必须显式持有引用。
_KEEPALIVE: list = []


@pytest.fixture()
def chart_card(qapp):
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    legend_helper = _LegendHelper()
    engine.rootContext().setContextProperty("chartLegendHelper", legend_helper)
    engine.rootContext().setContextProperty(
        "chartOptions",
        {"alarmColorSyncWithLimits": True, "yAxisMode": "auto"},
    )
    card, component = _load_component(engine, CHART_CARD_QML)
    _KEEPALIVE.extend([engine, legend_helper, component, card])
    yield card, engine
    card.deleteLater()
    qapp.processEvents()


def _color_name(value) -> str:
    return QColor(value).name()


# ------------------------------------------------------------------ R22


def test_alarm_color_ignores_disabled_lower_limits_when_synced(chart_card) -> None:
    card, _engine = chart_card
    card.setProperty("oosLimitValue", 80.0)
    card.setProperty("oosLowerLimitValue", 80.0)
    card.setProperty("oocLimitValue", 70.0)
    card.setProperty("oocLowerLimitValue", 70.0)
    card.setProperty("showOosLower", False)
    card.setProperty("showOocLower", False)
    card.setProperty("currentValue", 60.0)

    assert _color_name(card.property("currentValueColor")) == SUCCESS, (
        "下限显示已关闭，界面不应与后台判定不一致地显示报警色"
    )


def test_alarm_color_still_alarms_on_enabled_upper_limit(chart_card) -> None:
    card, _engine = chart_card
    card.setProperty("oosLimitValue", 80.0)
    card.setProperty("oocLimitValue", 70.0)
    card.setProperty("showOosUpper", True)
    card.setProperty("showOocUpper", True)
    card.setProperty("currentValue", 85.0)

    assert _color_name(card.property("currentValueColor")) == ALARM


def test_alarm_color_warning_on_enabled_control_limit(chart_card) -> None:
    card, _engine = chart_card
    card.setProperty("oosLimitValue", 80.0)
    card.setProperty("oocLimitValue", 70.0)
    card.setProperty("showOosUpper", True)
    card.setProperty("showOocUpper", True)
    card.setProperty("currentValue", 75.0)

    assert _color_name(card.property("currentValueColor")) == WARNING


def test_alarm_color_can_be_decoupled_from_backend_switches(chart_card) -> None:
    """关闭同步后，界面按原始限值着色（允许只做界面提示、不设后台报警）。"""
    card, _engine = chart_card
    card.setProperty("oosLimitValue", 80.0)
    card.setProperty("oosLowerLimitValue", 80.0)
    card.setProperty("showOosLower", False)
    card.setProperty("showOocLower", False)
    card.setProperty("colorSyncWithLimits", False)
    card.setProperty("currentValue", 60.0)

    assert _color_name(card.property("currentValueColor")) == ALARM


# ------------------------------------------------------------------ R23


def _y_axis_min(card) -> float:
    return float(card.property("yAxisMin"))


def test_y_axis_shows_negative_data_in_auto_mode(chart_card) -> None:
    card, _engine = chart_card
    card.setProperty("yAxisMode", "auto")
    card.setProperty("dataPoints", [{"x": 0, "y": -10.0}, {"x": 1000, "y": -5.0}])

    assert _y_axis_min(card) < -10.0, "负值数据必须可见"


def test_y_axis_zero_mode_keeps_legacy_clipping(chart_card) -> None:
    card, _engine = chart_card
    card.setProperty("yAxisMode", "zero")
    card.setProperty("dataPoints", [{"x": 0, "y": -11.0}, {"x": 1000, "y": -6.0}])

    assert _y_axis_min(card) == 0.0


def test_y_axis_positive_data_still_starts_at_zero(chart_card) -> None:
    card, _engine = chart_card
    card.setProperty("yAxisMode", "auto")
    card.setProperty("dataPoints", [{"x": 0, "y": 10.0}, {"x": 1000, "y": 20.0}])

    assert _y_axis_min(card) >= 0.0, "全正数据不应出现负半轴"
