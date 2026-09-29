"""登录对话框底部按钮区与对话框边界的对齐测试。

实测过的问题：Qt Quick Controls 的 Popup 默认带 6px padding，BaseDialog 没有
清零，于是 contentItem 被四周内缩 6px —— 底部按钮区（白色 surface 矩形）比
对话框左右各窄 6px、底边还溢出 12px，看起来就是"白色矩形没有和对话框对齐"。
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

    property var report: null

    Components.LoginDialog {{
        id: dlg
        objectName: "probeDialog"
        popupAnchorItem: win.contentItem
    }}

    function measure() {{
        var content = dlg.contentItem;
        var footer = null;
        for (var i = 0; i < content.children.length; ++i) {{
            var child = content.children[i];
            if (child.height !== undefined)
                footer = child;
        }}
        if (!footer) {{
            report = {{ error: "footer not found" }};
            return;
        }}
        report = {{
            popupW: Math.round(dlg.width),
            popupH: Math.round(dlg.height),
            padding: dlg.padding,
            contentX: Math.round(content.x),
            contentY: Math.round(content.y),
            footerX: Math.round(content.x + footer.x),
            footerW: Math.round(footer.width),
            footerBottom: Math.round(content.y + footer.y + footer.height)
        }};
    }}

    Timer {{
        interval: 60
        running: true
        onTriggered: win.measure()
    }}

    Component.onCompleted: dlg.open()
}}
"""


class _FakeAuth:
    def __init__(self) -> None:
        self.isAuthenticated = False
        self.currentUser = ""

    def login(self, username, password):  # noqa: D102
        return True

    def logout(self):  # noqa: D102
        return None


@pytest.fixture()
def dialog_geometry(tmp_path, qapp):
    """加载 LoginDialog 并返回实测几何（弹窗坐标）。"""
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    wrapper = tmp_path / "Probe.qml"
    wrapper.write_text(
        _WRAPPER.format(components=QML_COMPONENTS.as_posix()), encoding="utf-8"
    )

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_COMPONENTS))
    engine.rootContext().setContextProperty("authManager", _FakeAuth())
    engine.load(QUrl.fromLocalFile(str(wrapper)))

    roots = engine.rootObjects()
    assert roots, "Probe.qml 加载失败"
    window = roots[0]

    deadline = time.time() + 5.0
    while time.time() < deadline and window.property("report") is None:
        qapp.processEvents()
        time.sleep(0.01)

    report = window.property("report")
    assert report is not None, "未能取到弹窗几何"
    data = report.toVariant()
    assert "error" not in data, data
    return data


def test_dialog_content_fills_the_popup(dialog_geometry) -> None:
    assert dialog_geometry["padding"] == 0, "Popup 默认 padding 未清零，内容区会内缩"
    assert dialog_geometry["contentX"] == 0
    assert dialog_geometry["contentY"] == 0


def test_footer_aligns_with_dialog_edges(dialog_geometry) -> None:
    assert dialog_geometry["footerX"] == 0, "底部按钮区左侧未与对话框对齐"
    assert dialog_geometry["footerW"] == dialog_geometry["popupW"], (
        "底部按钮区宽度与对话框不一致"
    )
    assert dialog_geometry["footerBottom"] == dialog_geometry["popupH"], (
        "底部按钮区底边未与对话框底边对齐"
    )
