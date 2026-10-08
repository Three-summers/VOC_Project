"""面向 STM32 ASCII 协议的简化串口客户端。"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from voc_app.logging_config import get_logger

logger = get_logger(__name__)

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover - 允许通过 serial_factory 注入
    serial = None


class AsciiSerialClient:
    """STM32 ASCII 串口客户端，直接提供业务命令 API。"""

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
        message_callback: Optional[Callable[[str], None]] = None,
        serial_factory: Optional[Callable[..., Any]] = None,
        idle_sleep: float = 0.01,
        connection_lost_callback: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._rx_buffer = bytearray()
        self._message_callback = message_callback
        self._connection_lost_callback = connection_lost_callback
        self._idle_sleep = idle_sleep

        self._serial_factory = serial_factory or self._default_serial_factory
        self._serial: Any | None = None
        self._reader_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._write_lock = threading.Lock()
        # 保护串口对象 / 读线程 / 失效状态的整体切换（R16）
        self._state_lock = threading.RLock()
        self._last_error: Exception | None = None
        # 兼容旧代码：历史版本通过 client.device 调用底层方法，这里直接指向自身。
        self.device = self
        self._command_builders: dict[str, Callable[..., str]] = {
            "get": lambda target: f"get {target}",
            "servo_on": lambda enable: f"servo_{'on' if enable else 'off'}",
            "home": lambda: "home",
            "reset": lambda: "reset",
            "lock": lambda: "lock",
            "unlock": lambda: "unlock",
            "connect": lambda: "connect",
            "disconnect": lambda: "disconnect",
            "move_to_step": lambda x: f"move_to_step {x}",
        }

    def _default_serial_factory(self, **kwargs: Any) -> Any:
        if serial is None:
            raise RuntimeError("pyserial 未安装，请先安装 pyserial")
        return serial.Serial(**kwargs)

    def _ensure_connected(self) -> None:
        if not self.is_connected:
            raise RuntimeError("串口尚未连接，请先调用 connect()")

    def set_connection_lost_callback(
        self, callback: Optional[Callable[[Exception], None]]
    ) -> None:
        self._connection_lost_callback = callback

    def _reader_loop(self) -> None:
        serial_obj = self._serial
        if serial_obj is None:
            return
        failure: Exception | None = None
        while not self._stop_event.is_set() and getattr(serial_obj, "is_open", False):
            try:
                waiting = getattr(serial_obj, "in_waiting", 0)
                size = waiting if waiting else 1
                chunk = serial_obj.read(size)
                if chunk:
                    self._parse_chunk(chunk)
                else:
                    time.sleep(self._idle_sleep)
            except Exception as exc:  # noqa: BLE001
                failure = exc
                logger.error(f"串口读取异常: {exc}")
                break
        if failure is not None and not self._stop_event.is_set():
            self._handle_reader_failure(serial_obj, failure)

    def _handle_reader_failure(self, serial_obj: Any, exc: Exception) -> None:
        """读线程异常退出：标记失效、释放串口并通知上层（R16）。

        这里不能 join 当前线程，也不能直接调用 ``connect()``；上层收到通知后
        在需要时可以安全地重建连接。
        """
        callback: Optional[Callable[[Exception], None]]
        with self._state_lock:
            if self._serial is not serial_obj:
                # 串口已经被重连替换，旧线程的失败不再影响当前连接
                return
            self._last_error = exc
            self._serial = None
            self._reader_thread = None
            callback = self._connection_lost_callback
        try:
            if getattr(serial_obj, "is_open", False):
                serial_obj.close()
        except Exception:  # noqa: BLE001
            logger.debug("关闭失效串口时发生异常", exc_info=True)
        if callback is not None:
            try:
                callback(exc)
            except Exception:  # noqa: BLE001
                logger.exception("串口失效回调执行失败")

    def _parse_chunk(self, chunk: bytes) -> None:
        self._rx_buffer.extend(chunk)

        while b"\n" in self._rx_buffer:
            line_bytes, _, remaining = self._rx_buffer.partition(b"\n")
            self._rx_buffer = remaining

            line_str = (
                line_bytes.replace(b"\r", b"")
                .decode("utf-8", errors="ignore")
                .strip()
            )

            if line_str:
                self._handle_valid_line(line_str)

    def _handle_valid_line(self, line: str) -> None:
        """处理完整的业务行。"""

        logger.debug(f"[STM32] << {line}")

        if line.startswith("Unknown:"):
            logger.warning(f"协议错误: {line}")

        if self._message_callback:
            self._message_callback(line)

    def set_message_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        self._message_callback = callback

    def connect(self) -> None:
        with self._state_lock:
            if self.is_connected:
                return
            # 清理上一次失效/半死状态的资源，保证能够重建读线程（R16）
            self._stop_event.set()
            old_serial = self._serial
            old_thread = self._reader_thread
            self._serial = None
            self._reader_thread = None

        if (
            old_thread is not None
            and old_thread.is_alive()
            and old_thread is not threading.current_thread()
        ):
            old_thread.join(timeout=1.0)
        if old_serial is not None and getattr(old_serial, "is_open", False):
            try:
                old_serial.close()
            except Exception:  # noqa: BLE001
                logger.debug("关闭旧串口时发生异常", exc_info=True)

        with self._state_lock:
            self._rx_buffer.clear()
            self._last_error = None
            self._stop_event.clear()
            self._serial = self._serial_factory(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
            )
            thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread = thread
            thread.start()

    def disconnect(self) -> None:
        with self._state_lock:
            self._stop_event.set()
            serial_obj = self._serial
            thread = self._reader_thread
            self._serial = None
            self._reader_thread = None

        if (
            thread is not None
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(timeout=1.0)
        if serial_obj is not None and getattr(serial_obj, "is_open", False):
            try:
                serial_obj.close()
            except Exception:  # noqa: BLE001
                logger.debug("关闭串口时发生异常", exc_info=True)

    def __enter__(self) -> "AsciiSerialClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    def send_raw(self, data: bytes) -> None:
        with self._state_lock:
            serial_obj = self._serial
            thread = self._reader_thread
            if not (
                serial_obj is not None
                and getattr(serial_obj, "is_open", False)
                and thread is not None
                and thread.is_alive()
            ):
                raise RuntimeError("串口尚未连接，请先调用 connect()")
        with self._write_lock:
            serial_obj.write(data)

    def send_line(self, line: str) -> None:
        text = line.strip()
        if not text:
            return
        self.send_raw(f"{text}\n".encode("utf-8"))

    def send_command(self, name: str, **kwargs: Any) -> None:
        builder = self._command_builders.get(name)
        if builder is None:
            raise KeyError(f"未找到命令: {name}")
        line = builder(**kwargs)
        self.send_line(line)

    @property
    def is_connected(self) -> bool:
        """串口打开且读线程仍存活才算已连接。

        R16：读线程因异常退出后，串口对象可能仍是 open 状态，如果只看
        ``serial.is_open``，界面会一直显示已连接，自动重连也永远不会触发。
        """
        with self._state_lock:
            serial_obj = self._serial
            thread = self._reader_thread
        return bool(
            serial_obj is not None
            and getattr(serial_obj, "is_open", False)
            and thread is not None
            and thread.is_alive()
        )

    @property
    def last_error(self) -> Exception | None:
        return self._last_error

    def get_param(self, target: str) -> None:
        self.send_command("get", target=target)

    def set_servo(self, enable: bool) -> None:
        self.send_command("servo_on", enable=enable)

    def home(self) -> None:
        self.send_command("home")

    def reset(self) -> None:
        self.send_command("reset")

    def set_lock(self) -> None:
        self.send_command("lock")

    def set_unlock(self) -> None:
        self.send_command("unlock")

    def set_connect(self) -> None:
        self.send_command("connect")

    def set_unconnect(self) -> None:
        self.send_command("disconnect")

    def move_to_step(self, x: int) -> None:
        self.send_command("move_to_step", x=x)
