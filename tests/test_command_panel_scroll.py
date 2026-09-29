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
    from PySide6.QtCore import QObject

    result = []
    for child in window.findChildren(QObject):
        try:
            text = child.property("text")
        except RuntimeError:
            continue
        if isinstance(text, str) and text and hasattr(child, "property"):
            if "Button" in child.metaObject().className():
                result.append(child)
    return result


def test_command_area_scrolls_and_reaches_last_button(command_panel_env) -> None:
    from PySide6.QtCore import QObject

    window, app, _engine, _auth = command_panel_env

    scroll = window.findChild(QObject, "command_panel_scroll")
    assert scroll is not None, "命令区没有可滚动容器"
    viewport_height = scroll.property("height")
    content_height = scroll.property("contentHeight")
    assert content_height > viewport_height, (
        f"内容({content_height})没有超过可视区({viewport_height})，用例前提不成立"
    )

    buttons = _buttons(window)
    assert len(buttons) >= 9, f"命令按钮数量异常: {len(buttons)}"
    last = max(buttons, key=lambda item: item.property("y"))
    # 滚到底部后，最后一个按钮必须落在可视区内
    scroll.setProperty("contentY", content_height - viewport_height)
    _pump(app, 0.3)
    bottom_in_view = last.property("y") - scroll.property("contentY") + last.property("height")
    assert bottom_in_view <= viewport_height + 1, (
        f"滚到底后最后一个按钮仍在可视区之外: bottom={bottom_in_view}"
    )


def test_command_buttons_are_disabled_when_logged_out(command_panel_env) -> None:
    """门控仍然生效：未登录时整块命令区不可交互"""
    from PySide6.QtCore import QObject

    window, _app, _engine, auth = command_panel_env
    assert auth.isAuthenticated is True
    scroll = window.findChild(QObject, "command_panel_scroll")
    assert scroll.property("enabled") is True  # 已登录

    loader = window.findChild(QObject, "command_panel_loader")
    assert loader is not None and loader.property("enabled") is True
