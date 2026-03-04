"""AsciiSerialClient 简化实现的单元测试。"""

from __future__ import annotations

import queue
import time
import unittest

from voc_app.loadport.ascii_serial import AsciiSerialClient


class InMemorySerial:
    """简单内存串口，用于模拟读写。"""

    def __init__(self) -> None:
        self.buffer: queue.Queue[bytes] = queue.Queue()
        self.written: list[bytes] = []
        self.is_open = True

    @property
    def in_waiting(self) -> int:
        return self.buffer.qsize()

    def read(self, size: int = 1) -> bytes:
        try:
            return self.buffer.get(timeout=0.05)
        except queue.Empty:
            return b""

    def write(self, data: bytes) -> int:
        self.written.append(data)
        return len(data)

    def close(self) -> None:
        self.is_open = False

    def feed(self, data: bytes) -> None:
        if not self.is_open:
            raise RuntimeError("串口已关闭")
        self.buffer.put(data)


class AsciiSerialClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stub_serial = InMemorySerial()
        self.received: list[str] = []

        def factory(**_kwargs):
            return self.stub_serial

        self.client = AsciiSerialClient(
            port="loopback",
            message_callback=self.received.append,
            serial_factory=factory,
            idle_sleep=0.001,
        )
        self.client.connect()

    def tearDown(self) -> None:
        self.client.disconnect()

    def _wait_until(self, predicate, timeout: float = 0.5) -> bool:
        end_at = time.time() + timeout
        while time.time() < end_at:
            if predicate():
                return True
            time.sleep(0.01)
        return False

    def test_business_commands_are_easy_to_send(self) -> None:
        self.client.home()
        self.client.reset()
        self.client.set_servo(True)
        self.client.move_to_step(4)
        self.client.send_line("custom")

        self.assertEqual(
            self.stub_serial.written,
            [
                b"home\n",
                b"reset\n",
                b"servo_on\n",
                b"move_to_step 4\n",
                b"custom\n",
            ],
        )

    def test_reader_merges_fragmented_line_and_calls_callback(self) -> None:
        self.stub_serial.feed(b"ready")
        self.stub_serial.feed(b"\nUnknown: bad\r\n")

        ok = self._wait_until(lambda: len(self.received) >= 2)
        self.assertTrue(ok)
        self.assertEqual(self.received[:2], ["ready", "Unknown: bad"])

    def test_send_before_connect_raises_error(self) -> None:
        self.client.disconnect()
        with self.assertRaises(RuntimeError):
            self.client.home()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
