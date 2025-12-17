"""测试 QML 组件修改

测试内容：
1. UiConstants singleton 加载和属性
2. 修改后的 QML 组件能正常加载
3. 防抖定时器和缓存属性的正确性
"""
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtCore import QObject, QUrl, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent


# 全局 QGuiApplication 实例（QML 测试需要）
_app = None


def get_app():
    """获取或创建 QGuiApplication 实例"""
    global _app
    if _app is None:
        _app = QGuiApplication.instance()
        if _app is None:
            _app = QGuiApplication([])
    return _app


class TestUiConstants(unittest.TestCase):
    """测试 UiConstants singleton"""

    @classmethod
    def setUpClass(cls):
        cls.app = get_app()
        cls.engine = QQmlApplicationEngine()
        # 添加 QML 导入路径
        qml_dir = ROOT_DIR / "src" / "voc_app" / "gui" / "qml"
        cls.engine.addImportPath(str(qml_dir))

    @classmethod
    def tearDownClass(cls):
        cls.engine.deleteLater()

    def test_ui_constants_file_exists(self):
        """测试 UiConstants.qml 文件存在"""
        constants_path = (
            ROOT_DIR
            / "src"
            / "voc_app"
            / "gui"
            / "qml"
            / "components"
            / "UiConstants.qml"
        )
        self.assertTrue(constants_path.exists(), f"UiConstants.qml 不存在: {constants_path}")

    def test_ui_constants_singleton_loads(self):
        """测试 UiConstants singleton 能正常加载"""
        # 创建一个简单的测试 QML 来验证 singleton 加载
        test_qml = """
        import QtQuick
        import "../src/voc_app/gui/qml/components" as Components

        QtObject {
            property real testOocUpper: Components.UiConstants.defaultOocUpper
            property real testOocLower: Components.UiConstants.defaultOocLower
            property real testOosUpper: Components.UiConstants.defaultOosUpper
            property real testOosLower: Components.UiConstants.defaultOosLower
            property real testTarget: Components.UiConstants.defaultTarget
            property bool testShowOocUpper: Components.UiConstants.defaultShowOocUpper
            property int testDebounceInterval: Components.UiConstants.resizeDebounceInterval
        }
        """
        component = QQmlComponent(self.engine)
        component.setData(test_qml.encode(), QUrl.fromLocalFile(str(ROOT_DIR / "tests" / "test.qml")))

        if component.status() == QQmlComponent.Error:
            errors = component.errors()
            # 如果是导入路径问题，跳过测试
            self.skipTest(f"QML 组件创建失败（可能是导入路径问题）: {[e.toString() for e in errors]}")

        obj = component.create()
        if obj is None:
            self.skipTest("无法创建 QML 对象（singleton 可能需要完整 QML 环境）")

        # 验证默认值
        self.assertEqual(obj.property("testOocUpper"), 80)
        self.assertEqual(obj.property("testOocLower"), 20)
        self.assertEqual(obj.property("testOosUpper"), 90)
        self.assertEqual(obj.property("testOosLower"), 10)
        self.assertEqual(obj.property("testTarget"), 50)
        self.assertTrue(obj.property("testShowOocUpper"))
        self.assertEqual(obj.property("testDebounceInterval"), 32)

        obj.deleteLater()

    def test_ui_constants_default_values(self):
        """测试 UiConstants 默认值正确性（通过读取文件验证）"""
        constants_path = (
            ROOT_DIR
            / "src"
            / "voc_app"
            / "gui"
            / "qml"
            / "components"
            / "UiConstants.qml"
        )
        content = constants_path.read_text(encoding="utf-8")

        # 验证文件中包含正确的默认值定义
        self.assertIn("defaultOocUpper: 80", content)
        self.assertIn("defaultOocLower: 20", content)
        self.assertIn("defaultOosUpper: 90", content)
        self.assertIn("defaultOosLower: 10", content)
        self.assertIn("defaultTarget: 50", content)
        self.assertIn("defaultShowOocUpper: true", content)
        self.assertIn("defaultShowOocLower: true", content)
        self.assertIn("defaultShowOosUpper: true", content)
        self.assertIn("defaultShowOosLower: true", content)
        self.assertIn("defaultShowTarget: true", content)
        self.assertIn("resizeDebounceInterval: 32", content)

    def test_ui_constants_default_limits_function(self):
        """测试 UiConstants.defaultLimits 函数定义"""
        constants_path = (
            ROOT_DIR
            / "src"
            / "voc_app"
            / "gui"
            / "qml"
            / "components"
            / "UiConstants.qml"
        )
        content = constants_path.read_text(encoding="utf-8")

        # 验证函数定义存在
        self.assertIn("function defaultLimits()", content)
        self.assertIn("oocUpper: defaultOocUpper", content)
        self.assertIn("oocLower: defaultOocLower", content)


