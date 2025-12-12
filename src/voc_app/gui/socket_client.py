import socket
import os
import struct
import serial
import abc
from typing import Any, Optional, Iterable, Union, List


# --- 1. 通信层抽象 ---


class Communicator(abc.ABC):
    """通信接口抽象基类."""

    @abc.abstractmethod
    def send(self, data: bytes) -> None:
        pass

    @abc.abstractmethod
    def recv(self, size: int) -> bytes:
        pass

    @abc.abstractmethod
    def close(self) -> None:
        pass

    def __enter__(self) -> "Communicator":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()


class SocketCommunicator(Communicator):
    """使用 Socket 进行通信的实现."""

    def __init__(self, host: str, port: int, timeout: float | None = 5.0) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 设置超时，避免阻塞导致线程无法退出
        if timeout is not None:
            self.sock.settimeout(timeout)
        try:
            self.sock.connect((host, port))
        except ConnectionRefusedError as e:
            raise

    def send(self, data: bytes) -> None:
        self.sock.sendall(data)

    def recv(self, size: int) -> bytes:
        try:
            return self.sock.recv(size)
        except socket.timeout:
            # 超时返回空字节，交由上层判定为断开/中断
            return b""

    def close(self) -> None:
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        self.sock.close()


class SerialCommunicator(Communicator):
    """使用串口进行通信的实现."""

    def __init__(self, port: str, baudrate: int, timeout: float = 2.0) -> None:
        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
        except serial.SerialException as e:
            raise

    def send(self, data: bytes) -> None:
        self.ser.write(data)

    def recv(self, size: int) -> bytes:
        return self.ser.read(size)

    def close(self) -> None:
        try:
            self.ser.flush()
        except Exception:
            pass
        self.ser.close()


# --- 2. 可复用客户端类 ---


class Client:
    """
    面向外部调用的客户端封装:
    - 支持 run() / power() 命令
    - 支持 get() 文件/目录下载（流式协议）
    - 返回结果或抛出异常，无控制台打印
    """

    def __init__(self, communicator: Communicator, max_message_size: int = 1024 * 1024) -> None:
        self.comm = communicator
        self.max_message_size = max_message_size
        self._closed = False

    # --- 基础消息编解码 ---

    def _send_msg(self, msg: str) -> None:
        msg_bytes = msg.encode("utf-8")
        packed = struct.pack(">I", len(msg_bytes)) + msg_bytes
        self.comm.send(packed)

    def _recvall(self, n: int) -> Optional[bytes]:
        data = bytearray()
        while len(data) < n:
            packet = self.comm.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return bytes(data)

    def _recv_msg(self) -> Optional[str]:
        raw_len = self._recvall(4)
        if not raw_len:
            return None
        msglen = struct.unpack(">I", raw_len)[0]
        if msglen > self.max_message_size:
            # 超限：消费掉消息体后返回提示
            self._recvall(msglen)
            return "错误: 消息过大已被丢弃."
        body = self._recvall(msglen)
        if not body:
            return None
        return body.decode("utf-8")

    # --- 命令方法 ---

    def run_shell(self, command: Union[str, Iterable[str]]) -> Optional[str]:
        """
        执行远端 shell 命令。
        command: 字符串或字符串序列（会用空格拼接）
        返回服务端响应文本，或 None 表示连接中断/超时。
        """
        if isinstance(command, str):
            cmd_str = command
        else:
            cmd_str = " ".join(command)
        self._send_msg(f"run {cmd_str}")
        return self._recv_msg()

    def get_file(self, remote_path: str, dest_root: Optional[str] = None) -> List[str]:
        """
        下载文件或目录到本地。
        - remote_path: 服务端路径
        - dest_root: 本地存放根目录（默认当前目录）
        返回下载的本地文件绝对路径列表；若连接中断/协议错误会抛出异常。
        """
        dest_root = dest_root or "."
        dest_root = os.path.abspath(dest_root)

        self._send_msg(f"get {remote_path}")

        dir_stack = []
        server_root = None
        local_root = None
        saved_files: List[str] = []

        while True:
            msg = self._recv_msg()
            if msg is None:
                raise RuntimeError("连接中断或接收超时。")

            parts = msg.split(" ", 1)
            msg_type = parts[0]

            if msg_type == "D_START":
                server_path = parts[1]
                if server_root is None:
                    server_root = server_path
                    local_root = os.path.join(dest_root, os.path.basename(server_path))
                    local_path = local_root
                else:
                    if local_root is None:
                        raise RuntimeError("协议错误: local_root 未初始化。")
                    # 将服务端路径前缀 server_root 替换为 local_root，映射到本地
                    local_path = server_path.replace(server_root, local_root, 1)

                os.makedirs(local_path, exist_ok=True)
                dir_stack.append(server_path)

            elif msg_type == "D_END":
                server_path = parts[1]
                if not dir_stack or dir_stack[-1] != server_path:
                    raise RuntimeError(f"协议错误: 乱序的 D_END for {server_path}")
                dir_stack.pop()
                if not dir_stack:
                    # 根目录处理完毕
                    return saved_files

            elif msg_type == "FILE":
                try:
                    _, server_filepath, filesize_str = msg.split(" ", 2)
                    filesize = int(filesize_str)
                except ValueError:
                    raise RuntimeError(f"协议错误: 无效的 FILE 消息: {msg}")

                if server_root is None:
                    # 单文件模式：直接保存到 dest_root 下
                    local_filepath = os.path.join(
                        dest_root, os.path.basename(server_filepath)
                    )
                else:
                    if local_root is None:
                        raise RuntimeError("协议错误: local_root 未初始化。")
                    local_filepath = server_filepath.replace(server_root, local_root, 1)

                parent_dir = os.path.dirname(local_filepath)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)

                remaining = filesize
                with open(local_filepath, "wb") as f:
                    while remaining > 0:
                        chunk_size = min(4096, remaining)
                        data = self._recvall(chunk_size)
                        if not data:
                            raise RuntimeError("文件传输中断或超时。")
                        f.write(data)
                        remaining -= len(data)

                saved_files.append(os.path.abspath(local_filepath))

                # 如果是单文件模式，收到第一份文件就结束
                if server_root is None:
                    return saved_files

            elif msg_type == "ERROR":
                detail = parts[1] if len(parts) > 1 else ""
                raise RuntimeError(f"服务端错误: {detail}")

            else:
                raise RuntimeError(f"未知的服务端响应: {msg}")

    def close(self) -> None:
        """关闭底层通信。若合适会尝试先发送 exit。"""
        if self._closed:
            return
        self.comm.close()
        self._closed = True

    def __enter__(self) -> "Client":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()
