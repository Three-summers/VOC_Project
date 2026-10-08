"""R16：串口读取线程死亡后仍显示已连接、自动重连无效。

复现口径（审查报告）：模拟读取异常后，读线程已经退出，``is_connected`` 仍为
True；再次 ``connect()`` 不创建新串口或新读线程，工厂调用次数仍为 1。

修复后的外部可观察行为：

1. 读线程异常退出后，``is_connected`` 必须变为 False；
2. ``last_error`` 记录异常，并通过 ``connection_lost_callback`` 向上层发出一次通知；
3. 再次 ``connect()`` 必须重建串口对象与读线程，接收链路恢复可用；
4. 失效后的 ``disconnect()`` 不能死锁或抛异常。
"""

from __future__ import annotations

import queue
import sys
import threading
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.loadport.ascii_serial import AsciiSerialClient


class InMemorySerial:
    """可用的内存串口。"""

    def __init__(self) -> None:
        self.buffer: queue.Queue[bytes] = queue.Queue()
        self.written: list[bytes] = []
        self.is_open = True

    @property
    def in_waiting(self) -> int:
        return self.buffer.qsize()

    def read(self, size: int = 1) -> bytes:
        try:
            return self.buffer.get(timeout=0.02)
        except queue.Empty:
            return b""

    def write(self, data: bytes) -> int:
        self.written.append(data)
        return len(data)

    def close(self) -> None:
        self.is_open = False

    def feed(self, data: bytes) -> None:
        self.buffer.put(data)


class ExplodingSerial(InMemorySerial):
    """一读到数据就抛异常，模拟 USB 掉线。"""

    def __init__(self) -> None:
        super().__init__()
        self.close_calls = 0

    def read(self, size: int = 1) -> bytes:
        raise OSError("device disconnected")

    def close(self) -> None:
        self.close_calls += 1
        super().close()


def _wait_until(predicate, timeout: float = 2.0) -> bool:
    end_at = time.time() + timeout
    while time.time() < end_at:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_reader_failure_marks_disconnected_and_reports() -> None:
    created: list[InMemorySerial] = []

    def factory(**_kwargs):
        serial_obj = ExplodingSerial() if not created else InMemorySerial()
        created.append(serial_obj)
        return serial_obj

    lost: list[Exception] = []
    received: list[str] = []
    client = AsciiSerialClient(
        port="loopback",
        message_callback=received.append,
        serial_factory=factory,
        idle_sleep=0.001,
        connection_lost_callback=lost.append,
    )
    client.connect()

    assert _wait_until(lambda: len(lost) == 1), "读线程死亡后必须向上层发出失效通知"
    assert isinstance(lost[0], OSError)
    assert client.is_connected is False, "读线程已经死亡，不能继续显示为已连接"
    assert isinstance(client.last_error, OSError)
    assert created[0].close_calls >= 1, "失效串口对象必须被释放"


def test_connect_rebuilds_reader_after_failure() -> None:
    created: list[InMemorySerial] = []

    def factory(**_kwargs):
        serial_obj = ExplodingSerial() if not created else InMemorySerial()
        created.append(serial_obj)
        return serial_obj

    received: list[str] = []
    client = AsciiSerialClient(
        port="loopback",
        message_callback=received.append,
        serial_factory=factory,
        idle_sleep=0.001,
    )
    client.connect()
    assert _wait_until(lambda: not client.is_connected)

    # app.py 的 _ensure_connected 就是在这种状态下调用 connect()
    client.connect()
    assert client.is_connected is True
    assert len(created) == 2, "必须重建串口对象"
    assert client._reader_thread is not None and client._reader_thread.is_alive()

    created[-1].feed(b"recovered\n")
    assert _wait_until(lambda: "recovered" in received), "重建后必须恢复接收"
    client.disconnect()


def test_disconnect_after_failure_is_safe() -> None:
    created: list[InMemorySerial] = []

    def factory(**_kwargs):
        serial_obj = ExplodingSerial() if not created else InMemorySerial()
        created.append(serial_obj)
        return serial_obj

    client = AsciiSerialClient(
        port="loopback", serial_factory=factory, idle_sleep=0.001
    )
    client.connect()
    assert _wait_until(lambda: not client.is_connected)

    done = threading.Event()

    def run_disconnect() -> None:
        client.disconnect()
        done.set()

    thread = threading.Thread(target=run_disconnect, daemon=True)
    thread.start()
    assert done.wait(2.0), "失效状态下 disconnect() 不能阻塞"
