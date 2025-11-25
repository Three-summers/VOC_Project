"""通用串口通信模块。

该模块提供 GenericSerialCommand 与 GenericSerialDevice，
支持通过命令表与自定义解析逻辑快速构建串口程序。
"""

from __future__ import annotations

from dataclasses import dataclass, field
import queue
import threading
import time
from typing import Any, Callable, Dict, Optional, Protocol

try:  # 可选依赖，允许在未安装 pyserial 时注入自定义工厂
    import serial  # type: ignore
except ImportError:  # pragma: no cover - fallback 路径
    serial = None


# 约束
class SerialTransport(Protocol):
    """串口对象最小接口约束，方便注入 mock。"""

    def read(self, size: int = 1) -> bytes: ...

    def write(self, data: bytes) -> int: ...

    def close(self) -> None: ...

    @property
    def in_waiting(self) -> int: ...

    @property
    def is_open(self) -> bool: ...


# ... 表示任意参数，SerialFactory 返回 SerialTransport
SerialFactory = Callable[..., SerialTransport]
ParserFn = Callable[[bytes, "GenericSerialDevice"], None]
ResponseParserFn = Callable[[bytes, "GenericSerialDevice"], Any]
ResponseHandlerFn = Callable[[Any, "GenericSerialDevice"], None]


@dataclass
class GenericSerialCommand:
    """命令定义，包含构帧与响应处理信息。"""

    name: str
    build_frame: Callable[..., bytes]
    response_parser: Optional[ResponseParserFn] = None
    response_handler: Optional[ResponseHandlerFn] = None
    # 预留字段
    metadata: Dict[str, Any] = field(default_factory=dict)


class GenericSerialDevice:
    """可注入命令表与自定义解析逻辑的串口设备。"""

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
        serial_factory: Optional[SerialFactory] = None,
        command_table: Optional[Dict[str, GenericSerialCommand]] = None,
        parser: Optional[ParserFn] = None,
        idle_sleep: float = 0.01,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        # 串口可支持自测
        self._serial_factory = serial_factory or self._default_serial_factory
        self._serial: Optional[SerialTransport] = None

        # 接收解析线程
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._write_lock = threading.Lock()

        self._last_error: Optional[Exception] = None
        self.idle_sleep = idle_sleep

        # 命令表用于解析
        self.command_table: Dict[str, GenericSerialCommand] = command_table or {}
        self.parser: ParserFn = parser or self._default_parser
        # 用于广播机制，用于在解析之前依次执行其中的回调函数，但要注意不能存在耗时操作
        self.raw_listeners: list[Callable[[bytes], None]] = []

    # ------------------------------------------------------------------
    # 生命周期管理
    # ------------------------------------------------------------------
    def _default_serial_factory(self, **kwargs: Any) -> SerialTransport:
        if serial is None:
            raise RuntimeError(
                "pyserial 未安装，请传入 serial_factory 或安装 pyserial"
            )
        return serial.Serial(**kwargs)

    def start(self) -> None:
        # 如果属性不存在，返回 False
        if self._serial and getattr(self._serial, "is_open", False):
            return
        self._serial = self._serial_factory(
            port=self.port, baudrate=self.baudrate, timeout=self.timeout
        )
        self._stop_event.clear()
        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True
        )
        self._reader_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
        self._reader_thread = None
        if self._serial and getattr(self._serial, "is_open", False):
            self._serial.close()
        self._serial = None

    # 支持 with 操作
    def __enter__(self) -> "GenericSerialDevice":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    # ------------------------------------------------------------------
    # 命令与发送
    # ------------------------------------------------------------------
    def register_command(self, command: GenericSerialCommand) -> None:
        self.command_table[command.name] = command

    def send_raw(self, data: bytes) -> None:
        if not self._serial or not getattr(self._serial, "is_open", False):
            raise RuntimeError("串口尚未启动，请先调用 start()")
        with self._write_lock:
            self._serial.write(data)

    def send_command(self, name: str, **build_kwargs: Any) -> bytes:
        command = self.command_table.get(name)
        if not command:
            raise KeyError(f"未找到命令: {name}")
        frame = command.build_frame(**build_kwargs)
        self.send_raw(frame)
        return frame

    def handle_response(self, command_name: str, payload: bytes) -> None:
        command = self.command_table.get(command_name)
        if not command:
            print(f"[Serial] 未注册命令 {command_name}, 忽略响应")
            return
        parsed: Any = payload
        if command.response_parser:
            parsed = command.response_parser(payload, self)
        if command.response_handler:
            command.response_handler(parsed, self)

    # ------------------------------------------------------------------
    # 读取与解析
    # ------------------------------------------------------------------
    def add_raw_listener(self, callback: Callable[[bytes], None]) -> None:
        self.raw_listeners.append(callback)

    def _reader_loop(self) -> None:
        assert self._serial is not None
        serial_obj = self._serial
        while not self._stop_event.is_set() and getattr(serial_obj, "is_open", False):
            try:
                # in_waiting 属性返回的是当前操作系统的串口输入缓冲区中已经接收但尚未读取的字节数
                waiting = getattr(serial_obj, "in_waiting", 0)
                size = waiting if waiting else 1
                chunk = serial_obj.read(size)
                if chunk:
                    self._dispatch_chunk(chunk)
                else:
                    time.sleep(self.idle_sleep)
            except Exception as exc:  # noqa: BLE001
                self._last_error = exc
                print(f"[Serial] 读取线程异常: {exc}")
                break

    def _dispatch_chunk(self, chunk: bytes) -> None:
        for listener in self.raw_listeners:
            listener(chunk)
        self.parser(chunk, self)

    @staticmethod
    def _default_parser(chunk: bytes, device: "GenericSerialDevice") -> None:
        print(f"[Serial] 接收到 {len(chunk)} 字节: {chunk.hex()}")

    # ------------------------------------------------------------------
    @property
    def last_error(self) -> Optional[Exception]:
        return self._last_error
