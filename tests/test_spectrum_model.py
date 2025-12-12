"""测试 spectrum_model 模块"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.spectrum_model import SpectrumDataModel, SpectrumSimulator


class TestSpectrumDataModel(unittest.TestCase):
    """测试 SpectrumDataModel 类"""

    def setUp(self) -> None:
        self.model = SpectrumDataModel(bin_count=256)

    def test_init_default_bin_count(self) -> None:
        """测试默认 bin 数量"""
        model = SpectrumDataModel()
        self.assertEqual(model.binCount, 256)

    def test_init_custom_bin_count(self) -> None:
        """测试自定义 bin 数量"""
        model = SpectrumDataModel(bin_count=128)
        self.assertEqual(model.binCount, 128)

    def test_bin_count_setter(self) -> None:
        """测试设置 bin 数量"""
        self.model._set_bin_count(512)
        self.assertEqual(self.model.binCount, 512)

    def test_bin_count_setter_invalid(self) -> None:
        """测试设置无效 bin 数量"""
        original = self.model.binCount
        self.model._set_bin_count(0)  # 无效值
        self.assertEqual(self.model.binCount, original)

        self.model._set_bin_count(-10)  # 负值
        self.assertEqual(self.model.binCount, original)

    def test_spectrum_data_initial(self) -> None:
        """测试初始频谱数据"""
        data = self.model.spectrumData
        self.assertEqual(len(data), 256)
        self.assertTrue(all(v == 0.0 for v in data))

    def test_update_spectrum_list(self) -> None:
        """测试使用列表更新频谱"""
        test_data = [0.5] * 256
        self.model.updateSpectrum(test_data)
        data = self.model.spectrumData
        self.assertEqual(len(data), 256)
        self.assertTrue(all(abs(v - 0.5) < 0.01 for v in data))

    def test_update_spectrum_numpy(self) -> None:
        """测试使用 NumPy 数组更新频谱"""
        test_data = np.random.random(256)
        self.model.updateSpectrum(test_data)
        data = self.model.spectrumData
        self.assertEqual(len(data), 256)

    def test_update_spectrum_truncate(self) -> None:
        """测试过长数据被截断"""
        test_data = [0.5] * 512  # 超过 bin_count
        self.model.updateSpectrum(test_data)
        data = self.model.spectrumData
        self.assertEqual(len(data), 256)

    def test_update_spectrum_pad(self) -> None:
        """测试过短数据被补零"""
        test_data = [0.8] * 100  # 少于 bin_count
        self.model.updateSpectrum(test_data)
        data = self.model.spectrumData
        self.assertEqual(len(data), 256)
        # 前 100 个应该是 0.8
        self.assertTrue(all(abs(v - 0.8) < 0.01 for v in data[:100]))
        # 后面应该是 0
        self.assertTrue(all(v == 0.0 for v in data[100:]))

    def test_update_spectrum_empty(self) -> None:
        """测试空数据不会崩溃"""
        self.model.updateSpectrum([])  # 不应该崩溃
        data = self.model.spectrumData
        self.assertEqual(len(data), 256)

    def test_peak_hold(self) -> None:
        """测试峰值保持"""
        # 先更新一个高值
        self.model.updateSpectrum([0.9] * 256)
        # 再更新一个低值
        self.model.updateSpectrum([0.1] * 256)

        peak_data = self.model.peakHoldData
        self.assertEqual(len(peak_data), 256)
        # 峰值应该比当前值高（因为有衰减但还没完全衰减）
        self.assertTrue(all(p >= 0.1 for p in peak_data))

    def test_peak_decay_rate(self) -> None:
        """测试峰值衰减速率设置"""
        self.model.setPeakDecayRate(0.05)
        self.assertEqual(self.model._peak_decay_rate, 0.05)

    def test_peak_decay_rate_invalid(self) -> None:
        """测试无效衰减速率"""
        original = self.model._peak_decay_rate
        self.model.setPeakDecayRate(0)  # 无效
        self.assertEqual(self.model._peak_decay_rate, original)

        self.model.setPeakDecayRate(-0.1)  # 负值
        self.assertEqual(self.model._peak_decay_rate, original)

    def test_update_from_time_domain(self) -> None:
        """测试从时域数据生成频谱"""
        # 生成一个简单的正弦波
        sample_rate = 44100
        t = np.arange(1024) / sample_rate
        signal = np.sin(2 * np.pi * 440 * t)

        self.model.updateFromTimeDomain(signal)
        data = self.model.spectrumData
        self.assertEqual(len(data), 256)
        # 应该有一些非零值
        self.assertTrue(any(v > 0 for v in data))

    def test_update_from_time_domain_empty(self) -> None:
        """测试空时域数据"""
        self.model.updateFromTimeDomain([])  # 不应该崩溃

    def test_update_from_raw_bytes(self) -> None:
        """测试从原始字节数据生成频谱"""
        # 模拟 16-bit ADC 数据
        raw_data = [int(16000 * np.sin(2 * np.pi * 440 * i / 44100)) for i in range(1024)]
        self.model.updateFromRawBytes(raw_data, bits=16)
        data = self.model.spectrumData
        self.assertEqual(len(data), 256)

    def test_set_db_range(self) -> None:
        """测试设置 dB 范围"""
        self.model.setDbRange(-60.0, 0.0)
        self.assertEqual(self.model._db_min, -60.0)
        self.assertEqual(self.model._db_max, 0.0)

    def test_buffer_operations(self) -> None:
        """测试缓冲区操作"""
        self.model.setBufferSize(512)
        self.assertEqual(self.model._buffer_size, 512)

        self.model.setSampleRate(48000.0)
        self.assertEqual(self.model._sample_rate, 48000.0)

        self.model.setAutoUpdate(False)
        self.assertFalse(self.model._auto_update)

    def test_push_sample(self) -> None:
        """测试推入单个采样"""
        self.model.setBufferSize(10)  # 小缓冲区便于测试
        self.model.setAutoUpdate(True)

        for i in range(15):
            self.model.pushSample(0.5)

        # 缓冲区应该被清空过一次
        self.assertLess(self.model.getBufferLevel(), 10)

    def test_push_samples(self) -> None:
        """测试批量推入采样"""
        self.model.setBufferSize(100)
        self.model.setAutoUpdate(False)

        self.model.pushSamples([0.1] * 50)
        self.assertEqual(self.model.getBufferLevel(), 50)

        self.model.pushSamples([0.1] * 60)
        # 应该消费掉一个缓冲区的数据
        self.assertEqual(self.model.getBufferLevel(), 10)

    def test_push_raw_sample(self) -> None:
        """测试推入原始 ADC 采样"""
        self.model.setBufferSize(10)
        self.model.pushRawSample(16000, bits=16)
        self.assertEqual(self.model.getBufferLevel(), 1)

    def test_flush_buffer(self) -> None:
        """测试强制处理缓冲区"""
        self.model.setBufferSize(100)
        self.model.pushSamples([0.5] * 50)
        self.model.flushBuffer()
        self.assertEqual(self.model.getBufferLevel(), 0)

    def test_clear_buffer(self) -> None:
        """测试清空缓冲区"""
        self.model.pushSamples([0.5] * 50)
        self.model.clearBuffer()
        self.assertEqual(self.model.getBufferLevel(), 0)

    def test_clear(self) -> None:
        """测试清空所有数据"""
        self.model.updateSpectrum([0.5] * 256)
        self.model.pushSamples([0.1] * 50)
        self.model.clear()

        data = self.model.spectrumData
        self.assertTrue(all(v == 0.0 for v in data))
        self.assertEqual(self.model.getBufferLevel(), 0)

    def test_buffer_progress(self) -> None:
        """测试缓冲区进度"""
        self.model.setBufferSize(100)
        self.model.pushSamples([0.1] * 50)
        progress = self.model.getBufferProgress()
        self.assertAlmostEqual(progress, 0.5, places=2)

    def test_get_sample_rate(self) -> None:
        """测试获取采样率"""
        self.assertEqual(self.model.getSampleRate(), 44100.0)

    def test_get_max_frequency(self) -> None:
        """测试获取最大频率"""
        self.model.setSampleRate(44100.0)
        self.assertEqual(self.model.getMaxFrequency(), 22050.0)

    def test_get_frequency_resolution(self) -> None:
        """测试获取频率分辨率"""
        self.model.setSampleRate(44100.0)
        self.model.setBufferSize(441)
        resolution = self.model.getFrequencyResolution()
        self.assertAlmostEqual(resolution, 100.0, places=1)

    def test_signal_emission(self) -> None:
        """测试信号发射"""
        signal_received = []

        def on_data_changed():
            signal_received.append(True)

        self.model.spectrumDataChanged.connect(on_data_changed)
        self.model.updateSpectrum([0.5] * 256)

        self.assertTrue(len(signal_received) > 0)


class TestSpectrumSimulator(unittest.TestCase):
    """测试 SpectrumSimulator 类"""

    def setUp(self) -> None:
        self.model = SpectrumDataModel(bin_count=256)
        self.simulator = SpectrumSimulator(self.model)

    def tearDown(self) -> None:
        if self.simulator._timer.isActive():
            self.simulator.stop()

    def test_init(self) -> None:
        """测试初始化"""
        self.assertFalse(self.simulator.running)
        self.assertEqual(self.simulator.intervalMs, 100)

    def test_set_interval(self) -> None:
        """测试设置更新间隔"""
        self.simulator._set_interval_ms(50)
        self.assertEqual(self.simulator.intervalMs, 50)

    def test_set_interval_invalid(self) -> None:
        """测试设置无效间隔"""
        self.simulator._set_interval_ms(0)  # 无效
        self.assertEqual(self.simulator.intervalMs, 100)  # 保持原值

    @unittest.skip("QTimer requires QApplication event loop")
    def test_start_stop(self) -> None:
        """测试启动和停止"""
        self.simulator.start()
        self.assertTrue(self.simulator.running)

        self.simulator.stop()
        self.assertFalse(self.simulator.running)

    def test_spectrum_model_property(self) -> None:
        """测试 spectrumModel 属性"""
        self.assertIs(self.simulator.spectrumModel, self.model)

    def test_generate_frame(self) -> None:
        """测试生成一帧数据"""
        # 手动调用内部方法
        self.simulator._generate_frame()
        data = self.model.spectrumData

        # 应该有数据更新
        self.assertTrue(any(v > 0 for v in data))
        # 所有值应该在 [0, 1] 范围内
        self.assertTrue(all(0.0 <= v <= 1.0 for v in data))


if __name__ == "__main__":
    unittest.main()
