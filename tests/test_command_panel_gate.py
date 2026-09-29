"""命令面板登录门控的运行时集成测试。

用真实的 AuthenticationManager 与真实的 CommandPanel.qml 验证：
未登录时命令面板 Loader 处于 disabled，登录后立即变为可用。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

QML_ROOT = ROOT_DIR / "src" / "voc_app" / "gui" / "qml"

_WRAPPER = """
import QtQuick
import QtQuick.Controls
import "file://{qml_root}" as Ui

ApplicationWindow {{
    id: win
    width: 1024
    height: 768
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


def test_command_panel_is_disabled_until_login(qapp, tmp_path) -> None:
    from PySide6.QtCore import QObject, QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    from voc_app.gui.app import AuthenticationManager

    wrapper = tmp_path / "GateProbe.qml"
    wrapper.write_text(_WRAPPER.format(qml_root=QML_ROOT.as_posix()), encoding="utf-8")

    auth = AuthenticationManager()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_ROOT))
    engine.rootContext().setContextProperty("authManager", auth)
    engine.load(QUrl.fromLocalFile(str(wrapper)))

    roots = engine.rootObjects()
    assert roots, "GateProbe.qml 加载失败"
    window = roots[0]
    _pump(qapp, 0.5)

    loader = window.findChild(QObject, "command_panel_loader")
    assert loader is not None, "未找到命令面板 Loader"
    assert loader.property("enabled") is False, "未登录时命令面板必须不可点击"

    assert auth.login("admin", "123456") is True
    _pump(qapp, 0.5)

    assert loader.property("enabled") is True, "登录后命令面板必须恢复可用"

    auth.logout()
    _pump(qapp, 0.5)
    assert loader.property("enabled") is False, "登出后命令面板必须重新禁用"