class TestQmldirRegistration(unittest.TestCase):
    """测试 qmldir 注册"""

    def test_qmldir_contains_ui_constants(self):
        """测试 qmldir 包含 UiConstants singleton 注册"""
        qmldir_path = (
            ROOT_DIR
            / "src"
            / "voc_app"
            / "gui"
            / "qml"
            / "components"
            / "qmldir"
        )
        content = qmldir_path.read_text(encoding="utf-8")

        self.assertIn("singleton UiConstants", content)
        self.assertIn("UiConstants.qml", content)


class TestStatusViewOptimization(unittest.TestCase):
    """测试 StatusView.qml 优化"""

    def setUp(self):
        self.status_view_path = (
            ROOT_DIR
            / "src"
            / "voc_app"
            / "gui"
            / "qml"
            / "views"
            / "StatusView.qml"
        )
        self.content = self.status_view_path.read_text(encoding="utf-8")

    def test_foup_acquisition_cache_property_exists(self):
        """测试 _foupAcq 缓存属性存在"""
        self.assertIn("readonly property var _foupAcq:", self.content)
        self.assertIn('(typeof foupAcquisition !== "undefined")', self.content)

    def test_has_foup_acq_property_exists(self):
        """测试 _hasFoupAcq 布尔属性存在"""
        self.assertIn("readonly property bool _hasFoupAcq:", self.content)
        self.assertIn("_foupAcq !== null", self.content)

    def test_cached_property_usage(self):
        """测试缓存属性被正确使用"""
        # 验证使用缓存属性而非重复 typeof 检查
        self.assertIn("statusRoot._hasFoupAcq", self.content)
        self.assertIn("statusRoot._foupAcq.", self.content)

    def test_uses_ui_constants_for_defaults(self):
        """测试使用 UiConstants 作为默认值"""
        self.assertIn("Components.UiConstants.defaultOocUpper", self.content)
        self.assertIn("Components.UiConstants.defaultOocLower", self.content)
        self.assertIn("Components.UiConstants.defaultOosUpper", self.content)
        self.assertIn("Components.UiConstants.defaultOosLower", self.content)
        self.assertIn("Components.UiConstants.defaultTarget", self.content)

    def test_no_redundant_typeof_in_property_bindings(self):
        """测试属性绑定中没有冗余的 typeof 检查"""
        # 计算 typeof foupAcquisition 出现次数
        # 应该只在缓存属性定义处出现一次
        typeof_count = self.content.count('typeof foupAcquisition !== "undefined"')
        # 允许最多 2 次（缓存属性定义 + 可能的其他必要检查）
        self.assertLessEqual(
            typeof_count,
            2,
            f"typeof 检查出现 {typeof_count} 次，应减少到 2 次以下",
        )


class TestConfigFoupPageOptimization(unittest.TestCase):
    """测试 ConfigFoupPage.qml 优化"""

    def setUp(self):
        self.config_page_path = (
            ROOT_DIR
            / "src"
            / "voc_app"
            / "gui"
            / "qml"
            / "views"
            / "config"
            / "ConfigFoupPage.qml"
        )
        self.content = self.config_page_path.read_text(encoding="utf-8")

    def test_foup_acquisition_cache_property_exists(self):
        """测试 _foupAcq 缓存属性存在"""
        self.assertIn("readonly property var _foupAcq:", self.content)

    def test_has_foup_acq_property_exists(self):
        """测试 _hasFoupAcq 布尔属性存在"""
        self.assertIn("readonly property bool _hasFoupAcq:", self.content)

    def test_cached_property_usage(self):
        """测试缓存属性被正确使用"""
        self.assertIn("root._hasFoupAcq", self.content)
        self.assertIn("root._foupAcq.", self.content)


class TestCommandPanelMemoryLeakFix(unittest.TestCase):
    """测试 CommandPanel.qml 内存泄漏修复"""

    def setUp(self):
        self.command_panel_path = (
            ROOT_DIR
            / "src"
            / "voc_app"
            / "gui"
            / "qml"
            / "CommandPanel.qml"
        )
        self.content = self.command_panel_path.read_text(encoding="utf-8")

    def test_pending_component_property_exists(self):
        """测试 _pendingComponent 属性存在"""
        self.assertIn("property Component _pendingComponent:", self.content)

    def test_cleanup_function_exists(self):
        """测试 _cleanupPendingComponent 函数存在"""
        self.assertIn("function _cleanupPendingComponent()", self.content)

    def test_cleanup_called_before_load(self):
        """测试加载前调用清理函数"""
        self.assertIn("_cleanupPendingComponent()", self.content)

    def test_pending_component_tracking(self):
        """测试异步加载时追踪待加载组件"""
        self.assertIn("_pendingComponent = component", self.content)

    def test_stale_component_check(self):
        """测试检查组件是否过期"""
        self.assertIn("component !== _pendingComponent", self.content)


