"""测试 socket_client 模块"""
import socket
import struct
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.socket_client import Communicator, SocketCommunicator, Client


class MockCommunicator(Communicator):
    """用于测试的模拟通信器"""

    def __init__(self):
        self.sent_data = bytearray()
        self.recv_buffer = bytearray()
        self.closed = False

    def send(self, data: bytes) -> None:
        self.sent_data.extend(data)

    def recv(self, size: int) -> bytes:
        if len(self.recv_buffer) >= size:
            result = bytes(self.recv_buffer[:size])
            self.recv_buffer = self.recv_buffer[size:]
            return result
        return b""

    def close(self) -> None:
        self.closed = True

    def feed(self, data: bytes) -> None:
        """向接收缓冲区添加数据"""
        self.recv_buffer.extend(data)


class TestCommunicatorInterface(unittest.TestCase):
    """测试 Communicator 接口"""

    def test_mock_communicator_send(self) -> None:
        """测试模拟通信器的发送功能"""
        comm = MockCommunicator()
        comm.send(b"hello")
        self.assertEqual(bytes(comm.sent_data), b"hello")

    def test_mock_communicator_recv(self) -> None:
        """测试模拟通信器的接收功能"""
        comm = MockCommunicator()
        comm.feed(b"world")
        data = comm.recv(5)
        self.assertEqual(data, b"world")

    def test_mock_communicator_context_manager(self) -> None:
        """测试上下文管理器"""
        comm = MockCommunicator()
        with comm:
            comm.send(b"test")
        self.assertTrue(comm.closed)


class TestClient(unittest.TestCase):
    """测试 Client 类"""

    def setUp(self) -> None:
        self.comm = MockCommunicator()
        self.client = Client(self.comm)

    def tearDown(self) -> None:
        if not self.comm.closed:
            self.client.close()

    def test_send_msg(self) -> None:
        """测试消息发送"""
        self.client._send_msg("hello")
        # 检查消息格式: 4字节长度 + 内容
        expected_len = struct.pack(">I", 5)
        self.assertEqual(bytes(self.comm.sent_data), expected_len + b"hello")

    def test_recv_msg(self) -> None:
        """测试消息接收"""
        # 准备消息: 4字节长度 + 内容
        msg = "测试消息"
        msg_bytes = msg.encode("utf-8")
        self.comm.feed(struct.pack(">I", len(msg_bytes)) + msg_bytes)

        received = self.client._recv_msg()
        self.assertEqual(received, msg)

    def test_recv_msg_empty(self) -> None:
        """测试接收空消息"""
        # 空缓冲区
        received = self.client._recv_msg()
        self.assertIsNone(received)

    def test_recv_msg_zero_length(self) -> None:
        """测试接收长度为0的消息"""
        self.comm.feed(struct.pack(">I", 0))
        received = self.client._recv_msg()
        # 当 body 为空字节时，_recvall 返回 b""，if not body 为 True，返回 None
        self.assertIsNone(received)

    def test_recv_msg_too_large(self) -> None:
        """测试消息过大被丢弃"""
        client = Client(self.comm, max_message_size=10)
        # 发送长度超过限制的消息
        self.comm.feed(struct.pack(">I", 20) + b"x" * 20)
        received = client._recv_msg()
        self.assertIn("过大", received)

    def test_recvall(self) -> None:
        """测试完整接收"""
        self.comm.feed(b"12345")
        data = self.client._recvall(5)
        self.assertEqual(data, b"12345")

    def test_recvall_partial(self) -> None:
        """测试部分数据接收"""
        self.comm.feed(b"123")
        data = self.client._recvall(5)
        self.assertIsNone(data)

    def test_run_shell(self) -> None:
        """测试 shell 命令执行"""
        # 准备响应
        response = "command output"
        resp_bytes = response.encode("utf-8")
        self.comm.feed(struct.pack(">I", len(resp_bytes)) + resp_bytes)

        result = self.client.run_shell("ls -la")

        # 检查发送的命令
        sent = bytes(self.comm.sent_data)
        cmd_len = struct.unpack(">I", sent[:4])[0]
        cmd = sent[4 : 4 + cmd_len].decode("utf-8")
        self.assertEqual(cmd, "run ls -la")

        # 检查接收的响应
        self.assertEqual(result, response)

    def test_run_shell_with_list(self) -> None:
        """测试使用列表形式的 shell 命令"""
        response = "ok"
        resp_bytes = response.encode("utf-8")
        self.comm.feed(struct.pack(">I", len(resp_bytes)) + resp_bytes)

        self.client.run_shell(["echo", "hello", "world"])

        sent = bytes(self.comm.sent_data)
        cmd_len = struct.unpack(">I", sent[:4])[0]
        cmd = sent[4 : 4 + cmd_len].decode("utf-8")
        self.assertEqual(cmd, "run echo hello world")

    def test_close(self) -> None:
        """测试关闭连接"""
        self.client.close()
        self.assertTrue(self.comm.closed)

    def test_close_twice(self) -> None:
        """测试重复关闭"""
        self.client.close()
        self.client.close()  # 不应该报错
        self.assertTrue(self.comm.closed)

    def test_context_manager(self) -> None:
        """测试上下文管理器"""
        with Client(MockCommunicator()) as client:
            self.assertFalse(client._closed)
        self.assertTrue(client._closed)


