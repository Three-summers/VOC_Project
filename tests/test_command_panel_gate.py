"""命令面板登录门控的运行时集成测试。

用真实的 AuthenticationManager 与真实的 CommandPanel.qml 验证两件事：

1. 未登录时命令面板不可点击，登录后恢复；
2. 未登录时**不渲染命令内容**，只在面板中心显示占位提示——避免提示文字
   浮在按钮文字上导致重叠看不清。
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

PANEL_HEIGHT = 768

_WRAPPER = """
import QtQuick
import QtQuick.Controls
import "file://{qml_root}" as Ui

ApplicationWindow {{
    id: win
    width: 1024
    height: {height}
    visible: true

    Ui.CommandPanel {{
        anchors.fill: parent
        currentView: "Status"
        currentSubPage: "foup"
    }}
}}
"""


def _pump(app, seconds: float = 1.5) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)


@pytest.fixture()
def panel_env(qapp, tmp_path):
    """加载带 CommandPanel 的探针窗口，返回 (window, auth)。"""
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    from voc_app.gui.app import AuthenticationManager

    wrapper = tmp_path / "GateProbe.qml"
    wrapper.write_text(
        _WRAPPER.format(qml_root=QML_ROOT.as_posix(), height=PANEL_HEIGHT),
        encoding="utf-8",
    )

    auth = AuthenticationManager()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_ROOT))
    engine.rootContext().setContextProperty("authManager", auth)
    engine.load(QUrl.fromLocalFile(str(wrapper)))

    roots = engine.rootObjects()
    assert roots, "GateProbe.qml 加载失败"
    window = roots[0]
    _pump(qapp, 0.5)
    # 同时返回 engine：它是 QML 对象的持有者，被回收后 window 会失效
    return window, auth, qapp, engine


def test_command_panel_is_disabled_until_login(panel_env) -> None:
    from PySide6.QtCore import QObject

    window, auth, app, _engine = panel_env
    loader = window.findChild(QObject, "command_panel_loader")
    assert loader is not None, "未找到命令面板 Loader"
    assert loader.property("enabled") is False, "未登录时命令面板必须不可点击"

    assert auth.login("admin", "123456") is True
    _pump(app, 0.5)
    assert loader.property("enabled") is True, "登录后命令面板必须恢复可用"

    auth.logout()
    _pump(app, 0.5)
    assert loader.property("enabled") is False, "登出后命令面板必须重新禁用"


def test_login_hint_replaces_commands_instead_of_overlaying(panel_env) -> None:
    """提示与命令内容二选一显示，结构上不可能重叠"""
    from PySide6.QtCore import QObject

    window, auth, app, _engine = panel_env
    loader = window.findChild(QObject, "command_panel_loader")
    hint = window.findChild(QObject, "command_panel_login_hint")
    assert loader is not None and hint is not None

    # 未登录：只显示提示，命令内容完全不渲染
    assert loader.property("visible") is False, "未登录时仍在渲染命令内容"
    assert hint.property("visible") is True, "未登录时应显示登录提示"
    assert loader.property("visible") != hint.property("visible")

    assert auth.login("admin", "123456") is True
    _pump(app, 0.5)
    assert loader.property("visible") is True
    assert hint.property("visible") is False
    assert loader.property("visible") != hint.property("visible")

    auth.logout()
    _pump(app, 0.5)
    assert loader.property("visible") is False
    assert hint.property("visible") is True


def test_login_hint_is_centered_in_the_panel(panel_env) -> None:
    """提示应居中占位，而不是压在面板顶部/底部的其它文字上"""
    from PySide6.QtCore import QObject

    window, _auth, _app, _engine = panel_env
    column = window.findChild(QObject, "command_panel_login_placeholder_column")
    assert column is not None, "未找到登录占位块"

    center = column.property("y") + column.property("height") / 2
    assert abs(center - PANEL_HEIGHT / 2) < 60, f"提示未居中: center={center}"
