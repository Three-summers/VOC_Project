"""FoupAcquisitionController 的 E84 联动流程测试。"""

from __future__ import annotations

import struct
import unittest
from unittest.mock import patch

from voc_app.gui.foup_acquisition import FoupAcquisitionController


def _pack_message(text: str) -> bytes:
    payload = text.encode("utf-8")
    return struct.pack(">I", len(payload)) + payload


def _unpack_command(frame: bytes) -> str:
    (size,) = struct.unpack(">I", frame[:4])
    return frame[4 : 4 + size].decode("utf-8")


class FakeSocketCommunicator:
    """用于模拟长度前缀协议通信的假连接。"""

    def __init__(self, response_messages: list[str] | None = None) -> None:
        self._responses = bytearray()
        for message in response_messages or []:
            self._responses.extend(_pack_message(message))
        self.sent_payloads: list[bytes] = []
        self.closed = False

    def send(self, data: bytes) -> None:
        self.sent_payloads.append(data)

    def recv(self, size: int) -> bytes:
        if not self._responses:
            return b""
        chunk = self._responses[:size]
        del self._responses[:size]
        return bytes(chunk)

    def close(self) -> None:
        self.closed = True


class FoupAcquisitionE84Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = FoupAcquisitionController(series_models=[])

    def test_unload_sequence_queries_version_then_starts_collection(self) -> None:
        communicators: list[FakeSocketCommunicator] = []

        def factory(host: str, port: int, timeout: float | None = 5.0):
            _ = (host, port, timeout)
            comm = FakeSocketCommunicator(response_messages=["ack", "Noise,1.2.3"])
            communicators.append(comm)
            return comm

        with patch("voc_app.gui.foup_acquisition.SocketCommunicator", side_effect=factory):
            ok = self.controller.e84StartDataCollectionForUnload()

        self.assertTrue(ok)
        self.assertEqual(len(communicators), 1)
        commands = [_unpack_command(frame) for frame in communicators[0].sent_payloads]
        self.assertEqual(
            commands,
            ["get_function_version_info", "NOISE_data_coll_ctrl_start"],
        )

    def test_load_sequence_stops_collection_and_downloads_logs(self) -> None:
        communicators: list[FakeSocketCommunicator] = []

        def factory(host: str, port: int, timeout: float | None = 5.0):
            _ = (host, port, timeout)
            comm = FakeSocketCommunicator()
            communicators.append(comm)
            return comm

        self.controller._apply_server_identity(prefix="VOC")
        with patch("voc_app.gui.foup_acquisition.SocketCommunicator", side_effect=factory):
            with patch.object(
                self.controller,
                "_download_logs",
                return_value=["/tmp/fake_log.csv"],
            ) as mocked_download:
                ok = self.controller.e84StopDataCollectionForLoad()

        self.assertTrue(ok)
        mocked_download.assert_called_once()
        self.assertEqual(len(communicators), 1)
        commands = [_unpack_command(frame) for frame in communicators[0].sent_payloads]
        self.assertEqual(commands, ["VOC_data_coll_ctrl_stop"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
