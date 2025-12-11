import os
import random
import socket
import struct
import threading
import time
from pathlib import Path

# 简易测试服务器，使用与客户端一致的 4 字节大端长度前缀协议。
# 支持命令：
# - get_function_version_info -> 返回 VOC_Version 或 Noise_Humility 版本号
# - voc_sample_type_normal/test、Noise_Hmulity_sample_type_normal/test -> ACK
# - voc_data_coll_ctrl_start/stop、Noise_Hmulity_data_coll_ctrl_start/stop -> 开始/停止推送数据
# - get <path> -> 发送单文件目录结构，兼容 Client.get_file
# 其他命令默认返回 ACK。


def send_prefixed(sock: socket.socket, text: str) -> None:
    """发送带 4 字节长度前缀的文本"""
    payload = text.encode("utf-8")
    header = struct.pack(">I", len(payload))
    sock.sendall(header + payload)


def recv_exact(sock: socket.socket, size: int) -> bytes | None:
    """按字节数精确读取，失败返回 None"""
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data.extend(chunk)
    return bytes(data)


class TestServer:
    """简单的多线程测试服务器"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 65432,
        server_type: str = "voc",  # voc 或 noise
    ):
        self.host = host
        self.port = port
        self.server_type = server_type.lower()
        self._running = False
        self._threads: list[threading.Thread] = []
        self._send_lock = threading.Lock()

    def start(self) -> None:
        """启动监听，阻塞主线程"""
        self._running = True
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            print(f"[SERVER] Listening on {self.host}:{self.port} (type={self.server_type})")
            while self._running:
                conn, addr = s.accept()
                print(f"[SERVER] Accepted {addr}")
                t = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                t.start()
                self._threads.append(t)

    def stop(self) -> None:
        """停止服务器"""
        self._running = False
        # 关闭线程由连接退出自行结束

    def _handle_client(self, conn: socket.socket, addr) -> None:
        sender_thread = None
        send_flag = threading.Event()

        def sender_loop():
            """根据类型推送数据"""
            while send_flag.is_set():
                if self.server_type == "noise":
                    values = [
                        round(random.uniform(40, 70), 2),
                        round(random.uniform(18, 28), 2),
                        round(random.uniform(30, 60), 2),
                    ]
                    line = ",".join(str(v) for v in values)
                else:
                    value = round(random.uniform(100, 200), 2)
                    line = str(value)
                with self._send_lock:
                    send_prefixed(conn, line)
                time.sleep(0.5)

        try:
            while True:
                header = recv_exact(conn, 4)
                if not header:
                    break
                (length,) = struct.unpack(">I", header)
                if length == 0:
                    continue
                payload = recv_exact(conn, length)
                if not payload:
                    break
                cmd = payload.decode("utf-8").strip()
                print(f"[SERVER] {addr} -> {cmd}")

                if cmd.startswith("get "):
                    path = cmd[4:].strip() or "Log"
                    self._handle_get(conn, path)
                    continue

                if cmd == "get_function_version_info":
                    version = "V1.0.0"
                    if self.server_type == "noise":
                        send_prefixed(conn, f"Noise_Humility,{version}")
                    else:
                        send_prefixed(conn, f"VOC,{version}")
                    continue

                if "sample_type" in cmd:
                    send_prefixed(conn, "ACK")
                    continue

                if cmd.endswith("_start"):
                    send_prefixed(conn, "ACK")
                    if sender_thread and sender_thread.is_alive():
                        send_flag.clear()
                        sender_thread.join()
                    send_flag.set()
                    sender_thread = threading.Thread(target=sender_loop, daemon=True)
                    sender_thread.start()
                    continue

                if cmd.endswith("_stop"):
                    send_prefixed(conn, "ACK")
                    send_flag.clear()
                    if sender_thread and sender_thread.is_alive():
                        sender_thread.join(timeout=1.0)
                    continue

                # 默认 ACK
                send_prefixed(conn, "ACK")
        except Exception as exc:
            print(f"[SERVER] client error {addr}: {exc}")
        finally:
            send_flag.clear()
            if sender_thread and sender_thread.is_alive():
                sender_thread.join(timeout=1.0)
            try:
                conn.close()
            except Exception:
                pass
            print(f"[SERVER] {addr} closed")

    def _handle_get(self, conn: socket.socket, remote_path: str) -> None:
        """发送单文件目录结构，兼容 Client.get_file"""
        content = "timestamp,ch1,ch2,ch3\n0,1.0,2.0,3.0\n1,1.1,2.1,3.1\n"
        data = content.encode("utf-8")
        filename = "sample.csv"
        remote_dir = remote_path.rstrip("/")
        remote_file = f"{remote_dir}/{filename}"

        send_prefixed(conn, f"D_START {remote_dir}")
        send_prefixed(conn, f"FILE {remote_file} {len(data)}")
        conn.sendall(data)
        send_prefixed(conn, f"D_END {remote_dir}")


if __name__ == "__main__":
    host = os.environ.get("TEST_SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("TEST_SERVER_PORT", "65432"))
    server_type = os.environ.get("TEST_SERVER_TYPE", "voc")
    server = TestServer(host=host, port=port, server_type=server_type)
    try:
        server.start()
    except KeyboardInterrupt:
        print("[SERVER] stopping")
        server.stop()
