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
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._rx_buffer = bytearray()
        self._message_callback = message_callback
        self._idle_sleep = idle_sleep

        self._serial_factory = serial_factory or self._default_serial_factory
        self._serial: Any | None = None
        self._reader_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._write_lock = threading.Lock()
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
        if not self._serial or not getattr(self._serial, "is_open", False):
            raise RuntimeError("串口尚未连接，请先调用 connect()")

    def _reader_loop(self) -> None:
        assert self._serial is not None
        serial_obj = self._serial
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
                self._last_error = exc
                logger.error(f"串口读取异常: {exc}")
                break

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
        if self._serial and getattr(self._serial, "is_open", False):
            return
        self._rx_buffer.clear()
        self._last_error = None
        self._serial = self._serial_factory(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )
        self._stop_event.clear()
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
        self._reader_thread = None
        if self._serial and getattr(self._serial, "is_open", False):
            self._serial.close()
        self._serial = None

    def __enter__(self) -> "AsciiSerialClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    def send_raw(self, data: bytes) -> None:
        self._ensure_connected()
        with self._write_lock:
            self._serial.write(data)

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
        return bool(self._serial and getattr(self._serial, "is_open", False))

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
