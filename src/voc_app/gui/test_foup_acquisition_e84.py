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
            comm = FakeSocketCommunicator(response_messages=["ack", "VOC,V1.0.0"])
            communicators.append(comm)
            return comm

        with patch("voc_app.gui.foup_acquisition.SocketCommunicator", side_effect=factory):
            ok = self.controller.e84StartDataCollectionForUnload()

        self.assertTrue(ok)
        self.assertEqual(len(communicators), 1)
        commands = [_unpack_command(frame) for frame in communicators[0].sent_payloads]
        # 下位机 VOC_Sample_Type 是全局标志：只有先声明 normal，start 才会写 CSV。
        # 缺少 sample_type_normal 时，上一次测试模式会残留 false，整趟飞行不记录数据。
        self.assertEqual(
            commands,
            [
                "get_function_version_info",
                "VOC_sample_type_normal",
                "VOC_data_coll_ctrl_start",
            ],
        )

    def test_unload_sequence_skips_version_query_when_prefix_known(self) -> None:
        """已知前缀时不在传输关键路径上做版本查询（避免占用 BUSY 前的余量）"""
        communicators: list[FakeSocketCommunicator] = []

        def factory(host: str, port: int, timeout: float | None = 5.0):
            _ = (host, port, timeout)
            comm = FakeSocketCommunicator(response_messages=["ack"])
            communicators.append(comm)
            return comm

        self.controller._apply_server_identity(prefix="VOC")
        with patch("voc_app.gui.foup_acquisition.SocketCommunicator", side_effect=factory):
            ok = self.controller.e84StartDataCollectionForUnload()

        self.assertTrue(ok)
        commands = [_unpack_command(frame) for frame in communicators[0].sent_payloads]
        self.assertEqual(
            commands,
            ["VOC_sample_type_normal", "VOC_data_coll_ctrl_start"],
        )

    def test_load_sequence_downloads_logs_before_sending_stop(self) -> None:
        """必须先下载再发 STOP：下位机收到 stop 后 5 秒会反挂载 SD 分区"""
        communicators: list[FakeSocketCommunicator] = []
        events: list[str] = []

        def factory(host: str, port: int, timeout: float | None = 5.0):
            _ = (host, port, timeout)
            comm = FakeSocketCommunicator()
            original_send = comm.send

            def send_recording(data: bytes) -> None:
                events.append(f"send:{_unpack_command(data)}")
                original_send(data)

            comm.send = send_recording  # type: ignore[method-assign]
            communicators.append(comm)
            return comm

        def fake_download() -> list[str]:
            events.append("download")
            return ["/tmp/fake_log.csv"]

        self.controller._apply_server_identity(prefix="VOC")
        with patch("voc_app.gui.foup_acquisition.SocketCommunicator", side_effect=factory):
            with patch.object(
                self.controller, "_download_logs", side_effect=fake_download
            ) as mocked_download:
                ok = self.controller.e84StopDataCollectionForLoad()

        self.assertTrue(ok)
        mocked_download.assert_called_once()
        self.assertEqual(len(communicators), 1)
        self.assertEqual(events, ["download", "send:VOC_data_coll_ctrl_stop"])

    def test_load_sequence_still_stops_collection_when_download_fails(self) -> None:
        """下载失败也要尽力停止采集，避免下位机继续写文件/不关文件"""
        communicators: list[FakeSocketCommunicator] = []
        commands: list[str] = []

        def factory(host: str, port: int, timeout: float | None = 5.0):
            _ = (host, port, timeout)
            comm = FakeSocketCommunicator()
            original_send = comm.send

            def send_recording(data: bytes) -> None:
                commands.append(_unpack_command(data))
                original_send(data)

            comm.send = send_recording  # type: ignore[method-assign]
            communicators.append(comm)
            return comm

        self.controller._apply_server_identity(prefix="VOC")
        with patch("voc_app.gui.foup_acquisition.SocketCommunicator", side_effect=factory):
            with patch.object(
                self.controller,
                "_download_logs",
                side_effect=RuntimeError("download broken"),
            ):
                ok = self.controller.e84StopDataCollectionForLoad()

        self.assertFalse(ok)
        self.assertEqual(commands, ["VOC_data_coll_ctrl_stop"])

    def test_unload_start_does_not_retry_on_connection_failure(self) -> None:
        """开始采集是安全关键路径：连接失败不重连重试，避免拖住机械动作"""
        attempts: list[str] = []

        def factory(host: str, port: int, timeout: float | None = 5.0):
            attempts.append("attempt")
            raise ConnectionError("no route to foup")

        with patch("voc_app.gui.foup_acquisition.SocketCommunicator", side_effect=factory):
            ok = self.controller.e84StartDataCollectionForUnload()

        self.assertFalse(ok)
        self.assertEqual(len(attempts), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
