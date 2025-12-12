"""测试 logging_config 模块"""
import json
import logging
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 重置模块状态以便测试
import voc_app.logging_config as logging_config_module


class TestLoggingConfig(unittest.TestCase):
    """logging_config 模块测试"""

    def setUp(self) -> None:
        # 每次测试前重置模块状态
        logging_config_module.reset()

    def tearDown(self) -> None:
        # 清理
        logging_config_module.reset()

    def test_get_logger_basic(self) -> None:
        """测试基本的 get_logger 功能"""
        logger = logging_config_module.get_logger("test_module")
        self.assertIsInstance(logger, logging.Logger)
        self.assertIn("voc_app", logger.name)

    def test_get_logger_caching(self) -> None:
        """测试 logger 缓存"""
        logger1 = logging_config_module.get_logger("cached_module")
        logger2 = logging_config_module.get_logger("cached_module")
        self.assertIs(logger1, logger2)

    def test_get_logger_voc_app_prefix(self) -> None:
        """测试 voc_app 前缀的日志器"""
        logger = logging_config_module.get_logger("voc_app.gui.test")
        self.assertEqual(logger.name, "voc_app.gui.test")

    def test_get_logger_without_prefix(self) -> None:
        """测试无前缀的日志器会自动添加 voc_app 前缀"""
        logger = logging_config_module.get_logger("my_module")
        self.assertEqual(logger.name, "voc_app.my_module")

    def test_setup_logging_console(self) -> None:
        """测试控制台日志配置"""
        root_logger = logging_config_module.setup_logging(
            level=logging.DEBUG, console=True
        )
        self.assertIsInstance(root_logger, logging.Logger)
        self.assertEqual(root_logger.level, logging.DEBUG)
        # 检查是否有 StreamHandler
        has_stream_handler = any(
            isinstance(h, logging.StreamHandler) for h in root_logger.handlers
        )
        self.assertTrue(has_stream_handler)

    def test_setup_logging_file(self) -> None:
        """测试文件日志配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            # 重置状态
            logging_config_module.reset()

            root_logger = logging_config_module.setup_logging(
                level=logging.INFO, log_file=log_file, console=False
            )
            # 检查是否有 FileHandler
            has_file_handler = any(
                isinstance(h, logging.FileHandler) for h in root_logger.handlers
            )
            self.assertTrue(has_file_handler)
            self.assertTrue(log_file.exists())

    def test_setup_logging_no_duplicate_handlers(self) -> None:
        """测试不会重复添加 handlers"""
        logging_config_module.setup_logging(level=logging.INFO, console=True)
        handler_count_1 = len(logging.getLogger("voc_app").handlers)

        logging_config_module.setup_logging(level=logging.INFO, console=True)
        handler_count_2 = len(logging.getLogger("voc_app").handlers)

        self.assertEqual(handler_count_1, handler_count_2)

    def test_set_level(self) -> None:
        """测试动态设置日志级别"""
        logging_config_module.setup_logging(level=logging.INFO, console=True)
        logging_config_module.set_level(logging.DEBUG)

        root_logger = logging.getLogger("voc_app")
        self.assertEqual(root_logger.level, logging.DEBUG)

    def test_set_level_string(self) -> None:
        """测试使用字符串设置日志级别"""
        logging_config_module.setup_logging(level="INFO", console=True)
        logging_config_module.set_level("DEBUG")

        root_logger = logging.getLogger("voc_app")
        self.assertEqual(root_logger.level, logging.DEBUG)

    def test_log_level_constants(self) -> None:
        """测试日志级别常量"""
        self.assertEqual(logging_config_module.DEBUG, logging.DEBUG)
        self.assertEqual(logging_config_module.INFO, logging.INFO)
        self.assertEqual(logging_config_module.WARNING, logging.WARNING)
        self.assertEqual(logging_config_module.ERROR, logging.ERROR)
        self.assertEqual(logging_config_module.CRITICAL, logging.CRITICAL)

    def test_logger_output(self) -> None:
        """测试日志输出"""
        import io

        # 创建一个内存流来捕获日志
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))

        root_logger = logging.getLogger("voc_app")
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)

        logger = logging_config_module.get_logger("test_output")
        logger.info("测试消息")

        output = stream.getvalue()
        self.assertIn("INFO", output)
        self.assertIn("测试消息", output)


class TestModuleLevelConfig(unittest.TestCase):
    """测试模块级别配置功能"""

    def setUp(self) -> None:
        logging_config_module.reset()

    def tearDown(self) -> None:
        logging_config_module.reset()

    def test_set_module_level(self) -> None:
        """测试设置单个模块级别"""
        logging_config_module.setup_logging(level=logging.INFO, console=False)
        logging_config_module.set_module_level("voc_app.gui", logging.WARNING)

        gui_logger = logging.getLogger("voc_app.gui")
        self.assertEqual(gui_logger.level, logging.WARNING)

    def test_set_module_level_string(self) -> None:
        """测试使用字符串设置模块级别"""
        logging_config_module.setup_logging(level="INFO", console=False)
        logging_config_module.set_module_level("voc_app.gui", "ERROR")

        gui_logger = logging.getLogger("voc_app.gui")
        self.assertEqual(gui_logger.level, logging.ERROR)

    def test_configure_levels(self) -> None:
        """测试批量配置模块级别"""
        logging_config_module.setup_logging(level=logging.INFO, console=False)
        logging_config_module.configure_levels({
            "voc_app": "INFO",
            "voc_app.gui": "WARNING",
            "voc_app.loadport": "DEBUG",
        })

        root_logger = logging.getLogger("voc_app")
        gui_logger = logging.getLogger("voc_app.gui")
        loadport_logger = logging.getLogger("voc_app.loadport")

        self.assertEqual(root_logger.level, logging.INFO)
        self.assertEqual(gui_logger.level, logging.WARNING)
        self.assertEqual(loadport_logger.level, logging.DEBUG)

    def test_configure_from_file(self) -> None:
        """测试从文件加载配置"""
        logging_config_module.setup_logging(level=logging.INFO, console=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "logging.json"
            config = {
                "levels": {
                    "voc_app": "WARNING",
                    "voc_app.gui": "ERROR",
                }
            }
            with open(config_file, "w") as f:
                json.dump(config, f)

            result = logging_config_module.configure_from_file(config_file)
            self.assertTrue(result)

            gui_logger = logging.getLogger("voc_app.gui")
            self.assertEqual(gui_logger.level, logging.ERROR)

    def test_configure_from_file_not_exists(self) -> None:
        """测试从不存在的文件加载配置"""
        result = logging_config_module.configure_from_file("/nonexistent/path.json")
        self.assertFalse(result)

    def test_configure_from_file_invalid_json(self) -> None:
        """测试从无效 JSON 文件加载配置"""
        logging_config_module.setup_logging(level=logging.INFO, console=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "invalid.json"
            with open(config_file, "w") as f:
                f.write("invalid json {{{")

            result = logging_config_module.configure_from_file(config_file)
            self.assertFalse(result)

    def test_get_current_config(self) -> None:
        """测试获取当前配置"""
        logging_config_module.setup_logging(level=logging.INFO, console=True)
        logging_config_module.set_module_level("voc_app.gui", "WARNING")

        config = logging_config_module.get_current_config()

        self.assertIn("global_level", config)
        self.assertIn("module_levels", config)
        self.assertIn("initialized", config)
        self.assertTrue(config["initialized"])
        self.assertIn("voc_app.gui", config["module_levels"])

    def test_reset(self) -> None:
        """测试重置配置"""
        logging_config_module.setup_logging(level=logging.DEBUG, console=True)
        logging_config_module.set_module_level("voc_app.gui", "ERROR")

        logging_config_module.reset()

        config = logging_config_module.get_current_config()
        self.assertFalse(config["initialized"])
        self.assertEqual(len(config["module_levels"]), 0)


class TestParseLevels(unittest.TestCase):
    """测试级别解析功能"""

    def test_parse_level_int(self) -> None:
        """测试整数级别"""
        self.assertEqual(logging_config_module._parse_level(10), 10)
        self.assertEqual(logging_config_module._parse_level(20), 20)

    def test_parse_level_string(self) -> None:
        """测试字符串级别"""
        self.assertEqual(logging_config_module._parse_level("DEBUG"), logging.DEBUG)
        self.assertEqual(logging_config_module._parse_level("INFO"), logging.INFO)
        self.assertEqual(logging_config_module._parse_level("WARNING"), logging.WARNING)
        self.assertEqual(logging_config_module._parse_level("WARN"), logging.WARNING)
        self.assertEqual(logging_config_module._parse_level("ERROR"), logging.ERROR)
        self.assertEqual(logging_config_module._parse_level("CRITICAL"), logging.CRITICAL)
        self.assertEqual(logging_config_module._parse_level("FATAL"), logging.CRITICAL)

    def test_parse_level_case_insensitive(self) -> None:
        """测试大小写不敏感"""
        self.assertEqual(logging_config_module._parse_level("debug"), logging.DEBUG)
        self.assertEqual(logging_config_module._parse_level("Info"), logging.INFO)
        self.assertEqual(logging_config_module._parse_level("WARNING"), logging.WARNING)

    def test_parse_level_invalid(self) -> None:
        """测试无效级别返回 INFO"""
        self.assertEqual(logging_config_module._parse_level("invalid"), logging.INFO)


class TestFormatConstants(unittest.TestCase):
    """测试格式常量"""

    def test_format_constants(self) -> None:
        """测试格式常量存在"""
        self.assertIsInstance(logging_config_module.FORMAT_DEFAULT, str)
        self.assertIsInstance(logging_config_module.FORMAT_SIMPLE, str)
        self.assertIsInstance(logging_config_module.FORMAT_DETAILED, str)

    def test_format_detailed_has_filename(self) -> None:
        """测试详细格式包含文件名"""
        self.assertIn("filename", logging_config_module.FORMAT_DETAILED)
        self.assertIn("lineno", logging_config_module.FORMAT_DETAILED)


if __name__ == "__main__":
    unittest.main()
