"""资源泄漏测试。

目标：
- SocketCommunicator 通过 SocketResourceManager 关闭底层 socket（无泄漏）
- E84Controller 在 close() 时停止 QTimer 并释放 GPIO 资源（可在无树莓派依赖环境下测试）
"""

from __future__ import annotations

import os
import socket
import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_QT_APP = None


def _ensure_qt_app() -> None:
    """在存在 PySide6 的环境中创建最小 QCoreApplication，避免 QTimer 启动报错。"""
    global _QT_APP
    try:
        from PySide6.QtCore import QCoreApplication  # type: ignore
    except ModuleNotFoundError:
        return
    if QCoreApplication.instance() is None:
        _QT_APP = QCoreApplication([])  # pragma: no cover - 仅在有 PySide6 时执行


class TestSocketCommunicatorResourceRelease(unittest.TestCase):
    def test_socket_is_closed_via_resource_manager(self) -> None:
        from voc_app.gui.socket_client import SocketCommunicator
        import voc_app.utils.resource_manager as resource_manager_module

        calls: dict[str, object] = {"closed": 0, "shutdown": 0, "connected": 0}

        class DummySocket:
            def settimeout(self, timeout: float) -> None:  # noqa: ANN001
                calls["timeout"] = timeout

            def connect(self, addr) -> None:  # noqa: ANN001
                calls["connected"] = calls.get("connected", 0) + 1
                calls["addr"] = addr

            def shutdown(self, how: int) -> None:  # noqa: ANN001
                calls["shutdown"] = calls.get("shutdown", 0) + 1

            def close(self) -> None:
                calls["closed"] = calls.get("closed", 0) + 1

        with patch.object(resource_manager_module.socket, "socket", return_value=DummySocket()):
            comm = SocketCommunicator("127.0.0.1", 12345, timeout=1.0)
            comm.close()
            comm.close()  # 幂等：不应重复 close 底层 socket

        self.assertEqual(calls["connected"], 1)
        self.assertEqual(calls["shutdown"], 1)
        self.assertEqual(calls["closed"], 1)

    def test_socket_send_and_recv_timeout_paths(self) -> None:
        from voc_app.gui.socket_client import SocketCommunicator
        import voc_app.utils.resource_manager as resource_manager_module

        calls: dict[str, int] = {"sendall": 0, "recv": 0, "closed": 0, "shutdown": 0}

        class DummySocket:
            def settimeout(self, timeout: float) -> None:  # noqa: ANN001
                self._timeout = timeout

            def connect(self, addr) -> None:  # noqa: ANN001
                self._addr = addr

            def sendall(self, data: bytes) -> None:
                calls["sendall"] += 1
                self._last_sent = data

            def recv(self, size: int) -> bytes:
                calls["recv"] += 1
                raise socket.timeout()

            def shutdown(self, how: int) -> None:  # noqa: ANN001
                calls["shutdown"] += 1

            def close(self) -> None:
                calls["closed"] += 1

        with patch.object(resource_manager_module.socket, "socket", return_value=DummySocket()):
            comm = SocketCommunicator("127.0.0.1", 12345, timeout=0.1)
            comm.send(b"ping")
            self.assertEqual(comm.recv(4), b"")
            comm.close()

        self.assertEqual(calls["sendall"], 1)
        self.assertGreaterEqual(calls["recv"], 1)
        self.assertEqual(calls["shutdown"], 1)
        self.assertEqual(calls["closed"], 1)

    def test_socket_init_maps_connection_refused_to_original_exception(self) -> None:
        from voc_app.gui.socket_client import SocketCommunicator
        import voc_app.utils.resource_manager as resource_manager_module

        class DummySocket:
            def settimeout(self, timeout: float) -> None:  # noqa: ANN001
                self._timeout = timeout

            def connect(self, addr) -> None:  # noqa: ANN001
                raise ConnectionRefusedError("refused")

            def shutdown(self, how: int) -> None:  # noqa: ANN001
                return None

            def close(self) -> None:
                return None

        with patch.object(resource_manager_module.socket, "socket", return_value=DummySocket()):
            with self.assertRaises(ConnectionRefusedError):
                SocketCommunicator("127.0.0.1", 1, timeout=0.1)


