"""GenericSerialDevice 兼容层测试。"""

from __future__ import annotations

import queue
import time
import unittest

from voc_app.loadport.serial_device import GenericSerialCommand, GenericSerialDevice


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


class GenericSerialDeviceCompatTests(unittest.TestCase):
    def test_send_command_and_handle_response(self) -> None:
        stub_serial = InMemorySerial()

        def factory(**_kwargs):
            return stub_serial

        responses: list[str] = []

        def parser(chunk: bytes, device: GenericSerialDevice) -> None:
            device.handle_response("ping", chunk)

        ping_command = GenericSerialCommand(
            name="ping",
            build_frame=lambda payload=b"": b"\x02" + payload,
            response_parser=lambda raw, _device: raw.decode("ascii"),
            response_handler=lambda parsed, _device: responses.append(parsed),
        )

        device = GenericSerialDevice(
            port="loopback",
            serial_factory=factory,
            command_table={"ping": ping_command},
            parser=parser,
            idle_sleep=0.001,
        )
        self.addCleanup(device.stop)
        device.start()

        frame = device.send_command("ping", payload=b"OK")
        self.assertEqual(frame, b"\x02OK")
        self.assertEqual(stub_serial.written, [b"\x02OK"])

        stub_serial.feed(b"OK")
        end_at = time.time() + 0.5
        while time.time() < end_at and not responses:
            time.sleep(0.01)

        self.assertIn("OK", responses)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