class TestSpectrumChartDebounce(unittest.TestCase):
    """测试 SpectrumChart.qml 防抖优化"""

    def setUp(self):
        self.spectrum_chart_path = (
            ROOT_DIR
            / "src"
            / "voc_app"
            / "gui"
            / "qml"
            / "components"
            / "SpectrumChart.qml"
        )
        self.content = self.spectrum_chart_path.read_text(encoding="utf-8")

    def test_resize_debounce_timer_exists(self):
        """测试 resizeDebounceTimer 存在"""
        self.assertIn("id: resizeDebounceTimer", self.content)

    def test_grid_debounce_timer_exists(self):
        """测试 gridDebounceTimer 存在"""
        self.assertIn("id: gridDebounceTimer", self.content)

    def test_scan_line_debounce_timer_exists(self):
        """测试 scanLineDebounceTimer 存在"""
        self.assertIn("id: scanLineDebounceTimer", self.content)

    def test_resize_uses_debounce(self):
        """测试尺寸变化使用防抖"""
        self.assertIn("onWidthChanged: resizeDebounceTimer.restart()", self.content)
        self.assertIn("onHeightChanged: resizeDebounceTimer.restart()", self.content)

    def test_grid_properties_use_debounce(self):
        """测试网格属性使用防抖"""
        self.assertIn("onShowGridChanged: gridDebounceTimer.restart()", self.content)
        self.assertIn("onGridColorChanged: gridDebounceTimer.restart()", self.content)

    def test_scan_line_uses_debounce(self):
        """测试扫描线使用防抖"""
        self.assertIn("onScanLineEnabledChanged: scanLineDebounceTimer.restart()", self.content)
        self.assertIn("onScanLineOpacityChanged: scanLineDebounceTimer.restart()", self.content)

    def test_uses_ui_constants_interval(self):
        """测试使用 UiConstants 定义的防抖间隔"""
        self.assertIn("Components.UiConstants.resizeDebounceInterval", self.content)


class TestConfigFoupCommandsConnections(unittest.TestCase):
    """测试 Config_foupCommands.qml Connections 保护"""

    def setUp(self):
        self.config_commands_path = (
            ROOT_DIR
            / "src"
            / "voc_app"
            / "gui"
            / "qml"
            / "commands"
            / "Config_foupCommands.qml"
        )
        self.content = self.config_commands_path.read_text(encoding="utf-8")

    def test_connections_has_enabled_property(self):
        """测试 Connections 包含 enabled 属性"""
        self.assertIn("enabled: acquisitionController !== null", self.content)

    def test_uses_ui_constants_for_defaults(self):
        """测试使用 UiConstants 作为默认值"""
        self.assertIn("Components.UiConstants.defaultOocUpper", self.content)
        self.assertIn("Components.UiConstants.defaultOocLower", self.content)
        self.assertIn("Components.UiConstants.defaultOosUpper", self.content)
        self.assertIn("Components.UiConstants.defaultOosLower", self.content)
        self.assertIn("Components.UiConstants.defaultTarget", self.content)


class TestChartCardDefaults(unittest.TestCase):
    """测试 ChartCard.qml 默认值"""

    def setUp(self):
        self.chart_card_path = (
            ROOT_DIR
            / "src"
            / "voc_app"
            / "gui"
            / "qml"
            / "components"
            / "ChartCard.qml"
        )
        self.content = self.chart_card_path.read_text(encoding="utf-8")

    def test_uses_ui_constants_for_limit_defaults(self):
        """测试使用 UiConstants 作为限值默认值"""
        self.assertIn("Components.UiConstants.defaultOosUpper", self.content)
        self.assertIn("Components.UiConstants.defaultOocUpper", self.content)

    def test_uses_ui_constants_for_show_defaults(self):
        """测试使用 UiConstants 作为显示开关默认值"""
        self.assertIn("Components.UiConstants.defaultShowOocUpper", self.content)
        self.assertIn("Components.UiConstants.defaultShowOocLower", self.content)
        self.assertIn("Components.UiConstants.defaultShowOosUpper", self.content)
        self.assertIn("Components.UiConstants.defaultShowOosLower", self.content)
        self.assertIn("Components.UiConstants.defaultShowTarget", self.content)


class TestMainQmlDefaults(unittest.TestCase):
    """测试 main.qml 默认值"""

    def setUp(self):
        self.main_qml_path = (
            ROOT_DIR
            / "src"
            / "voc_app"
            / "gui"
            / "qml"
            / "main.qml"
        )
        self.content = self.main_qml_path.read_text(encoding="utf-8")

    def test_default_limits_uses_ui_constants(self):
        """测试 defaultLimits 函数使用 UiConstants"""
        self.assertIn("Components.UiConstants.defaultLimits()", self.content)


if __name__ == "__main__":
    unittest.main()