class TestSerialCommunicatorOptionalDependency(unittest.TestCase):
    def test_serial_missing_raises_runtime_error(self) -> None:
        import voc_app.gui.socket_client as socket_client

        with patch.object(socket_client, "serial", None):
            with self.assertRaises(RuntimeError):
                socket_client.SerialCommunicator("/dev/ttyS0", 9600, timeout=0.1)

    def test_serial_send_recv_close_with_dummy_module(self) -> None:
        import voc_app.gui.socket_client as socket_client

        calls: dict[str, int] = {"write": 0, "read": 0, "flush": 0, "close": 0}

        class DummySerialException(Exception):
            pass

        class DummySerial:
            def __init__(self, port: str, baudrate: int, timeout: float):  # noqa: ANN001
                self._port = port
                self._baudrate = baudrate
                self._timeout = timeout

            def write(self, data: bytes) -> None:
                calls["write"] += 1
                self._last = data

            def read(self, size: int) -> bytes:
                calls["read"] += 1
                return b"x" * size

            def flush(self) -> None:
                calls["flush"] += 1
                raise DummySerialException("flush boom")

            def close(self) -> None:
                calls["close"] += 1

        dummy_serial_module = types.SimpleNamespace(  # type: ignore[assignment]
            Serial=DummySerial,
            SerialException=DummySerialException,
        )

        with patch.object(socket_client, "serial", dummy_serial_module):
            comm = socket_client.SerialCommunicator("/dev/ttyS0", 9600, timeout=0.1)
            comm.send(b"abc")
            self.assertEqual(comm.recv(3), b"xxx")
            comm.close()

        self.assertEqual(calls["write"], 1)
        self.assertEqual(calls["read"], 1)
        self.assertEqual(calls["flush"], 1)
        self.assertEqual(calls["close"], 1)


