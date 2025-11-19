import queue
import threading
import time
import unittest

from new_loadport.serial_device import GenericSerialCommand, GenericSerialDevice


class InMemorySerial:
    """简单的内存串口，用于测试读写流程。"""

    def __init__(self):
        self.buffer = queue.Queue()
        self.is_open = True
        self.written = []

    @property
    def in_waiting(self) -> int:
        return self.buffer.qsize()

    def read(self, size: int = 1) -> bytes:
        try:
            data = self.buffer.get(timeout=0.05)
            return data
        except queue.Empty:
            return b""

    def write(self, data: bytes) -> int:
        self.written.append(data)
        return len(data)

    def close(self) -> None:
        self.is_open = False

    # 测试辅助函数
    def feed(self, data: bytes) -> None:
        if not self.is_open:
            raise RuntimeError("串口已关闭")
        self.buffer.put(data)


class GenericSerialDeviceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stub_serial = InMemorySerial()

        def factory(**_kwargs):
            return self.stub_serial

        self.responses = []

        def parser(chunk: bytes, device: GenericSerialDevice) -> None:
            # 简单示例：所有数据都按 ping 命令处理
            device.handle_response("ping", chunk)

        ping_command = GenericSerialCommand(
            name="ping",
            build_frame=lambda payload=b"": b"\x02" + payload,
            response_parser=lambda raw, _device: raw.decode("ascii"),
            response_handler=lambda parsed, _device: self.responses.append(parsed),
        )

        self.device = GenericSerialDevice(
            port="loopback",
            serial_factory=factory,
            command_table={"ping": ping_command},
            parser=parser,
        )
        self.device.start()

    def tearDown(self) -> None:
        self.device.stop()

    def test_send_command_and_handle_response(self) -> None:
        frame = self.device.send_command("ping", payload=b"OK")
        self.assertEqual(frame, b"\x02OK")
        self.assertEqual(self.stub_serial.written, [b"\x02OK"])

        self.stub_serial.feed(b"OK")
        time.sleep(0.1)
        self.assertIn("OK", self.responses)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
