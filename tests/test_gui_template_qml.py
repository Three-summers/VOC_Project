"""GUI_Template QML 冒烟测试

- Date: 2026-01-16
- Executor: Codex

目的：
1) 验证 `GUI_Template/qml/main.qml` 可在 offscreen 环境下解析并创建根对象
2) 为跨项目复制提供最小“可加载”保障
"""

import os
import unittest
from pathlib import Path

# 必须在导入 PySide6 之前设置（否则 Qt 平台插件可能初始化失败）
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent


_app = None


def get_app() -> QGuiApplication:
    """获取或创建全局 QGuiApplication 实例（QML 测试需要）"""
    global _app
    if _app is None:
        _app = QGuiApplication.instance()
        if _app is None:
            _app = QGuiApplication([])
    return _app


class TestGuiTemplateQml(unittest.TestCase):
    def test_template_main_qml_loads(self):
        app = get_app()
        _ = app  # 避免 lint/类型工具误报未使用

        root_dir = Path(__file__).resolve().parents[1]
        qml_path = (root_dir / "GUI_Template" / "qml" / "main.qml").resolve()
        self.assertTrue(qml_path.exists(), f"模板 main.qml 不存在: {qml_path}")

        engine = QQmlApplicationEngine()
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_path)))

        if component.status() == QQmlComponent.Error:
            errors = [e.toString() for e in component.errors()]
            self.fail(f"QML 解析失败: {errors}")

        obj = component.create()
        self.assertIsNotNone(obj, "QML 根对象创建失败")

        obj.deleteLater()
        engine.deleteLater()