class TestClientDirectoryTransfer(unittest.TestCase):
    def test_get_file_directory_protocol(self) -> None:
        from voc_app.gui.socket_client import Client, Communicator

        class DummyCommunicator(Communicator):
            def __init__(self, payload: bytes) -> None:
                self._buf = bytearray(payload)
                self._sent = bytearray()
                self._closed = False

            def send(self, data: bytes) -> None:
                self._sent.extend(data)

            def recv(self, size: int) -> bytes:
                if not self._buf:
                    return b""
                chunk = bytes(self._buf[:size])
                del self._buf[:size]
                return chunk

            def close(self) -> None:
                self._closed = True

        def pack_msg(text: str) -> bytes:
            b = text.encode("utf-8")
            return struct.pack(">I", len(b)) + b

        file_content = b"abc"
        stream = (
            pack_msg("D_START /remote/dir")
            + pack_msg(f"FILE /remote/dir/a.txt {len(file_content)}")
            + file_content
            + pack_msg("D_END /remote/dir")
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            comm = DummyCommunicator(stream)
            client = Client(comm)
            saved_files = client.get_file("/remote/dir", tmpdir)
            client.close()
            self.assertEqual(len(saved_files), 1)
            self.assertTrue(os.path.exists(saved_files[0]))
            with open(saved_files[0], "rb") as f:  # noqa: PTH123
                self.assertEqual(f.read(), file_content)

        self.assertTrue(comm._closed)

    def test_get_file_directory_out_of_order_end_raises(self) -> None:
        from voc_app.gui.socket_client import Client, Communicator

        class DummyCommunicator(Communicator):
            def __init__(self, payload: bytes) -> None:
                self._buf = bytearray(payload)

            def send(self, data: bytes) -> None:
                return None

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

        stream = pack_msg("D_START /remote/dir") + pack_msg("D_END /remote/other")
        with tempfile.TemporaryDirectory() as tmpdir:
            client = Client(DummyCommunicator(stream))
            with self.assertRaises(RuntimeError):
                client.get_file("/remote/dir", tmpdir)


class TestGPIOControllerContextManager(unittest.TestCase):
    def test_gpio_controller_context_manager_calls_cleanup(self) -> None:
        # 通过注入 dummy RPi.GPIO，覆盖无树莓派依赖环境下的导入问题
        dummy_gpio = types.ModuleType("RPi.GPIO")
        dummy_gpio.BCM = 0  # type: ignore[attr-defined]
        dummy_gpio.IN = 1  # type: ignore[attr-defined]
        dummy_gpio.OUT = 2  # type: ignore[attr-defined]
        dummy_gpio.PUD_UP = 3  # type: ignore[attr-defined]
        dummy_gpio.PUD_DOWN = 4  # type: ignore[attr-defined]
        dummy_gpio.HIGH = 1  # type: ignore[attr-defined]
        dummy_gpio.LOW = 0  # type: ignore[attr-defined]
        dummy_gpio._cleanup_calls = 0  # type: ignore[attr-defined]

        def _noop(*args, **kwargs):  # noqa: ANN001
            return None

        def _cleanup() -> None:
            dummy_gpio._cleanup_calls += 1  # type: ignore[attr-defined]

        dummy_gpio.setmode = _noop  # type: ignore[attr-defined]
        dummy_gpio.setup = _noop  # type: ignore[attr-defined]
        dummy_gpio.output = _noop  # type: ignore[attr-defined]
        dummy_gpio.input = lambda pin: 0  # noqa: E731, ANN001
        dummy_gpio.cleanup = _cleanup  # type: ignore[attr-defined]

        sys.modules["RPi"] = types.ModuleType("RPi")
        sys.modules["RPi.GPIO"] = dummy_gpio

        # 重新导入以拾取 dummy RPi.GPIO
        import importlib

        gpio_controller = importlib.reload(importlib.import_module("voc_app.loadport.gpio_controller"))

        ctrl = gpio_controller.GPIOController(  # type: ignore[attr-defined]
            input_pins_config={"A": 1},
            output_pins_config={"B": 2},
            PUL_Status=1,
            default_state=True,
        )
        with ctrl:
            _ = ctrl.read_all_inputs()
        self.assertEqual(dummy_gpio._cleanup_calls, 1)  # type: ignore[attr-defined]


class TestE84ControllerResourceRelease(unittest.TestCase):
    def test_e84_close_stops_timers_and_cleans_gpio(self) -> None:
        from voc_app.loadport import e84_passive as e84_module

        _ensure_qt_app()
        calls: dict[str, int] = {"cleanup": 0}

        class DummyGPIOController:
            def __init__(self, input_pins_config, output_pins_config, *args, **kwargs):  # noqa: ANN001
                self._inputs = list(getattr(input_pins_config, "keys", lambda: [])())
                self._outputs = list(getattr(output_pins_config, "keys", lambda: [])())
                self.output_calls: list[tuple[str, bool]] = []
                self.all_output_calls: list[bool] = []

            def read_all_inputs(self) -> dict[str, bool]:
                return {name: False for name in self._inputs}

            def set_output(self, pin_name: str, state: bool) -> None:  # noqa: ARG002
                self.output_calls.append((pin_name, bool(state)))
                return None

            def set_all_outputs(self, state: bool) -> None:  # noqa: ARG002
                self.all_output_calls.append(bool(state))
                return None

            def cleanup(self) -> None:
                calls["cleanup"] += 1

        with patch.object(e84_module, "GPIOController", DummyGPIOController):
            ctrl = e84_module.E84Controller(refresh_interval=0.01)
            ctrl.start()
            self.assertTrue(ctrl.refresh_timer.isActive())
            ctrl.close()
            self.assertFalse(ctrl.refresh_timer.isActive())
            self.assertFalse(ctrl.timeout_timer.isActive())
            # 两个 GPIOController 都注册了 cleanup 回调
            self.assertEqual(calls["cleanup"], 2)
        # 无 PySide6 环境下依旧应可通过内部 stub 运行并完成资源释放校验

    def test_e84_state_machine_flow_emits_start_and_stop(self) -> None:
        from voc_app.loadport import e84_passive as e84_module

        _ensure_qt_app()
        events: list[str] = []

        class DummyGPIOController:
            def __init__(self, input_pins_config, output_pins_config, *args, **kwargs):  # noqa: ANN001
                self._inputs = list(getattr(input_pins_config, "keys", lambda: [])())
                self.output_calls: list[tuple[str, bool]] = []

            def read_all_inputs(self) -> dict[str, bool]:
                return {name: False for name in self._inputs}

            def set_output(self, pin_name: str, state: bool) -> None:
                self.output_calls.append((pin_name, bool(state)))

            def set_all_outputs(self, state: bool) -> None:  # noqa: ARG002
                return None

            def cleanup(self) -> None:
                return None

        with patch.object(e84_module, "GPIOController", DummyGPIOController):
            ctrl = e84_module.E84Controller(refresh_interval=0.01)
            ctrl.data_collection_start.connect(lambda: events.append("start"))  # type: ignore[attr-defined]
            ctrl.data_collection_stop.connect(lambda: events.append("stop"))  # type: ignore[attr-defined]

            # 1) IDLE -> WAIT_TR_REQ（握手条件满足，且 FOUP_status=True 时发出 start）
            ctrl.FOUP_status = True
            ctrl.E84_InSig_Value.update({"GO": True, "CS_0": True, "VALID": True})
            ctrl._process_state()
            self.assertEqual(ctrl.state, e84_module.E84State.WAIT_TR_REQ)
            self.assertIn("start", events)

            # 2) WAIT_TR_REQ -> WAIT_BUSY（TR_REQ=1）
            ctrl.E84_InSig_Value.update({"TR_REQ": True})
            ctrl._process_state()
            self.assertEqual(ctrl.state, e84_module.E84State.WAIT_BUSY)

            # 3) WAIT_BUSY -> WAIT_U_REQ（BUSY=1，FOUP_status=True）
            ctrl.E84_InSig_Value.update({"BUSY": True})
            ctrl._process_state()
            self.assertEqual(ctrl.state, e84_module.E84State.WAIT_U_REQ)

            # 4) WAIT_U_REQ -> WAIT_COMPT（FOUP_status 变为 False，表示移走）
            ctrl.FOUP_status = False
            ctrl._process_state()
            self.assertEqual(ctrl.state, e84_module.E84State.WAIT_COMPT)

            # 5) WAIT_COMPT -> WAIT_DONE（COMPT=1，且 FOUP_status=False 时发出 stop）
            ctrl.E84_InSig_Value.update({"COMPT": True})
            ctrl._process_state()
            self.assertEqual(ctrl.state, e84_module.E84State.WAIT_DONE)
            self.assertIn("stop", events)

            # 6) WAIT_DONE -> IDLE（CS_0/VALID/COMPT 都为 0）
            ctrl.E84_InSig_Value.update({"CS_0": False, "VALID": False, "COMPT": False})
            ctrl._process_state()
            self.assertEqual(ctrl.state, e84_module.E84State.IDLE)

            ctrl.close()

    def test_e84_refresh_input_key_debounce_and_led_paths(self) -> None:
        from voc_app.loadport import e84_passive as e84_module

        _ensure_qt_app()
        warnings: list[str] = []
        key_events: list[str] = []

        class DummyPin:
            def __init__(self, reads: list[dict[str, bool]]) -> None:
                self._reads = list(reads)
                self.output_calls: list[tuple[str, bool]] = []
                self.all_output_calls: list[bool] = []

            def read_all_inputs(self) -> dict[str, bool]:
                if self._reads:
                    return self._reads.pop(0)
                return {}

            def set_output(self, pin_name: str, state: bool) -> None:
                self.output_calls.append((pin_name, bool(state)))

            def set_all_outputs(self, state: bool) -> None:
                self.all_output_calls.append(bool(state))

            def cleanup(self) -> None:
                return None

        class DummyGPIOController:
            def __init__(self, input_pins_config, output_pins_config, *args, **kwargs):  # noqa: ANN001
                self._inputs = list(getattr(input_pins_config, "keys", lambda: [])())

            def read_all_inputs(self) -> dict[str, bool]:
                return {name: False for name in self._inputs}

            def set_output(self, pin_name: str, state: bool) -> None:  # noqa: ARG002
                return None

            def set_all_outputs(self, state: bool) -> None:  # noqa: ARG002
                return None

            def cleanup(self) -> None:
                return None

        with patch.object(e84_module, "GPIOController", DummyGPIOController):
            ctrl = e84_module.E84Controller(refresh_interval=0.01)
            ctrl.warning.connect(lambda msg: warnings.append(str(msg)))  # type: ignore[attr-defined]
            ctrl.all_keys_set.connect(lambda: key_events.append("all_keys_set"))  # type: ignore[attr-defined]

            # 覆盖 debounce：旧值与新值不同会 sleep 再读一次
            sig_reads = [
                {"GO": False, "CS_0": False, "VALID": False, "TR_REQ": False, "BUSY": False, "COMPT": False},
            ]
            key_reads = [
                {"KEY_0": False, "KEY_1": False, "KEY_2": False},
                {"KEY_0": True, "KEY_1": True, "KEY_2": True},
                {"KEY_0": True, "KEY_1": True, "KEY_2": True},
            ]
            ctrl.E84_SigPin = DummyPin(sig_reads)  # type: ignore[assignment]
            ctrl.E84_InfoPin = DummyPin(key_reads)  # type: ignore[assignment]
            # 强制触发 debounce 分支：首次读到的 Key_Value 与 Old_Value 不同
            ctrl.E84_Key_Old_Value = {"KEY_0": True, "KEY_1": True, "KEY_2": True}

            with patch.object(e84_module.time, "sleep", return_value=None):
                ctrl.led_cnt = 4
                ctrl.Refresh_Input()

            # all_keys_on=True 时应触发 all_keys_set
            self.assertIn("all_keys_set", key_events)
            # GO=False 时应发出 warning
            self.assertTrue(any("GO 信号为低" in w for w in warnings))
            # led_cnt==5 时点亮 CODE_LED
            info_calls = getattr(ctrl.E84_InfoPin, "output_calls", [])
            self.assertTrue(any(name == "CODE_LED" for name, _ in info_calls))

            # 覆盖 E84_TestOutPin（sleep 打补丁避免等待）
            with patch.object(e84_module.time, "sleep", return_value=None):
                ctrl.E84_SigPin = DummyPin(sig_reads)  # type: ignore[assignment]
                ctrl.E84_TestOutPin()
                self.assertEqual(getattr(ctrl.E84_SigPin, "all_output_calls", []), [bool(e84_module.SIG_OFF), bool(e84_module.SIG_ON)])

            ctrl.close()

    def test_e84_init_gpio_failure_raises(self) -> None:
        from voc_app.loadport import e84_passive as e84_module
        from voc_app.utils.error_handler import VOCError

        _ensure_qt_app()

        class BadGPIOController:
            def __init__(self, *args, **kwargs):  # noqa: ANN001
                raise VOCError("bad gpio")

        with patch.object(e84_module, "GPIOController", BadGPIOController):
            with self.assertRaises(VOCError):
                e84_module.E84Controller(refresh_interval=0.01)

    def test_e84_run_cycle_handles_voc_error(self) -> None:
        from voc_app.loadport import e84_passive as e84_module
        from voc_app.utils.error_handler import VOCError

        _ensure_qt_app()

        class DummyGPIOController:
            def __init__(self, input_pins_config, output_pins_config, *args, **kwargs):  # noqa: ANN001
                self._inputs = list(getattr(input_pins_config, "keys", lambda: [])())

            def read_all_inputs(self) -> dict[str, bool]:
                return {name: False for name in self._inputs}

            def set_output(self, pin_name: str, state: bool) -> None:  # noqa: ARG002
                return None

            def set_all_outputs(self, state: bool) -> None:  # noqa: ARG002
                return None

            def cleanup(self) -> None:
                return None

        with patch.object(e84_module, "GPIOController", DummyGPIOController):
            ctrl = e84_module.E84Controller(refresh_interval=0.01)

            def boom() -> None:
                raise VOCError("boom")

            ctrl.Refresh_Input = boom  # type: ignore[assignment]
            ctrl._run_cycle()
            self.assertTrue(ctrl._closed)

    def test_e84_init_refresh_input_failure_raises(self) -> None:
        from voc_app.loadport import e84_passive as e84_module
        from voc_app.utils.error_handler import VOCError

        _ensure_qt_app()

        class DummyGPIOController:
            def __init__(self, input_pins_config, output_pins_config, *args, **kwargs):  # noqa: ANN001
                self._inputs = list(getattr(input_pins_config, "keys", lambda: [])())

            def read_all_inputs(self) -> dict[str, bool]:
                return {name: False for name in self._inputs}

            def set_output(self, pin_name: str, state: bool) -> None:  # noqa: ARG002
                return None

            def set_all_outputs(self, state: bool) -> None:  # noqa: ARG002
                return None

            def cleanup(self) -> None:
                return None

        with patch.object(e84_module, "GPIOController", DummyGPIOController):
            with patch.object(
                e84_module.E84Controller,
                "Refresh_Input",
                side_effect=VOCError("refresh boom"),
            ):
                with self.assertRaises(VOCError):
                    e84_module.E84Controller(refresh_interval=0.01)

    def test_e84_stop_and_timeout_branches(self) -> None:
        from voc_app.loadport import e84_passive as e84_module

        _ensure_qt_app()
        warnings: list[str] = []

        class DummyGPIOController:
            def __init__(self, input_pins_config, output_pins_config, *args, **kwargs):  # noqa: ANN001
                self._inputs = list(getattr(input_pins_config, "keys", lambda: [])())
                self.output_calls: list[tuple[str, bool]] = []

            def read_all_inputs(self) -> dict[str, bool]:
                return {name: False for name in self._inputs}

            def set_output(self, pin_name: str, state: bool) -> None:
                self.output_calls.append((pin_name, bool(state)))

            def set_all_outputs(self, state: bool) -> None:  # noqa: ARG002
                return None

            def cleanup(self) -> None:
                return None

        with patch.object(e84_module, "GPIOController", DummyGPIOController):
            ctrl = e84_module.E84Controller(refresh_interval=0.01)
            ctrl.warning.connect(lambda msg: warnings.append(str(msg)))  # type: ignore[attr-defined]

            ctrl.start()
            self.assertTrue(ctrl.refresh_timer.isActive())
            ctrl.stop()
            self.assertFalse(ctrl.refresh_timer.isActive())

            # WAIT_TR_REQ 超时分支
            ctrl.state = e84_module.E84State.WAIT_TR_REQ
            ctrl.timeout_expired = True
            ctrl._process_state()
            self.assertEqual(ctrl.state, e84_module.E84State.IDLE)
            self.assertTrue(any("TR_REQ" in w for w in warnings))

            # WAIT_BUSY 超时分支
            ctrl.state = e84_module.E84State.WAIT_BUSY
            ctrl.timeout_expired = True
            ctrl._process_state()
            self.assertEqual(ctrl.state, e84_module.E84State.IDLE)
            self.assertTrue(any("BUSY" in w for w in warnings))

            # WAIT_L_REQ 信号中断分支（握手线断开）
            ctrl.state = e84_module.E84State.WAIT_L_REQ
            ctrl.E84_InSig_Value.update({"CS_0": False, "VALID": True, "TR_REQ": True, "BUSY": True})
            ctrl._process_state()
            self.assertEqual(ctrl.state, e84_module.E84State.IDLE)
            self.assertTrue(any("L_REQ" in w for w in warnings))

            # WAIT_U_REQ 信号中断分支（握手线断开）
            ctrl.state = e84_module.E84State.WAIT_U_REQ
            ctrl.E84_InSig_Value.update({"CS_0": True, "VALID": False, "TR_REQ": True, "BUSY": True})
            ctrl._process_state()
            self.assertEqual(ctrl.state, e84_module.E84State.IDLE)
            self.assertTrue(any("U_REQ" in w for w in warnings))

            # _on_timeout/_consume_timeout
            ctrl._on_timeout()
            self.assertTrue(ctrl._consume_timeout())
            self.assertFalse(ctrl._consume_timeout())

            ctrl.close()

    def test_e84_handoff_load_branch_and_context_manager(self) -> None:
        from voc_app.loadport import e84_passive as e84_module

        _ensure_qt_app()

        class DummyGPIOController:
            def __init__(self, input_pins_config, output_pins_config, *args, **kwargs):  # noqa: ANN001
                self._inputs = list(getattr(input_pins_config, "keys", lambda: [])())
                self.output_calls: list[tuple[str, bool]] = []

            def read_all_inputs(self) -> dict[str, bool]:
                return {name: False for name in self._inputs}

            def set_output(self, pin_name: str, state: bool) -> None:
                self.output_calls.append((pin_name, bool(state)))

            def set_all_outputs(self, state: bool) -> None:  # noqa: ARG002
                return None

            def cleanup(self) -> None:
                return None

        with patch.object(e84_module, "GPIOController", DummyGPIOController):
            with e84_module.E84Controller(refresh_interval=0.01) as ctrl:
                ctrl.FOUP_status = False
                ctrl.E84_InSig_Value.update({"GO": True, "CS_0": True, "VALID": True})
                self.assertEqual(ctrl.E84Handoff(), 1)
                # Load 分支会拉高 L_REQ
                sig_outputs = getattr(ctrl.E84_SigPin, "output_calls", [])
                self.assertTrue(any(name == "L_REQ" for name, _ in sig_outputs))

            self.assertTrue(ctrl._closed)

    def test_e84_refresh_input_partial_keys_and_go_true(self) -> None:
        from voc_app.loadport import e84_passive as e84_module

        _ensure_qt_app()

        class DummyPin:
            def __init__(self, reads: list[dict[str, bool]]) -> None:
                self._reads = list(reads)
                self.output_calls: list[tuple[str, bool]] = []

            def read_all_inputs(self) -> dict[str, bool]:
                if self._reads:
                    return self._reads.pop(0)
                return {"GO": True, "CS_0": False, "VALID": False, "TR_REQ": False, "BUSY": False, "COMPT": False}

            def set_output(self, pin_name: str, state: bool) -> None:
                self.output_calls.append((pin_name, bool(state)))

            def set_all_outputs(self, state: bool) -> None:  # noqa: ARG002
                return None

            def cleanup(self) -> None:
                return None

        class DummyGPIOController:
            def __init__(self, input_pins_config, output_pins_config, *args, **kwargs):  # noqa: ANN001
                self._inputs = list(getattr(input_pins_config, "keys", lambda: [])())

            def read_all_inputs(self) -> dict[str, bool]:
                return {name: False for name in self._inputs}

            def set_output(self, pin_name: str, state: bool) -> None:  # noqa: ARG002
                return None

            def set_all_outputs(self, state: bool) -> None:  # noqa: ARG002
                return None

            def cleanup(self) -> None:
                return None

        with patch.object(e84_module, "GPIOController", DummyGPIOController):
            ctrl = e84_module.E84Controller(refresh_interval=0.01)

            # any_key=True 但 all_keys_on=False
            ctrl.E84_SigPin = DummyPin([{"GO": True, "CS_0": False, "VALID": False, "TR_REQ": False, "BUSY": False, "COMPT": False}])  # type: ignore[assignment]
            ctrl.E84_InfoPin = DummyPin([{"KEY_0": True, "KEY_1": False, "KEY_2": False}])  # type: ignore[assignment]
            ctrl.E84_Key_Old_Value = {"KEY_0": True, "KEY_1": False, "KEY_2": False}
            ctrl.led_cnt = 9
            ctrl.Refresh_Input()

            info_calls = getattr(ctrl.E84_InfoPin, "output_calls", [])
            self.assertTrue(any(name == "SENSOR_LED" and state is bool(e84_module.LED_ON) for name, state in info_calls))
            # led_cnt==10 时熄灭 CODE_LED
            self.assertTrue(any(name == "CODE_LED" and state is bool(e84_module.LED_OFF) for name, state in info_calls))

            # led_cnt>10 分支
            ctrl.E84_SigPin = DummyPin([{"GO": True, "CS_0": False, "VALID": False, "TR_REQ": False, "BUSY": False, "COMPT": False}])  # type: ignore[assignment]
            ctrl.E84_InfoPin = DummyPin([{"KEY_0": False, "KEY_1": False, "KEY_2": False}])  # type: ignore[assignment]
            ctrl.E84_Key_Old_Value = {"KEY_0": False, "KEY_1": False, "KEY_2": False}
            ctrl.led_cnt = 11
            ctrl.Refresh_Input()

            ctrl.close()
