"""日志下载安全测试（R05 / R06）。

R05：服务端返回的 FILE 路径可能落在请求目录之外，必须拒绝，不能写出下载根目录。
R06：下载中断不能破坏本地已有的完整文件（先写临时文件，校验通过后原子替换）。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.socket_client import Client


class ScriptedCommunicator:
    """按脚本回放服务端报文的替身（发送内容被忽略）。"""

    def __init__(self, messages: list[bytes]) -> None:
        self._buffer = bytearray()
        for payload in messages:
            self._buffer.extend(payload)
        self.closed = False

    def send(self, data: bytes) -> None:
        return None

    def recv(self, size: int) -> bytes:
        if not self._buffer:
            return b""
        chunk = self._buffer[:size]
        del self._buffer[:size]
        return bytes(chunk)

    def close(self) -> None:
        self.closed = True


def _msg(text: str) -> bytes:
    body = text.encode("utf-8")
    return len(body).to_bytes(4, "big") + body


def _directory_transfer(
    server_root: str,
    files: list[tuple[str, bytes, int | None]],
    terminate_early: bool = False,
):
    """构造 D_START/FILE/D_END 报文；size=None 表示声明长度与实际一致。

    ``terminate_early=True`` 模拟传输中断：流在文件内容中途直接结束，
    不会再有后续帧，这样客户端只能读到不足的字节。
    """
    messages = [_msg(f"D_START {server_root}")]
    for path, data, declared in files:
        size = len(data) if declared is None else declared
        messages.append(_msg(f"FILE {path} {size}"))
        messages.append(data)
    if not terminate_early:
        messages.append(_msg(f"D_END {server_root}"))
    return messages


class DownloadPathSafetyTests(unittest.TestCase):
    def test_rejects_file_outside_requested_directory(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "downloads"
            communicator = ScriptedCommunicator(
                _directory_transfer(
                    "/remote/Log",
                    [("/etc/outside.csv", b"pwned", None)],
                )
            )
            client = Client(communicator)

            try:
                client.get_file("/remote/Log", str(dest))
            except RuntimeError as exc:
                self.assertIn("路径", str(exc))
            else:
                raise AssertionError("越界文件必须被拒绝")

            self.assertFalse((Path(tmp) / "outside.csv").exists())

    def test_rejects_parent_traversal(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "downloads"
            communicator = ScriptedCommunicator(
                _directory_transfer(
                    "/remote/Log",
                    [("/remote/Log/../../escaped.csv", b"pwned", None)],
                )
            )
            client = Client(communicator)

            with self.assertRaises(RuntimeError):
                client.get_file("/remote/Log", str(dest))

            self.assertFalse((Path(tmp) / "escaped.csv").exists())

    def test_accepts_normal_nested_files(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "downloads"
            communicator = ScriptedCommunicator(
                _directory_transfer(
                    "/remote/Log",
                    [("/remote/Log/csv_file/data.csv", b"a,b\n1,2\n", None)],
                )
            )
            client = Client(communicator)

            saved = client.get_file("/remote/Log", str(dest))

            self.assertEqual(len(saved), 1)
            self.assertTrue(Path(saved[0]).is_file())
            self.assertIn("csv_file", saved[0])


class DownloadAtomicityTests(unittest.TestCase):
    def test_interrupted_download_keeps_existing_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "downloads"
            target = dest / "Log" / "history.csv"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"IMPORTANT-HISTORY")

            communicator = ScriptedCommunicator(
                _directory_transfer(
                    "/remote/Log",
                    # 声明 20 字节但只给 4 字节，且连接在此中断
                    [("/remote/Log/history.csv", b"data", 20)],
                    terminate_early=True,
                )
            )
            client = Client(communicator)

            with self.assertRaises(RuntimeError):
                client.get_file("/remote/Log", str(dest))

            self.assertEqual(target.read_bytes(), b"IMPORTANT-HISTORY")
            leftovers = list(target.parent.glob("*.part"))
            self.assertEqual(leftovers, [], "临时文件必须被清理")

    def test_successful_download_replaces_previous_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "downloads"
            target = dest / "Log" / "history.csv"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"OLD")

            communicator = ScriptedCommunicator(
                _directory_transfer(
                    "/remote/Log",
                    [("/remote/Log/history.csv", b"NEWDATA", None)],
                )
            )
            client = Client(communicator)

            client.get_file("/remote/Log", str(dest))

            self.assertEqual(target.read_bytes(), b"NEWDATA")
            self.assertEqual(list(target.parent.glob("*.part")), [])


if __name__ == "__main__":
    unittest.main()
