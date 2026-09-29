"""测试 foup_acquisition 模块"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.foup_acquisition import FoupAcquisitionController


class MockSeriesModel:
    """模拟的曲线模型"""

    def __init__(self):
        self.points = []
        self.cleared = False

    def append_point(self, x, y):
        self.points.append((x, y))

    def clear(self):
        self.points = []
        self.cleared = True


class TestFoupAcquisitionController(unittest.TestCase):
    """测试 FoupAcquisitionController 类"""

    def setUp(self) -> None:
        self.series_models = [MockSeriesModel() for _ in range(3)]
        self.controller = FoupAcquisitionController(
            series_models=self.series_models,
            host="127.0.0.1",
            port=65432,
        )

    def tearDown(self) -> None:
        # 确保停止任何运行中的采集
        if self.controller.running:
            self.controller.stopAcquisition()

    def test_initial_state(self) -> None:
        """测试初始状态"""
        self.assertFalse(self.controller.running)
        self.assertEqual(self.controller.statusMessage, "未启动")
        self.assertEqual(self.controller.channelCount, 0)

    def test_host_property(self) -> None:
        """测试 host 属性"""
        self.assertEqual(self.controller.host, "127.0.0.1")

    def test_host_setter(self) -> None:
        """测试设置 host"""
        self.controller.host = "192.168.1.100"
        self.assertEqual(self.controller.host, "192.168.1.100")

    def test_host_setter_strip(self) -> None:
        """测试设置 host 时去除空白"""
        self.controller.host = "  192.168.1.100  "
        self.assertEqual(self.controller.host, "192.168.1.100")

    def test_host_setter_empty(self) -> None:
        """测试设置空 host"""
        original = self.controller.host
        self.controller.host = ""
        # 应该发出错误信号，host 不变
        self.assertEqual(self.controller.host, original)

    def test_operation_mode_property(self) -> None:
        """测试 operationMode 属性"""
        self.assertEqual(self.controller.operationMode, "test")

    def test_operation_mode_setter(self) -> None:
        """测试设置 operationMode"""
        self.controller.operationMode = "normal"
        self.assertEqual(self.controller.operationMode, "normal")

        self.controller.operationMode = "test"
        self.assertEqual(self.controller.operationMode, "test")

    def test_operation_mode_setter_invalid(self) -> None:
        """测试设置无效 operationMode"""
        self.controller.operationMode = "invalid"
        self.assertEqual(self.controller.operationMode, "test")  # 默认值

    def test_normal_mode_remote_path(self) -> None:
        """测试 normalModeRemotePath 属性"""
        self.assertEqual(self.controller.normalModeRemotePath, "Log")

    def test_normal_mode_remote_path_setter(self) -> None:
        """测试设置 normalModeRemotePath"""
        self.controller.normalModeRemotePath = "/custom/path"
        self.assertEqual(self.controller.normalModeRemotePath, "/custom/path")

    def test_series_model_property(self) -> None:
        """测试 seriesModel 属性"""
        self.assertIs(self.controller.seriesModel, self.series_models[0])

    def test_last_value_initial(self) -> None:
        """测试初始 lastValue"""
        import math
        self.assertTrue(math.isnan(self.controller.lastValue))

    def test_server_version_initial(self) -> None:
        """测试初始 serverVersion"""
        self.assertEqual(self.controller.serverVersion, "")

    def test_server_type_initial(self) -> None:
        """测试初始 serverType"""
        self.assertEqual(self.controller.serverType, "")

    def test_server_type_display_name_unknown(self) -> None:
        """测试未知服务器类型的显示名称"""
        self.assertEqual(self.controller.serverTypeDisplayName, "未知类型")

    def test_parse_version_response_simple(self) -> None:
        """测试解析简单版本响应"""
        version, prefix = self.controller._parse_version_response("VOC, v1.0")
        self.assertEqual(version, "v1.0")
        self.assertEqual(prefix, "VOC")

    def test_parse_version_response_uppercase(self) -> None:
        """测试解析版本响应转大写"""
        version, prefix = self.controller._parse_version_response("voc, v1.0")
        self.assertEqual(prefix, "VOC")

    def test_parse_version_response_no_version(self) -> None:
        """测试解析只有类型的响应"""
        version, prefix = self.controller._parse_version_response("NOISE_HUMILITY")
        self.assertEqual(version, "")
        self.assertEqual(prefix, "NOISE_HUMILITY")

    def test_parse_version_response_empty(self) -> None:
        """测试解析空响应"""
        version, prefix = self.controller._parse_version_response("")
        self.assertEqual(version, "")
        self.assertEqual(prefix, "")

    def test_parse_version_response_numeric(self) -> None:
        """测试解析纯数字响应"""
        version, prefix = self.controller._parse_version_response("12345")
        self.assertEqual(version, "")
        self.assertEqual(prefix, "")

    def test_select_command(self) -> None:
        """测试命令选择"""
        # 设置前缀
        self.controller._command_prefix = "VOC"
        cmd = self.controller._select_command("start")
        self.assertEqual(cmd, "VOC_data_coll_ctrl_start")

        cmd = self.controller._select_command("stop")
        self.assertEqual(cmd, "VOC_data_coll_ctrl_stop")

    def test_select_command_sample(self) -> None:
        """测试采样命令选择"""
        self.controller._command_prefix = "VOC"
        cmd = self.controller._select_command("sample_test")
        self.assertEqual(cmd, "VOC_sample_type_test")

        cmd = self.controller._select_command("sample_normal")
        self.assertEqual(cmd, "VOC_sample_type_normal")

    def test_handle_line_ack(self) -> None:
        """测试处理 ACK 响应"""
        self.controller._handle_line("ack")
        self.assertEqual(self.controller.statusMessage, "收到 ACK")

    def test_handle_line_single_value(self) -> None:
        """测试处理单值数据"""
        self.controller._handle_line("123.45")
        self.assertEqual(self.controller.channelCount, 1)
        self.assertAlmostEqual(self.controller.lastValue, 123.45, places=2)

    def test_handle_line_multiple_values(self) -> None:
        """测试处理多值数据"""
        self.controller._handle_line("100.0, 200.0, 300.0")
        self.assertEqual(self.controller.channelCount, 3)
        self.assertAlmostEqual(self.controller.lastValue, 100.0, places=2)

    def test_handle_line_invalid_token_drops_whole_frame(self) -> None:
        """含非法字段的数据帧必须整帧丢弃，否则后续通道会整体错位"""
        self.controller._handle_line("12.3,<bad>,45.6")
        # 不能把 45.6 落到通道 1：应当整帧丢弃
        self.assertEqual(self.controller.channelCount, 0)
        self.assertEqual(self.controller.lastValue != self.controller.lastValue, True)  # NaN
        for model in self.series_models:
            self.assertEqual(model.points, [])

    def test_handle_line_trailing_comma_drops_frame(self) -> None:
        """空字段同样视为非法，避免静默错位"""
        self.controller._handle_line("1.0,2.0,")
        self.assertEqual(self.controller.channelCount, 0)
        self.assertEqual(self.series_models[0].points, [])

    def test_handle_line_valid_frame_still_accepted_after_bad_frame(self) -> None:
        """坏帧之后的好帧仍要正常接收"""
        self.controller._handle_line("1.0,bad,3.0")
        self.controller._handle_line("10.0,20.0,30.0")
        self.assertEqual(self.controller.channelCount, 3)
        self.assertAlmostEqual(self.controller.getChannelValue(2), 30.0, places=2)

    @unittest.skip("Noise_Spectrum 当前暂未使用")
    def test_handle_line_noise_spectrum_routes_to_spectrum_model(self) -> None:
        """测试 Noise_Spectrum 前缀将 256 点数据路由到频谱模型"""
        spectrum_model = MagicMock()
        spectrum_simulator = MagicMock()
        spectrum_simulator.running = True

        controller = FoupAcquisitionController(
            series_models=self.series_models,
            host="127.0.0.1",
            port=65432,
            spectrum_model=spectrum_model,
            spectrum_simulator=spectrum_simulator,
        )

        payload = ",".join(str(i) for i in range(256))
        controller._handle_line("Noise_Spectrum," + payload)

        spectrum_model.updateSpectrum.assert_called_once()
        called_values = spectrum_model.updateSpectrum.call_args[0][0]
        self.assertEqual(len(called_values), 256)
        self.assertEqual(len(self.series_models[0].points), 0)
        spectrum_simulator.stop.assert_called_once()
        self.assertEqual(controller.serverType, "")

        # 第二次更新不会重复 stop（避免频繁控制模拟器）
        controller._handle_line("Noise_Spectrum," + payload)
        self.assertEqual(spectrum_simulator.stop.call_count, 1)

    @unittest.skip("Noise_Spectrum 当前暂未使用")
    def test_handle_line_noise_spectrum_prefixed_payload(self) -> None:
        """测试每包带 prefix 的 Noise_Spectrum 数据格式"""
        spectrum_model = MagicMock()
        controller = FoupAcquisitionController(
            series_models=self.series_models,
            host="127.0.0.1",
            port=65432,
            spectrum_model=spectrum_model,
        )

        payload = "Noise_Spectrum," + ",".join(str(i) for i in range(256))
        controller._handle_line(payload)

        spectrum_model.updateSpectrum.assert_called_once()
        called_values = spectrum_model.updateSpectrum.call_args[0][0]
        self.assertEqual(len(called_values), 256)
        self.assertEqual(controller.serverType, "")

    def test_handle_line_spec_with_timestamp_normalizes_uint32(self) -> None:
        """测试 SPEC,ts,uint32... 会丢弃 ts 并归一化到 0~1"""
        spectrum_model = MagicMock()
        controller = FoupAcquisitionController(
            series_models=self.series_models,
            host="127.0.0.1",
            port=65432,
            spectrum_model=spectrum_model,
        )

        # 256 个 bin，最大值应归一化为 1.0
        bins = [0, 10, 2**32 - 1] + [1] * 253
        payload = "SPEC,566167600," + ",".join(str(v) for v in bins)
        controller._handle_line(payload)

        spectrum_model.updateSpectrum.assert_called_once()
        called_values = spectrum_model.updateSpectrum.call_args[0][0]
        self.assertEqual(len(called_values), 256)
        self.assertAlmostEqual(max(called_values), 1.0, places=6)

    def test_handle_line_empty(self) -> None:
        """测试处理空行"""
        self.controller._handle_line("")  # 不应该崩溃
        self.controller._handle_line("   ")  # 不应该崩溃

    def test_handle_line_invalid(self) -> None:
        """测试处理无效数据"""
        self.controller._handle_line("invalid data")  # 不应该崩溃

    def test_handle_line_scientific_notation_is_not_identity(self) -> None:
        """科学计数法数值按数据处理，不得被当成服务器类型"""
        self.controller._handle_line("1.2e5,3.4")
        # 解析为两个通道的数据点，而不是把 "1.2E5" 当成 prefix
        self.assertEqual(self.controller.channelCount, 2)
        self.assertAlmostEqual(self.controller.getChannelValue(0), 120000.0, places=1)
        self.assertNotEqual(self.controller.serverType, "1.2E5")
        self.assertEqual(self.controller.serverVersion, "")

    def test_identity_parsing_rejects_data_and_error_text(self) -> None:
        """查询与流式两条路径共用同一套严格身份校验（R21）"""
        for payload in (
            "1.2e5",
            "1.2e5,3.4",
            "nan,1.2",
            "nan,inf",
            "-inf,2.0",
            "ERROR no device",
            "Error: timeout,1.0",
            "Noise_Spectrum,0.5,0.5",
            "SPEC,1,2,3",
            "123.45",
            "voc,v1.0.0",
        ):
            self.assertEqual(
                FoupAcquisitionController._parse_identity(payload), ("", ""), payload
            )

    def test_identity_parsing_accepts_device_forms(self) -> None:
        """下位机实际返回形式必须被接受"""
        self.assertEqual(
            FoupAcquisitionController._parse_identity("VOC,V1.0.0"), ("V1.0.0", "VOC")
        )
        self.assertEqual(
            FoupAcquisitionController._parse_identity("VOC, V1.0.0"), ("V1.0.0", "VOC")
        )
        self.assertEqual(
            FoupAcquisitionController._parse_identity("NOISE_HUMILITY"),
            ("", "NOISE_HUMILITY"),
        )

    def test_handle_line_accepts_strict_identity_line(self) -> None:
        """严格形如 {PREFIX},{version} 的报文仍然可以更新身份"""
        self.controller._handle_line("NOISE_HUMILITY,V1.2.3")
        self.assertEqual(self.controller.serverType, "NOISE_HUMILITY")
        self.assertEqual(self.controller.serverVersion, "V1.2.3")
        self.assertEqual(self.series_models[0].points, [])

    def test_handle_line_non_numeric_tokens_never_become_prefix(self) -> None:
        """NaN/inf/报错文本不得成为服务器类型"""
        for payload in ("nan,inf", "NaN", "-inf,2.0", "Error: timeout,1.0"):
            controller = FoupAcquisitionController(
                series_models=[MockSeriesModel()],
                host="127.0.0.1",
                port=65432,
            )
            controller._handle_line(payload)
            self.assertNotIn(
                controller.serverType, {"NAN", "INF", "ERROR: TIMEOUT"}, payload
            )

    def test_get_channel_value(self) -> None:
        """测试获取通道值"""
        self.controller._handle_line("100.0, 200.0, 300.0")
        self.assertAlmostEqual(self.controller.getChannelValue(0), 100.0, places=2)
        self.assertAlmostEqual(self.controller.getChannelValue(1), 200.0, places=2)
        self.assertAlmostEqual(self.controller.getChannelValue(2), 300.0, places=2)

    def test_get_channel_value_out_of_range(self) -> None:
        """测试获取越界通道值"""
        import math
        self.controller._handle_line("100.0")
        value = self.controller.getChannelValue(10)
        self.assertTrue(math.isnan(value))

    def test_channel_config_get(self) -> None:
        """测试获取通道配置"""
        self.controller._command_prefix = "VOC"
        self.controller._channel_count = 1
        self.controller._init_config_if_ready()

        config = self.controller.getChannelConfig(0)
        self.assertIsInstance(config, dict)
        self.assertIn("title", config)

    def test_channel_config_set_title(self) -> None:
        """测试设置通道标题"""
        self.controller._command_prefix = "VOC"
        self.controller._channel_count = 1
        self.controller._init_config_if_ready()

        self.controller.setChannelTitle(0, "Custom Title")
        title = self.controller.getChannelTitle(0)
        self.assertEqual(title, "Custom Title")

    def test_channel_config_set_limits(self) -> None:
        """测试设置通道限值"""
        self.controller._command_prefix = "VOC"
        self.controller._channel_count = 1
        self.controller._init_config_if_ready()

        self.controller.setChannelLimits(0, 100.0, 10.0, 120.0, 5.0, 50.0)
        self.assertEqual(self.controller.getOocUpper(0), 100.0)
        self.assertEqual(self.controller.getOocLower(0), 10.0)
        self.assertEqual(self.controller.getOosUpper(0), 120.0)
        self.assertEqual(self.controller.getOosLower(0), 5.0)
        self.assertEqual(self.controller.getTarget(0), 50.0)

    def test_channel_config_set_unit(self) -> None:
        """测试设置通道单位"""
        self.controller._command_prefix = "VOC"
        self.controller._channel_count = 1
        self.controller._init_config_if_ready()

        self.controller.setChannelUnit(0, "ppm")
        unit = self.controller.getUnit(0)
        self.assertEqual(unit, "ppm")

    def test_show_limits(self) -> None:
        """测试显示限值设置"""
        self.controller._command_prefix = "VOC"
        self.controller._channel_count = 1
        self.controller._init_config_if_ready()

        self.controller.setShowLimits(0, True, False, True, False, True)
        self.assertTrue(self.controller.getShowOocUpper(0))
        self.assertFalse(self.controller.getShowOocLower(0))
        self.assertTrue(self.controller.getShowOosUpper(0))
        self.assertFalse(self.controller.getShowOosLower(0))
        self.assertTrue(self.controller.getShowTarget(0))

    def test_set_running(self) -> None:
        """测试设置运行状态"""
        self.controller._set_running(True)
        self.assertTrue(self.controller.running)

        self.controller._set_running(False)
        self.assertFalse(self.controller.running)

    def test_set_status(self) -> None:
        """测试设置状态消息"""
        self.controller._set_status("测试状态")
        self.assertEqual(self.controller.statusMessage, "测试状态")

    def test_append_point_to_model(self) -> None:
        """测试追加数据点到模型"""
        self.controller._append_point_to_model(1000.0, [10.0, 20.0, 30.0])

        self.assertEqual(len(self.series_models[0].points), 1)
        self.assertEqual(self.series_models[0].points[0], (1000.0, 10.0))
        self.assertEqual(self.series_models[1].points[0], (1000.0, 20.0))
        self.assertEqual(self.series_models[2].points[0], (1000.0, 30.0))

    def test_version_query_ignores_non_identity_response(self) -> None:
        """查询阶段收到数据/错误文本时不得改写服务器类型（R21）"""
        import struct
        from unittest.mock import patch as _patch

        class _Comm:
            def __init__(self, *args, **kwargs):
                payload = "1.2e5".encode("utf-8")
                self._buffer = bytearray(struct.pack(">I", len(payload)) + payload)

            def send(self, data: bytes) -> None:
                return None

            def recv(self, size: int) -> bytes:
                if not self._buffer:
                    return b""
                chunk = self._buffer[:size]
                del self._buffer[:size]
                return bytes(chunk)

            def close(self) -> None:
                return None

        self.controller._communicator = _Comm()
        with _patch("voc_app.gui.foup_acquisition.SocketCommunicator", _Comm):
            self.controller._perform_version_query()

        self.assertEqual(self.controller.serverType, "")
        self.assertEqual(self.controller.serverVersion, "")


class TestFoupAcquisitionControllerNoSeries(unittest.TestCase):
    """测试没有曲线模型的情况"""

    def test_init_empty_series(self) -> None:
        """测试空曲线模型列表"""
        controller = FoupAcquisitionController(
            series_models=[],
            host="127.0.0.1",
            port=65432,
        )
        self.assertIsNone(controller.seriesModel)

    def test_init_none_series(self) -> None:
        """测试 None 曲线模型"""
        controller = FoupAcquisitionController(
            series_models=[None, None],
            host="127.0.0.1",
            port=65432,
        )
        self.assertEqual(len(controller._series_models), 0)


if __name__ == "__main__":
    unittest.main()
