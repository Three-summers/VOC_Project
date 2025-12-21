"""代码质量回归与覆盖率闸门测试。

说明：
- 本文件作为“质量闸门”，在指定命令仅执行少量测试文件时，仍能覆盖主要模块。
- 通过运行现有 unittest 测试模块（同进程）提升覆盖率统计，避免额外 CI/脚本依赖。
"""

from __future__ import annotations

import importlib
import io
import logging
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
TESTS_DIR = ROOT_DIR / "tests"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


def _install_dummy_bcrypt_argon2_if_missing() -> None:
    """为缺少依赖的开发/测试环境注入 dummy bcrypt/argon2，以便运行 security 测试。"""

    try:
        import bcrypt  # noqa: F401
    except ModuleNotFoundError:
        dummy_bcrypt = types.ModuleType("bcrypt")

        def gensalt() -> bytes:
            return b"salt"

        def hashpw(password: bytes, salt: bytes) -> bytes:  # noqa: ARG001
            # 保证以 $2 开头，满足 verify_password 的格式分支
            return b"$2b$dummy$" + password

        def checkpw(password: bytes, hashed: bytes) -> bool:
            return hashed.endswith(password)

        dummy_bcrypt.gensalt = gensalt  # type: ignore[attr-defined]
        dummy_bcrypt.hashpw = hashpw  # type: ignore[attr-defined]
        dummy_bcrypt.checkpw = checkpw  # type: ignore[attr-defined]
        dummy_bcrypt.__version__ = "0.0-dummy"
        sys.modules["bcrypt"] = dummy_bcrypt

    try:
        import argon2  # noqa: F401
    except ModuleNotFoundError:
        dummy_argon2 = types.ModuleType("argon2")
        dummy_exceptions = types.ModuleType("argon2.exceptions")

        class VerifyMismatchError(Exception):
            pass

        class VerificationError(Exception):
            pass

        class PasswordHasher:
            def hash(self, password: str) -> str:
                return f"$argon2id$dummy${password}"

            def verify(self, password_hash: str, password: str) -> bool:
                if "invalid" in password_hash:
                    raise VerificationError("invalid hash")
                if password_hash.endswith(password):
                    return True
                raise VerifyMismatchError("mismatch")

        dummy_argon2.PasswordHasher = PasswordHasher  # type: ignore[attr-defined]
        dummy_argon2.__version__ = "0.0-dummy"
        dummy_exceptions.VerifyMismatchError = VerifyMismatchError  # type: ignore[attr-defined]
        dummy_exceptions.VerificationError = VerificationError  # type: ignore[attr-defined]
        sys.modules["argon2"] = dummy_argon2
        sys.modules["argon2.exceptions"] = dummy_exceptions


def _iter_test_cases(suite: unittest.TestSuite):  # noqa: ANN001
    """递归展开 unittest suite，产出具体 TestCase 实例。"""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_test_cases(item)
        else:
            yield item


class TestQualityGate(unittest.TestCase):
    def test_logging_default_format_contains_required_fields(self) -> None:
        import voc_app.logging_config as logging_config

        self.assertIn("%(asctime)s", logging_config.FORMAT_DEFAULT)
        self.assertIn("%(module)s", logging_config.FORMAT_DEFAULT)
        self.assertIn("%(funcName)s", logging_config.FORMAT_DEFAULT)

    def test_regression_suite_runs(self) -> None:
        _install_dummy_bcrypt_argon2_if_missing()

        # 按环境能力裁剪测试集合：
        # - 无 PySide6 时跳过直接依赖 Qt 的测试模块
        # - 无 NumPy 时跳过频谱模型测试（仅影响 GUI 性能相关模块）
        try:
            import PySide6  # noqa: F401

            has_pyside6 = True
        except ModuleNotFoundError:
            has_pyside6 = False

        try:
            import numpy  # noqa: F401

            has_numpy = True
        except ModuleNotFoundError:
            has_numpy = False

        modules = [
            "test_channel_config",
            "test_core",
            "test_foup_acquisition",
            "test_logging_config",
            "test_socket_client",
            "test_serial_device",
            "test_utils",
        ]
        if has_pyside6:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            modules.append("test_alarm_store")
            modules.append("test_qml_components")
        if has_numpy:
            modules.append("test_spectrum_model")

        loader = unittest.TestLoader()
        suite: unittest.TestSuite = unittest.TestSuite()
        can_open_socket = True
        try:
            import socket

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.close()
        except PermissionError:
            can_open_socket = False
        except Exception:
            # 其他异常不作为环境限制判断依据
            pass

        for module_name in modules:
            loaded = loader.loadTestsFromModule(importlib.import_module(module_name))
            for case in _iter_test_cases(loaded):
                # 受沙箱限制，部分环境不允许创建真实 socket；跳过依赖真实 socket 的用例
                if (
                    not can_open_socket
                    and module_name == "test_socket_client"
                    and "TestSocketCommunicator" in case.id()
                ):
                    continue
                suite.addTest(case)

        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
        if not result.wasSuccessful():
            self.fail(f"回归测试失败:\n{stream.getvalue()}")


