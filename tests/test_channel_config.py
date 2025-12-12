"""测试 channel_config 模块"""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.channel_config import (
    ChannelPreset,
    PrefixPreset,
    PrefixRegistry,
    ChannelConfig,
    ChannelConfigManager,
    DEFAULT_PREFIX_BY_CHANNEL,
)


class TestChannelPreset(unittest.TestCase):
    """测试 ChannelPreset 数据类"""

    def test_create_preset(self) -> None:
        """测试创建预设"""
        preset = ChannelPreset(
            title="Test",
            unit="ppb",
            ooc_upper=100.0,
            ooc_lower=10.0,
            oos_upper=120.0,
            oos_lower=5.0,
            target=50.0,
        )
        self.assertEqual(preset.title, "Test")
        self.assertEqual(preset.unit, "ppb")
        self.assertEqual(preset.ooc_upper, 100.0)

    def test_default_show_flags(self) -> None:
        """测试默认显示标志"""
        preset = ChannelPreset(
            title="Test",
            unit="",
            ooc_upper=80.0,
            ooc_lower=20.0,
            oos_upper=90.0,
            oos_lower=10.0,
            target=50.0,
        )
        self.assertTrue(preset.show_ooc_upper)
        self.assertTrue(preset.show_ooc_lower)
        self.assertTrue(preset.show_oos_upper)
        self.assertTrue(preset.show_oos_lower)
        self.assertTrue(preset.show_target)


class TestPrefixPreset(unittest.TestCase):
    """测试 PrefixPreset 数据类"""

    def test_get_channel_preset_valid_index(self) -> None:
        """测试获取有效索引的通道预设"""
        ch1 = ChannelPreset(
            title="CH1", unit="ppb", ooc_upper=100, ooc_lower=0, oos_upper=150, oos_lower=0, target=50
        )
        ch2 = ChannelPreset(
            title="CH2", unit="dB", ooc_upper=80, ooc_lower=0, oos_upper=90, oos_lower=0, target=60
        )
        preset = PrefixPreset(prefix="TEST", display_name="Test", channel_count=2, channels=[ch1, ch2])

        self.assertEqual(preset.get_channel_preset(0).title, "CH1")
        self.assertEqual(preset.get_channel_preset(1).title, "CH2")

    def test_get_channel_preset_out_of_range(self) -> None:
        """测试超出范围的索引返回最后一个通道"""
        ch1 = ChannelPreset(
            title="CH1", unit="ppb", ooc_upper=100, ooc_lower=0, oos_upper=150, oos_lower=0, target=50
        )
        preset = PrefixPreset(prefix="TEST", display_name="Test", channel_count=1, channels=[ch1])

        # 超出范围返回最后一个
        result = preset.get_channel_preset(5)
        self.assertEqual(result.title, "CH1")

    def test_get_channel_preset_empty_channels(self) -> None:
        """测试空通道列表时返回默认值"""
        preset = PrefixPreset(prefix="TEST", display_name="Test", channel_count=0, channels=[])
        result = preset.get_channel_preset(0)
        self.assertIn("通道", result.title)