class TestSocketCommunicator(unittest.TestCase):
    """测试 SocketCommunicator 类"""

    def test_connection_refused(self) -> None:
        """测试连接被拒绝"""
        with self.assertRaises((ConnectionRefusedError, OSError)):
            # 尝试连接一个不存在的端口
            SocketCommunicator("127.0.0.1", 65535, timeout=0.1)

    def test_socket_communicator_with_server(self) -> None:
        """测试与真实服务器的通信"""
        # 创建一个简单的测试服务器
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("127.0.0.1", 0))  # 使用随机端口
        server_socket.listen(1)
        port = server_socket.getsockname()[1]

        server_received = []

        def server_thread():
            conn, _ = server_socket.accept()
            data = conn.recv(1024)
            server_received.append(data)
            conn.sendall(b"response")
            conn.close()
            server_socket.close()

        thread = threading.Thread(target=server_thread)
        thread.start()

        try:
            # 连接并通信
            comm = SocketCommunicator("127.0.0.1", port, timeout=2.0)
            comm.send(b"hello")
            response = comm.recv(8)
            comm.close()

            thread.join(timeout=2.0)

            self.assertEqual(server_received[0], b"hello")
            self.assertEqual(response, b"response")
        finally:
            if thread.is_alive():
                thread.join(timeout=1.0)


class TestClientFileTransfer(unittest.TestCase):
    """测试 Client 文件传输功能"""

    def setUp(self) -> None:
        self.comm = MockCommunicator()
        self.client = Client(self.comm)

    def test_get_file_single_file(self) -> None:
        """测试单文件下载协议"""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # 模拟服务器响应: FILE <path> <size>
            file_content = b"file content here"
            file_msg = f"FILE /remote/test.txt {len(file_content)}"
            file_msg_bytes = file_msg.encode("utf-8")

            # 发送 FILE 消息
            self.comm.feed(struct.pack(">I", len(file_msg_bytes)) + file_msg_bytes)
            # 发送文件内容
            self.comm.feed(file_content)

            saved_files = self.client.get_file("/remote/test.txt", tmpdir)

            self.assertEqual(len(saved_files), 1)
            self.assertTrue(os.path.exists(saved_files[0]))
            with open(saved_files[0], "rb") as f:
                self.assertEqual(f.read(), file_content)

    def test_get_file_error(self) -> None:
        """测试文件下载错误"""
        # 模拟服务器返回错误
        error_msg = "ERROR File not found"
        error_bytes = error_msg.encode("utf-8")
        self.comm.feed(struct.pack(">I", len(error_bytes)) + error_bytes)

        with self.assertRaises(RuntimeError) as ctx:
            self.client.get_file("/nonexistent")

        self.assertIn("File not found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
