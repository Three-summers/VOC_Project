"""登录对话框会话清理测试（R07）。

问题：登录成功后关闭弹窗，用户名与密码仍留在输入框里；下一位操作员
重新打开对话框直接点 OK 就能恢复上一次的权限。要求重新打开必须重新输入。
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

QML_COMPONENTS = ROOT_DIR / "src" / "voc_app" / "gui" / "qml" / "components"

_WRAPPER = """
import QtQuick
import QtQuick.Controls
import "file://{components}" as Components

ApplicationWindow {{
    id: win
    width: 1024
    height: 768
    visible: true

    Components.LoginDialog {{
        id: dlg
        objectName: "login_dialog"
        popupAnchorItem: win.contentItem
    }}
}}
"""


def _pump(app, seconds: float = 0.3) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)


class _DialogHarness:
    def __init__(self, window, dialog, engine, app) -> None:
        self.window = window
        self.dialog = dialog
        self.engine = engine
        self.app = app

    def invoke(self, method: str) -> None:
        from PySide6.QtCore import QMetaObject, Qt

        QMetaObject.invokeMethod(self.dialog, method, Qt.DirectConnection)
        _pump(self.app)

    def open(self) -> None:
        self.invoke("open")

    def close(self) -> None:
        self.invoke("close")

    def text_fields(self) -> list:
        from PySide6.QtCore import QObject

        fields = [
            child
            for child in self.window.findChildren(QObject)
            if "TextField" in child.metaObject().className()
        ]
        fields.sort(key=lambda item: item.property("y"))
        return fields

    def username_field(self):
        return self.text_fields()[0]

    def password_field(self):
        # 按 y 排序后第二个输入框是密码（避免读取 echoMode 枚举的转换问题）
        return self.text_fields()[-1]

    def ok_button(self):
        from PySide6.QtCore import QObject

        for child in self.window.findChildren(QObject):
            if child.property("text") == "OK":
                return child
        raise AssertionError("未找到 OK 按钮")


@pytest.fixture()
def dialog_env(qapp, tmp_path):
    from PySide6.QtCore import QObject, QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    from voc_app.gui.app import AuthenticationManager

    wrapper = tmp_path / "LoginProbe.qml"
    wrapper.write_text(
        _WRAPPER.format(components=QML_COMPONENTS.as_posix()), encoding="utf-8"
    )

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_COMPONENTS))
    engine.rootContext().setContextProperty("authManager", AuthenticationManager())
    engine.load(QUrl.fromLocalFile(str(wrapper)))
    roots = engine.rootObjects()
    assert roots, "LoginProbe.qml 加载失败"
    window = roots[0]
    _pump(qapp)

    dialog = window.findChild(QObject, "login_dialog")
    assert dialog is not None, "未找到登录对话框"
    return _DialogHarness(window, dialog, engine, qapp)


def test_fields_are_cleared_when_dialog_reopens(dialog_env) -> None:
    env = dialog_env
    env.open()
    env.username_field().setProperty("text", "admin")
    env.password_field().setProperty("text", "123456")
    _pump(env.app)
    assert env.ok_button().property("enabled") is True

    env.close()
    env.open()

    assert env.username_field().property("text") == "", "重新打开时用户名必须被清空"
    assert env.password_field().property("text") == "", "重新打开时密码必须被清空"
    assert env.ok_button().property("enabled") is False, "空输入时 OK 必须不可用"


def test_reopening_after_logout_requires_typing_again(dialog_env) -> None:
    """注销（直接关闭再打开）后不能靠残留内容直接点 OK。"""
    env = dialog_env
    env.open()
    env.username_field().setProperty("text", "admin")
    env.password_field().setProperty("text", "123456")
    _pump(env.app)

    # 模拟"关闭弹窗"（含绕过 onClosed 的路径：直接改 visible 再打开）
    env.dialog.setProperty("visible", False)
    _pump(env.app)
    env.open()

    assert env.password_field().property("text") == ""
    assert env.ok_button().property("enabled") is False