class TestPrefixRegistry(unittest.TestCase):
    """测试 PrefixRegistry 类"""

    def test_get_preset_voc(self) -> None:
        """测试获取 VOC 预设"""
        preset = PrefixRegistry.get_preset("VOC")
        self.assertEqual(preset.prefix, "VOC")
        self.assertEqual(preset.display_name, "VOC 监测")
        self.assertEqual(preset.channel_count, 1)

    def test_get_preset_noise_humility(self) -> None:
        """测试获取 NOISE_HUMILITY 预设"""
        preset = PrefixRegistry.get_preset("NOISE_HUMILITY")
        self.assertEqual(preset.prefix, "NOISE_HUMILITY")
        self.assertEqual(preset.channel_count, 3)

    def test_get_preset_case_insensitive(self) -> None:
        """测试大小写不敏感"""
        preset1 = PrefixRegistry.get_preset("voc")
        preset2 = PrefixRegistry.get_preset("VOC")
        preset3 = PrefixRegistry.get_preset("Voc")
        self.assertEqual(preset1.prefix, preset2.prefix)
        self.assertEqual(preset2.prefix, preset3.prefix)

    def test_get_preset_unknown(self) -> None:
        """测试获取未知前缀返回默认预设"""
        preset = PrefixRegistry.get_preset("UNKNOWN_TYPE")
        self.assertEqual(preset.prefix, "UNKNOWN")
        self.assertEqual(preset.display_name, "未知类型")

    def test_get_preset_by_channel_count(self) -> None:
        """测试根据通道数获取预设"""
        preset1 = PrefixRegistry.get_preset_by_channel_count(1)
        self.assertEqual(preset1.prefix, "VOC")

        preset3 = PrefixRegistry.get_preset_by_channel_count(3)
        self.assertEqual(preset3.prefix, "NOISE_HUMILITY")

    def test_get_preset_by_unknown_channel_count(self) -> None:
        """测试未知通道数返回默认预设"""
        preset = PrefixRegistry.get_preset_by_channel_count(99)
        self.assertEqual(preset.prefix, "UNKNOWN")

    def test_get_default_prefix(self) -> None:
        """测试获取默认前缀"""
        self.assertEqual(PrefixRegistry.get_default_prefix(1), "VOC")
        self.assertEqual(PrefixRegistry.get_default_prefix(3), "NOISE_HUMILITY")
        self.assertEqual(PrefixRegistry.get_default_prefix(99), "UNKNOWN")


class TestChannelConfig(unittest.TestCase):
    """测试 ChannelConfig 数据类"""

    def test_default_values(self) -> None:
        """测试默认值"""
        config = ChannelConfig()
        self.assertEqual(config.title, "")
        self.assertEqual(config.unit, "")
        self.assertEqual(config.ooc_upper, 80.0)
        self.assertEqual(config.ooc_lower, 20.0)
        self.assertEqual(config.target, 50.0)

    def test_to_dict(self) -> None:
        """测试转换为字典"""
        config = ChannelConfig(title="Test", unit="ppb", ooc_upper=100.0)
        d = config.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["title"], "Test")
        self.assertEqual(d["unit"], "ppb")
        self.assertEqual(d["ooc_upper"], 100.0)

    def test_from_dict(self) -> None:
        """测试从字典创建"""
        data = {
            "title": "Test Channel",
            "unit": "dB",
            "ooc_upper": 70.0,
            "ooc_lower": 30.0,
            "oos_upper": 80.0,
            "oos_lower": 20.0,
            "target": 50.0,
            "show_ooc_upper": False,
        }
        config = ChannelConfig.from_dict(data)
        self.assertEqual(config.title, "Test Channel")
        self.assertEqual(config.unit, "dB")
        self.assertEqual(config.ooc_upper, 70.0)
        self.assertFalse(config.show_ooc_upper)

    def test_from_dict_with_missing_keys(self) -> None:
        """测试从不完整字典创建"""
        data = {"title": "Partial"}
        config = ChannelConfig.from_dict(data)
        self.assertEqual(config.title, "Partial")
        self.assertEqual(config.ooc_upper, 80.0)  # 默认值

    def test_from_preset(self) -> None:
        """测试从预设创建"""
        preset = ChannelPreset(
            title="VOC",
            unit="ppb",
            ooc_upper=3000.0,
            ooc_lower=0.0,
            oos_upper=5000.0,
            oos_lower=0.0,
            target=1000.0,
            show_ooc_lower=False,
        )
        config = ChannelConfig.from_preset(preset)
        self.assertEqual(config.title, "VOC")
        self.assertEqual(config.unit, "ppb")
        self.assertEqual(config.ooc_upper, 3000.0)
        self.assertFalse(config.show_ooc_lower)


