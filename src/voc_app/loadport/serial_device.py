"""串口兼容层：保留 GenericSerialDevice API，内部实现尽量简化。"""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Any, Callable, Optional

from voc_app.logging_config import get_logger

logger = get_logger(__name__)

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover - 允许在测试中注入 serial_factory
    serial = None


ParserFn = Callable[[bytes, "GenericSerialDevice"], None]
ResponseParserFn = Callable[[bytes, "GenericSerialDevice"], Any]
ResponseHandlerFn = Callable[[Any, "GenericSerialDevice"], None]


@dataclass
class GenericSerialCommand:
    """命令定义：只保留最小必要字段。"""

    name: str
    build_frame: Callable[..., bytes]
    response_parser: Optional[ResponseParserFn] = None
    response_handler: Optional[ResponseHandlerFn] = None


class GenericSerialDevice:
    """简化后的通用串口设备。"""

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
        serial_factory: Optional[Callable[..., Any]] = None,
        command_table: Optional[dict[str, GenericSerialCommand]] = None,
        parser: Optional[ParserFn] = None,
        idle_sleep: float = 0.01,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.idle_sleep = idle_sleep

        self._serial_factory = serial_factory or self._default_serial_factory
        self._serial: Any | None = None
        self._reader_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._write_lock = threading.Lock()
        self._last_error: Exception | None = None

        self.command_table = command_table or {}
        self.parser: ParserFn = parser or self._default_parser
        self.raw_listeners: list[Callable[[bytes], None]] = []

    def _default_serial_factory(self, **kwargs: Any) -> Any:
        if serial is None:
            raise RuntimeError("pyserial 未安装，请传入 serial_factory 或安装 pyserial")
        return serial.Serial(**kwargs)

    def start(self) -> None:
        if self._serial and getattr(self._serial, "is_open", False):
            return
        self._serial = self._serial_factory(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )
        self._stop_event.clear()
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
        self._reader_thread = None

        if self._serial and getattr(self._serial, "is_open", False):
            self._serial.close()
        self._serial = None

    def __enter__(self) -> "GenericSerialDevice":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    def register_command(self, command: GenericSerialCommand) -> None:
        self.command_table[command.name] = command

    def add_raw_listener(self, callback: Callable[[bytes], None]) -> None:
        self.raw_listeners.append(callback)

    def send_raw(self, data: bytes) -> None:
        if not self._serial or not getattr(self._serial, "is_open", False):
            raise RuntimeError("串口尚未启动，请先调用 start()")
        with self._write_lock:
            self._serial.write(data)

    def send_command(self, name: str, **build_kwargs: Any) -> bytes:
        command = self.command_table.get(name)
        if command is None:
            raise KeyError(f"未找到命令: {name}")
        frame = command.build_frame(**build_kwargs)
        self.send_raw(frame)
        return frame

    def handle_response(self, command_name: str, payload: bytes) -> None:
        command = self.command_table.get(command_name)
        if command is None:
            logger.warning(f"未注册命令 {command_name}, 忽略响应")
            return

        parsed: Any = payload
        if command.response_parser:
            parsed = command.response_parser(payload, self)
        if command.response_handler:
            command.response_handler(parsed, self)

    def _reader_loop(self) -> None:
        assert self._serial is not None
        serial_obj = self._serial

        while not self._stop_event.is_set() and getattr(serial_obj, "is_open", False):
            try:
                waiting = getattr(serial_obj, "in_waiting", 0)
                size = waiting if waiting else 1
                chunk = serial_obj.read(size)
                if chunk:
                    self._dispatch_chunk(chunk)
                else:
                    time.sleep(self.idle_sleep)
            except Exception as exc:  # noqa: BLE001
                self._last_error = exc
                logger.error(f"读取线程异常: {exc}")
                break

    def _dispatch_chunk(self, chunk: bytes) -> None:
        for listener in self.raw_listeners:
            listener(chunk)
        self.parser(chunk, self)

    @staticmethod
    def _default_parser(chunk: bytes, device: "GenericSerialDevice") -> None:
        logger.debug(f"接收到 {len(chunk)} 字节: {chunk.hex()}")

    @property
    def last_error(self) -> Optional[Exception]:
        return self._last_error
