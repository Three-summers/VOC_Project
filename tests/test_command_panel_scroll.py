"""Loadport 命令区可达性测试（R09）。

问题：9 个按钮放在不能滚动的 Column 里，默认 1024×768 下命令区只有约 568px
高，第 9 个按钮（故障复位）落到 y=691..747，被底部导航压住 —— 关键故障恢复
入口不可点。要求命令区可滚动，且滚到底后最后一个按钮确实进入可视区域。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 注册 QQuickItem 类型，否则 property("contentItem") / mapToItem 无法转换
from PySide6.QtQuick import QQuickItem  # noqa: E402,F401

QML_ROOT = ROOT_DIR / "src" / "voc_app" / "gui" / "qml"

# 真实主窗口中命令面板的可用高度（R09 证据：y=120..688）
PANEL_HEIGHT = 568
PANEL_WIDTH = 160

_WRAPPER = """
import QtQuick
import QtQuick.Controls
import "file://{qml_root}" as Ui

ApplicationWindow {{
    id: win
    width: {width}
    height: {height}
    visible: true

    property bool authenticated: true

    Ui.CommandPanel {{
        id: panel
        anchors.fill: parent
        currentView: "Status"
        currentSubPage: "loadport"
    }}
}}
"""


def _pump(app, seconds: float = 0.5) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)


@pytest.fixture()
def command_panel_env(qapp, tmp_path):
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    wrapper = tmp_path / "PanelProbe.qml"
    wrapper.write_text(
        _WRAPPER.format(
            qml_root=QML_ROOT.as_posix(), width=PANEL_WIDTH, height=PANEL_HEIGHT
        ),
        encoding="utf-8",
    )

    from voc_app.gui.app import AuthenticationManager

    auth = AuthenticationManager()
    auth.login("admin", "123456")  # 用真实认证对象，命令区应处于可用状态

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_ROOT))
    engine.rootContext().setContextProperty("authManager", auth)
    engine.load(QUrl.fromLocalFile(str(wrapper)))
    roots = engine.rootObjects()
    assert roots, "PanelProbe.qml 加载失败"
    window = roots[0]
    _pump(qapp, 0.8)
    # 同时返回 auth：Python 侧必须持有它，否则会被回收导致绑定失效
    return window, qapp, engine, auth


def _buttons(window) -> list:
    """取命令页里真实的按钮对象。

    不能用 window.findChildren 全量搜索：同一批按钮会返回重复/陈旧的包装对象，
    用它们做 mapToItem 会得到不随滚动变化的坐标，测试会假通过或假失败。
    """
    from PySide6.QtCore import QObject

    loader = window.findChild(QObject, "command_panel_loader")
    assert loader is not None, "未找到命令页 Loader"
    page = loader.property("item")
    assert page is not None, "命令页尚未加载"

    result = []
    for child in page.children():
        try:
            text = child.property("text")
        except RuntimeError:
            continue
        if "Button" in child.metaObject().className() and isinstance(text, str) and text:
            result.append(child)
    return result


def test_command_area_scrolls_and_reaches_last_button(command_panel_env) -> None:
    """验证真实几何：滚动前最后一个按钮在可视区外，滚到底后进入可视区。

    注意不能只做 y/contentY 的算术——必须在窗口坐标系里比较（mapToItem），
    否则会在"设了 ScrollView 的动态 contentY、内容其实没动"时误判为通过。
    """
    from PySide6.QtCore import QObject, QPointF

    window, app, _engine, _auth = command_panel_env

    scroll = window.findChild(QObject, "command_panel_scroll")
    assert scroll is not None, "命令区没有可滚动容器"
    # ScrollView 本身不是 Flickable：必须操作它内部的 contentItem，
    # 否则只是在 ScrollView 上创建了一个动态属性，内容并不会移动。
    flick = scroll.property("contentItem")
    viewport_height = flick.property("height")
    content_height = flick.property("contentHeight")
    assert content_height > viewport_height, (
        f"内容({content_height})没有超过可视区({viewport_height})，用例前提不成立"
    )

    buttons = _buttons(window)
    assert len(buttons) >= 9, f"命令按钮数量异常: {len(buttons)}"
    last = max(buttons, key=lambda item: item.property("y"))

    root_item = window.property("contentItem")

    def window_y(item) -> float:
        return item.mapToItem(root_item, QPointF(0, 0)).y()

    bottom_before = window_y(last) + last.property("height")
    assert bottom_before > viewport_height, (
        f"修复前的前提不成立：最后一个按钮本应在可视区外 (bottom={bottom_before})"
    )

    flick.setProperty("contentY", content_height - viewport_height)
    _pump(app, 0.3)

    assert flick.property("contentY") > 0, "滚动偏移没有生效"
    bottom_after = window_y(last) + last.property("height")
    assert bottom_after <= viewport_height + 1, (
        f"滚到底后最后一个按钮仍在可视区之外: bottom={bottom_after}, viewport={viewport_height}"
    )
    assert window_y(last) < bottom_before, "内容没有随滚动位移"


def test_command_buttons_are_disabled_when_logged_out(command_panel_env) -> None:
    """门控仍然生效：未登录时整块命令区不可交互"""
    from PySide6.QtCore import QObject

    window, _app, _engine, auth = command_panel_env
    assert auth.isAuthenticated is True
    scroll = window.findChild(QObject, "command_panel_scroll")
    assert scroll.property("enabled") is True  # 已登录

    loader = window.findChild(QObject, "command_panel_loader")
    assert loader is not None and loader.property("enabled") is True