class TestChannelConfigManager(unittest.TestCase):
    """测试 ChannelConfigManager 类"""

    def setUp(self) -> None:
        # 使用临时文件
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = Path(self.tmpdir) / "test_config.json"
        self.manager = ChannelConfigManager(self.config_path)

    def tearDown(self) -> None:
        # 确保定时器被取消
        with self.manager._save_lock:
            if self.manager._save_timer is not None:
                self.manager._save_timer.cancel()
        # 清理临时文件
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_set_prefix(self) -> None:
        """测试设置前缀"""
        self.manager.set_prefix("VOC", 1)
        self.assertEqual(self.manager.get_prefix(), "VOC")

    def test_set_prefix_uppercase(self) -> None:
        """测试前缀自动转大写"""
        self.manager.set_prefix("voc", 1)
        self.assertEqual(self.manager.get_prefix(), "VOC")

    def test_has_prefix(self) -> None:
        """测试检查前缀是否存在"""
        self.assertFalse(self.manager.has_prefix("VOC"))
        self.manager.set_prefix("VOC", 1)
        self.assertTrue(self.manager.has_prefix("VOC"))
        self.assertTrue(self.manager.has_prefix("voc"))  # 大小写不敏感

    def test_get_channel_config(self) -> None:
        """测试获取通道配置"""
        self.manager.set_prefix("VOC", 1)
        config = self.manager.get(0)
        self.assertIsInstance(config, ChannelConfig)
        # VOC 预设的标题应该是 "VOC"
        self.assertEqual(config.title, "VOC")

    def test_get_creates_default_if_missing(self) -> None:
        """测试获取不存在的通道会创建默认配置"""
        self.manager.set_prefix("TEST", 2)
        # 通道 5 不存在
        config = self.manager.get(5)
        self.assertIn("通道", config.title)

    def test_set_channel_config(self) -> None:
        """测试设置通道配置"""
        self.manager.set_prefix("VOC", 1)
        new_config = ChannelConfig(title="Custom", unit="custom")
        self.manager.set(0, new_config)
        config = self.manager.get(0)
        self.assertEqual(config.title, "Custom")
        self.assertEqual(config.unit, "custom")

    def test_update_channel_config(self) -> None:
        """测试更新通道配置"""
        self.manager.set_prefix("VOC", 1)
        self.manager.update(0, title="Updated Title", ooc_upper=999.0)
        config = self.manager.get(0)
        self.assertEqual(config.title, "Updated Title")
        self.assertEqual(config.ooc_upper, 999.0)

    def test_save_and_load(self) -> None:
        """测试保存和加载"""
        self.manager.set_prefix("VOC", 1)
        self.manager.update(0, title="Saved Config")
        self.manager.save()  # 立即保存

        # 创建新的管理器加载配置
        new_manager = ChannelConfigManager(self.config_path)
        new_manager.set_prefix("VOC", 1)
        config = new_manager.get(0)
        self.assertEqual(config.title, "Saved Config")

    def test_debounced_save(self) -> None:
        """测试防抖保存"""
        self.manager.set_prefix("VOC", 1)
        self.manager.update(0, title="Test1")
        self.manager.update(0, title="Test2")
        self.manager.update(0, title="Test3")

        # 立即检查文件应该还没保存
        self.assertFalse(self.config_path.exists())

        # 等待防抖延迟
        time.sleep(self.manager.SAVE_DELAY + 0.5)
        self.assertTrue(self.config_path.exists())

    def test_flush(self) -> None:
        """测试强制刷新"""
        self.manager.set_prefix("VOC", 1)
        self.manager.update(0, title="Flushed")
        self.manager.flush()
        self.assertTrue(self.config_path.exists())

    def test_backup_on_save(self) -> None:
        """测试保存时创建备份"""
        self.manager.set_prefix("VOC", 1)
        self.manager.save()

        # 再次保存应该创建备份
        self.manager.update(0, title="New")
        self.manager.save()

        backup_path = self.config_path.with_suffix(".json.bak")
        self.assertTrue(backup_path.exists())

    def test_load_invalid_json(self) -> None:
        """测试加载无效 JSON"""
        # 写入无效 JSON
        with open(self.config_path, "w") as f:
            f.write("invalid json {{{")

        # 应该不会崩溃，只是使用默认配置
        manager = ChannelConfigManager(self.config_path)
        self.assertEqual(manager.get_prefix(), "")


class TestDefaultPrefixByChannel(unittest.TestCase):
    """测试 DEFAULT_PREFIX_BY_CHANNEL 常量"""

    def test_mapping(self) -> None:
        """测试通道数到前缀的映射"""
        self.assertEqual(DEFAULT_PREFIX_BY_CHANNEL.get(1), "VOC")
        self.assertEqual(DEFAULT_PREFIX_BY_CHANNEL.get(3), "NOISE_HUMILITY")


if __name__ == "__main__":
    unittest.main()