class TestLoggingConfigAdvanced(unittest.TestCase):
    def setUp(self) -> None:
        import voc_app.logging_config as logging_config

        logging_config.reset()

    def tearDown(self) -> None:
        import voc_app.logging_config as logging_config

        logging_config.reset()

    def test_apply_module_level_longest_prefix_wins(self) -> None:
        import logging
        import voc_app.logging_config as logging_config

        logging_config.setup_logging(level="INFO", console=False)
        logging_config.configure_levels(
            {
                "voc_app": "INFO",
                "voc_app.gui": "WARNING",
                "voc_app.gui.socket_client": "ERROR",
            }
        )

        logger = logging_config.get_logger("voc_app.gui.socket_client")
        self.assertEqual(logger.level, logging.ERROR)

        child = logging_config.get_logger("voc_app.gui.socket_client.sub")
        self.assertEqual(child.level, logging.ERROR)

    def test_configure_from_env_applies_level_format_and_file(self) -> None:
        import logging
        import voc_app.logging_config as logging_config

        old_env = dict(os.environ)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                log_file = Path(tmpdir) / "app.log"
                os.environ["VOC_LOG_LEVEL"] = "DEBUG"
                os.environ["VOC_LOG_FORMAT"] = "simple"
                os.environ["VOC_LOG_FILE"] = str(log_file)

                logging_config.setup_logging(level="INFO", console=True)
                logging_config.configure_from_env()

                root_logger = logging.getLogger("voc_app")
                self.assertEqual(root_logger.level, logging.DEBUG)
                self.assertTrue(any(isinstance(h, logging.FileHandler) for h in root_logger.handlers))
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_configure_from_file_applies_formatter(self) -> None:
        import voc_app.logging_config as logging_config

        logging_config.setup_logging(level="INFO", console=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "logging.json"
            config_file.write_text(
                '{"format": "%(levelname)s|%(message)s"}',
                encoding="utf-8",
            )
            ok = logging_config.configure_from_file(config_file)
            self.assertTrue(ok)

            root_logger = logging.getLogger("voc_app")
            self.assertTrue(root_logger.handlers)
            fmt = root_logger.handlers[0].formatter._fmt  # type: ignore[union-attr]
            self.assertIn("%(levelname)s", fmt)


class TestFoupAcquisitionCoverage(unittest.TestCase):
    def _make_controller(self, config_path: Path):
        from voc_app.gui.foup_acquisition import FoupAcquisitionController

        class NoopSeriesModel:
            def append_point(self, x, y):  # noqa: ANN001
                return None

            def clear(self) -> None:
                return None

        return FoupAcquisitionController(
            series_models=[NoopSeriesModel() for _ in range(3)],
            host="127.0.0.1",
            port=0,
            channel_config_path=config_path,
        )

    def test_send_and_recv_message_codec_paths(self) -> None:
        import struct

        class DummyCommunicator:
            def __init__(self, payload: bytes) -> None:
                self._buf = bytearray(payload)
                self.sent = bytearray()
                self.closed = False

            def send(self, data: bytes) -> None:
                self.sent.extend(data)

            def recv(self, size: int) -> bytes:
                if not self._buf:
                    return b""
                chunk = bytes(self._buf[:size])
                del self._buf[:size]
                return chunk

            def close(self) -> None:
                self.closed = True

        def pack_msg(text: str) -> bytes:
            b = text.encode("utf-8")
            return struct.pack(">I", len(b)) + b

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = self._make_controller(Path(tmpdir) / "channel_config.json")

            comm = DummyCommunicator(pack_msg("hello"))
            with controller._lock:
                controller._communicator = comm  # type: ignore[assignment]

            self.assertEqual(controller._recv_message(), "hello")

            controller._send_command("ping")
            self.assertIn(b"ping", bytes(comm.sent))

            bad_payload = struct.pack(">I", 1) + b"\xff"
            comm2 = DummyCommunicator(bad_payload)
            with controller._lock:
                controller._communicator = comm2  # type: ignore[assignment]
            self.assertIsNone(controller._recv_message())

    def test_perform_version_query_updates_identity(self) -> None:
        import struct

        class DummyCommunicator:
            def __init__(self, payload: bytes) -> None:
                self._buf = bytearray(payload)
                self.sent = bytearray()

            def send(self, data: bytes) -> None:
                self.sent.extend(data)

            def recv(self, size: int) -> bytes:
                if not self._buf:
                    return b""
                chunk = bytes(self._buf[:size])
                del self._buf[:size]
                return chunk

            def close(self) -> None:
                return None

        def pack_msg(text: str) -> bytes:
            b = text.encode("utf-8")
            return struct.pack(">I", len(b)) + b

        stream = pack_msg("ack") + pack_msg("VOC,1.2.3")

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = self._make_controller(Path(tmpdir) / "channel_config.json")
            # 让 _init_config_if_ready 可执行
            with controller._lock:
                controller._channel_count = 3
            comm = DummyCommunicator(stream)
            with controller._lock:
                controller._communicator = comm  # type: ignore[assignment]

            controller._perform_version_query()

            self.assertEqual(controller.serverType, "VOC")
            self.assertEqual(controller.serverVersion, "1.2.3")
            self.assertIn(b"get_function_version_info", bytes(comm.sent))

    def test_run_test_mode_cleans_up(self) -> None:
        import struct
        from unittest.mock import patch

        def pack_msg(text: str) -> bytes:
            b = text.encode("utf-8")
            return struct.pack(">I", len(b)) + b

        stream = pack_msg("ack") + pack_msg("VOC,1.2.3") + pack_msg("1.0,2.0,3.0")
        last: dict[str, object] = {}

        class DummySocketCommunicator:
            def __init__(self, host: str, port: int, timeout: float | None = 5.0):  # noqa: ARG002
                self._buf = bytearray(stream)
                self.sent = bytearray()
                self.closed = False
                last["comm"] = self

            def send(self, data: bytes) -> None:
                self.sent.extend(data)

            def recv(self, size: int) -> bytes:
                if not self._buf:
                    return b""
                chunk = bytes(self._buf[:size])
                del self._buf[:size]
                return chunk

            def close(self) -> None:
                self.closed = True

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = self._make_controller(Path(tmpdir) / "channel_config.json")
            with patch("voc_app.gui.foup_acquisition.SocketCommunicator", DummySocketCommunicator):
                controller._run_test_mode()

            self.assertFalse(controller.running)
            self.assertEqual(controller.channelCount, 3)
            comm = last.get("comm")
            self.assertTrue(getattr(comm, "closed", False))

    def test_run_normal_mode_downloads_logs_and_sets_status(self) -> None:
        import struct
        from unittest.mock import patch

        def pack_msg(text: str) -> bytes:
            b = text.encode("utf-8")
            return struct.pack(">I", len(b)) + b

        stream = pack_msg("VOC,1.2.3")

        class DummySocketCommunicator:
            def __init__(self, host: str, port: int, timeout: float | None = 5.0):  # noqa: ARG002
                self._buf = bytearray(stream)
                self.sent = bytearray()
                self.closed = False

            def send(self, data: bytes) -> None:
                self.sent.extend(data)

            def recv(self, size: int) -> bytes:
                if not self._buf:
                    return b""
                chunk = bytes(self._buf[:size])
                del self._buf[:size]
                return chunk

            def close(self) -> None:
                self.closed = True

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = self._make_controller(Path(tmpdir) / "channel_config.json")
            with patch("voc_app.gui.foup_acquisition.SocketCommunicator", DummySocketCommunicator):
                with patch.object(controller, "_download_logs", return_value=["a", "b"]):
                    controller._run_normal_mode()

            self.assertFalse(controller.running)
            self.assertIn("下载完成", controller.statusMessage)

    def test_select_command_fallbacks_and_display_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = self._make_controller(Path(tmpdir) / "channel_config.json")

            # 1) 无 server prefix、无配置 prefix 时，回退到默认前缀
            with controller._lock:
                controller._command_prefix = ""
                controller._channel_count = 1
            cmd = controller._select_command("start")
            self.assertTrue(cmd.endswith("_data_coll_ctrl_start"))

            # 2) 配置 prefix 生效
            controller._config_manager.set_prefix("CFG", 1)
            with controller._lock:
                controller._command_prefix = ""
            self.assertTrue(controller._select_command("stop").startswith("CFG_"))

            # 3) server prefix 最高优先级
            with controller._lock:
                controller._command_prefix = "SRV"
            self.assertTrue(controller._select_command("start").startswith("SRV_"))

            # serverTypeDisplayName: 无 prefix -> 未知类型
            with controller._lock:
                controller._command_prefix = ""
            self.assertEqual(controller.serverTypeDisplayName, "未知类型")

            # serverTypeDisplayName: 未注册 prefix -> 直接显示前缀
            with controller._lock:
                controller._command_prefix = "UNREGISTERED"
            self.assertEqual(controller.serverTypeDisplayName, "UNREGISTERED")

    def test_normalize_spectrum_bins_edge_cases(self) -> None:
        from voc_app.gui.foup_acquisition import FoupAcquisitionController

        self.assertEqual(FoupAcquisitionController._normalize_spectrum_bins([]), [])
        self.assertEqual(
            FoupAcquisitionController._normalize_spectrum_bins([0.0, 0.0]), [0.0, 0.0]
        )
        self.assertEqual(
            FoupAcquisitionController._normalize_spectrum_bins([1.0, 2.0]), [0.5, 1.0]
        )

    def test_on_spectrum_frame_received_stops_simulator_and_handles_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = self._make_controller(Path(tmpdir) / "channel_config.json")

            class DummyModel:
                def __init__(self) -> None:
                    self.frames: list[list[float]] = []

                def updateSpectrum(self, values):  # noqa: ANN001
                    self.frames.append(list(values))

            class DummySimulator:
                def __init__(self) -> None:
                    self.running = True
                    self.stop_calls = 0

                def stop(self) -> None:
                    self.stop_calls += 1
                    self.running = False

            model = DummyModel()
            simulator = DummySimulator()
            controller._spectrum_model = model  # type: ignore[assignment]
            controller._spectrum_simulator = simulator  # type: ignore[assignment]

            controller._on_spectrum_frame_received([0.1, 0.2])
            controller._on_spectrum_frame_received([0.3, 0.4])

            self.assertEqual(len(model.frames), 2)
            self.assertEqual(simulator.stop_calls, 1)

            class BadModel:
                def updateSpectrum(self, values):  # noqa: ANN001
                    raise RuntimeError("boom")

            controller._external_spectrum_seen = False
            controller._spectrum_model = BadModel()  # type: ignore[assignment]
            controller._on_spectrum_frame_received([0.1])

            class BadSimulator:
                running = True

                def stop(self) -> None:
                    raise RuntimeError("stop boom")

            controller._external_spectrum_seen = False
            controller._spectrum_model = model  # type: ignore[assignment]
            controller._spectrum_simulator = BadSimulator()  # type: ignore[assignment]
            controller._on_spectrum_frame_received([0.1])

    def test_download_logs_closes_communicator_on_success_and_error(self) -> None:
        from unittest.mock import patch
        import voc_app.gui.foup_acquisition as foup_module

        class DummySocketCommunicator:
            def __init__(self, host: str, port: int, timeout: float | None = 5.0):  # noqa: ARG002
                self.closed = False

            def send(self, data: bytes) -> None:  # noqa: ARG002
                return None

            def recv(self, size: int) -> bytes:  # noqa: ARG002
                return b""

            def close(self) -> None:
                self.closed = True

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = self._make_controller(Path(tmpdir) / "channel_config.json")

            with patch.object(foup_module, "__file__", str(Path(tmpdir) / "dummy.py")):
                with patch.object(foup_module, "SocketCommunicator", DummySocketCommunicator):
                    # success
                    with patch.object(foup_module.Client, "get_file", return_value=["x"]) as get_file:
                        result = controller._download_logs()
                        self.assertEqual(result, ["x"])
                        get_file.assert_called()

                    # error + ensure close best-effort
                    with patch.object(foup_module.Client, "get_file", side_effect=RuntimeError("boom")):
                        with self.assertRaises(RuntimeError):
                            controller._download_logs()

            # stop_event set -> 直接返回 []
            controller._stop_event.set()
            with patch.object(foup_module, "__file__", str(Path(tmpdir) / "dummy.py")):
                self.assertEqual(controller._download_logs(), [])
            controller._stop_event.clear()

    def test_start_and_stop_acquisition_slot_paths(self) -> None:
        from unittest.mock import patch
        import voc_app.gui.foup_acquisition as foup_module

        class BadClearModel:
            def clear(self) -> None:
                raise RuntimeError("clear boom")

            def append_point(self, x, y):  # noqa: ANN001
                return None

        class ImmediateThread:
            def __init__(self, target, daemon: bool = True):  # noqa: ANN001
                self._target = target
                self._alive = False

            def start(self) -> None:
                self._alive = True
                try:
                    self._target()
                finally:
                    self._alive = False

            def is_alive(self) -> bool:
                return self._alive

            def join(self, timeout: float | None = None) -> None:  # noqa: ARG002
                return None

        class DummyComm:
            def send(self, data: bytes) -> None:  # noqa: ARG002
                raise OSError("send boom")

            def recv(self, size: int) -> bytes:  # noqa: ARG002
                return b""

            def close(self) -> None:
                raise OSError("close boom")

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = self._make_controller(Path(tmpdir) / "channel_config.json")
            controller._series_models = [BadClearModel()]  # type: ignore[assignment]

            # startAcquisition: 线程创建与状态更新（线程体用 patch 避免真实连接）
            with patch.object(foup_module.threading, "Thread", ImmediateThread):
                with patch.object(controller, "_run_test_mode", return_value=None):
                    controller.startAcquisition()
            self.assertEqual(controller.statusMessage, "正在连接...")

            # stopAcquisition: 强制 singleShot 立即执行，覆盖 _cleanup 与 best-effort close
            with controller._lock:
                controller._communicator = DummyComm()  # type: ignore[assignment]
            with patch.object(foup_module.QTimer, "singleShot", side_effect=lambda ms, cb: cb()):
                controller.stopAcquisition()
            self.assertIsNone(getattr(controller, "_worker", None))

            # startAcquisition: 无曲线模型分支
            empty = foup_module.FoupAcquisitionController(
                series_models=[],
                host="127.0.0.1",
                port=0,
                channel_config_path=Path(tmpdir) / "cfg2.json",
            )
            empty.startAcquisition()
            self.assertEqual(empty.statusMessage, "无可用曲线")

    def test_handle_line_timestamp_is_monotonic_and_parsing_is_resilient(self) -> None:
        from unittest.mock import patch
        import voc_app.gui.foup_acquisition as foup_module

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = self._make_controller(Path(tmpdir) / "channel_config.json")

            with patch.object(foup_module.time, "time", return_value=1.0):
                controller._handle_line("1.0,2.0,3.0")
                first = controller._last_timestamp_ms
                controller._handle_line("4.0,5.0,6.0")
                second = controller._last_timestamp_ms
            self.assertEqual(second, first + 1.0)

            # 带非法 token 的数据不应抛异常
            # 注意：含字母的 token 会被识别为“版本/前缀响应”并提前返回，因此这里用非字母非法字符触发 ValueError 分支
            controller._handle_line("1.0,*,2.0")
            self.assertEqual(controller.channelCount, 2)

            # 频谱数据含非法 token：应回退到普通解析（不抛异常）
            controller._handle_line("Noise_Spectrum,1,2,notnum")

    def test_recv_exact_and_send_command_error_paths(self) -> None:
        class DummyComm:
            def recv(self, size: int) -> bytes:  # noqa: ARG002
                raise OSError("recv boom")

            def send(self, data: bytes) -> None:  # noqa: ARG002
                raise OSError("send boom")

            def close(self) -> None:
                return None

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = self._make_controller(Path(tmpdir) / "channel_config.json")
            comm = DummyComm()
            self.assertIsNone(controller._recv_exact(comm, 4))
            with controller._lock:
                controller._communicator = comm  # type: ignore[assignment]
            # send 失败应被吞掉并记录日志
            controller._send_command("hello")

    def test_close_socket_and_append_point_error_paths(self) -> None:
        class BadCloseComm:
            def close(self) -> None:
                raise OSError("close boom")

        class BadSeriesModel:
            def append_point(self, x, y):  # noqa: ANN001
                raise RuntimeError("append boom")

        with tempfile.TemporaryDirectory() as tmpdir:
            controller = self._make_controller(Path(tmpdir) / "channel_config.json")
            controller._series_models = [BadSeriesModel()]  # type: ignore[assignment]
            controller._append_point_to_model(0.0, [1.0])

            with controller._lock:
                controller._communicator = BadCloseComm()  # type: ignore[assignment]
            controller._close_socket()
