import queue
import serial
import threading
import time
from typing import Callable, Optional


class SerialManager:
    """一个通用的、线程安全的串口管理类"""

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
        serial_factory: Optional[Callable[..., serial.Serial]] = None,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        self.serial_factory = serial_factory or serial.Serial
        self._is_running = False
        self._read_thread: Optional[threading.Thread] = None
        self._reader_error: Optional[Exception] = None
        self.receive_queue = queue.Queue()

    def open(self) -> bool:
        """打开串口并启动后台读取线程"""
        if self.is_open():
            return True
        try:
            self.serial_conn = self.serial_factory(
                port=self.port, baudrate=self.baudrate, timeout=self.timeout
            )
            self._is_running = True
            self._reader_error = None
            self._read_thread = threading.Thread(target=self._read_data, daemon=True)
            self._read_thread.start()
            print(f"串口 {self.port} 已打开，监听线程已启动。")
            return True
        except serial.SerialException as e:
            print(f"无法打开串口 {self.port}: {e}")
            self.serial_conn = None
            self._reader_error = e
            return False

    def close(self) -> None:
        """关闭串口并停止线程"""
        self._is_running = False
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join()
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print(f"串口 {self.port} 已关闭。")
        self.serial_conn = None

    def is_open(self) -> bool:
        return self.serial_conn is not None and self.serial_conn.is_open

    def reconnect(self) -> bool:
        """重新建立串口连接"""
        self.close()
        return self.open()

    def has_reader_error(self) -> bool:
        """读取线程是否捕获到异常"""
        return self._reader_error is not None

    def get_last_error(self) -> Optional[Exception]:
        """返回最近一次读取线程的异常"""
        return self._reader_error

    def _read_data(self) -> None:
        """后台线程，持续读取数据并放入队列"""
        while self._is_running and self.is_open():
            try:
                # in_waiting: 获取输入缓冲区中的字节数
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    if data:
                        self.receive_queue.put(data)
                else:
                    time.sleep(0.01)  # 避免CPU空转
            except serial.SerialException as exc:
                print("读取数据时串口断开，线程退出。")
                self._is_running = False
                self._reader_error = exc
                break

    def send(self, data: bytes) -> bool:
        """发送字节数据"""
        if not self.is_open():
            print("错误: 串口未打开")
            return False
        try:
            self.serial_conn.write(data)
            return True
        except serial.SerialTimeoutException:
            print("错误: 发送超时")
            return False
        except serial.SerialException as e:
            print(f"发送错误: {e}")
            self._reader_error = e
            return False

    def read_from_queue(self, timeout: float = 0.05) -> Optional[bytes]:
        """从接收队列中读取一段数据"""
        try:
            return self.receive_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def clear_queue(self):
        """清空接收队列"""
        with self.receive_queue.mutex:
            self.receive_queue.queue.clear()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
