import queue
import time
from typing import Optional, Dict

# 假设 SerialManager 在同一个目录下或已安装
from SerialManager import SerialManager


class ProtocolError(Exception):
    """自定义协议错误"""

    pass


class DeviceController:
    """负责处理特定设备通信协议的控制器"""

    DEVICE_ID = 0x10

    def __init__(self, serial_manager: SerialManager):
        self.manager = serial_manager
        self._buffer = bytearray()

    def _build_command(
        self, wr_flag: int, cmd_type: int, cmd_data: Optional[int] = None
    ) -> bytes:
        """构建命令字节串"""
        combined_byte = (wr_flag << 7) | cmd_type
        if wr_flag == 1 and cmd_data is not None:  # 写操作
            return bytes([self.DEVICE_ID, combined_byte, cmd_data])
        else:  # 读操作
            return bytes([self.DEVICE_ID, combined_byte])

    def _parse_response(self, data: bytes) -> Dict:
        """解析响应字节串"""
        if len(data) not in (2, 3):
            raise ProtocolError(f"响应长度无效: {len(data)}字节")

        device_id = data[0]
        if device_id != self.DEVICE_ID:
            raise ProtocolError(
                f"设备ID不匹配: 期望 {self.DEVICE_ID}, 收到 {device_id}"
            )

        if len(data) == 2:  # 读ACK
            return {"device_id": device_id, "cmd_data": None, "ack_data": data[1]}
        else:  # 写ACK
            return {"device_id": device_id, "cmd_data": data[1], "ack_data": data[2]}

    def _expected_response_length(self, command: bytes) -> int:
        """根据命令判断期望的响应长度"""
        if len(command) < 2:
            raise ProtocolError("命令格式错误，缺少操作标志位")
        wr_flag = (command[1] >> 7) & 0x01
        return 3 if wr_flag == 1 else 2

    def _read_chunk(self, timeout: float = 0.05) -> Optional[bytes]:
        """统一的队列读取封装，便于注入自定义 SerialManager"""
        reader = getattr(self.manager, "read_from_queue", None)
        if callable(reader):
            return reader(timeout=timeout)
        try:
            return self.manager.receive_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _send_and_wait_response(self, command: bytes, timeout_sec: float = 2.0) -> Dict:
        """发送命令并等待完整响应，自动处理分包、粘包与断线"""
        if not self.manager.is_open():
            raise ConnectionError("串口未打开或已断开")

        expected_length = self._expected_response_length(command)
        self.manager.clear_queue()
        if not self.manager.send(command):
            raise ConnectionError("发送命令失败")

        self._buffer.clear()
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            if len(self._buffer) >= expected_length:
                frame = bytes(self._buffer[:expected_length])
                del self._buffer[:expected_length]
                try:
                    return self._parse_response(frame)
                except ProtocolError as err:
                    print(f"响应帧异常，尝试丢弃首字节继续解析: {err}")
                    if self._buffer:
                        self._buffer.pop(0)
                    continue

            chunk = self._read_chunk(timeout=0.05)
            if chunk:
                self._buffer.extend(chunk)
                continue

            if not self.manager.is_open():
                raise ConnectionError("串口已断开")
            has_error = getattr(self.manager, "has_reader_error", None)
            if callable(has_error) and has_error():
                last_error = getattr(self.manager, "get_last_error", lambda: None)()
                raise ConnectionError(f"串口读取异常: {last_error}")

        raise TimeoutError("等待响应超时")

    def sync_sampling_status(
        self,
        sampling_on: bool,
        retries: int = 2,
        retry_delay: float = 0.2,
        command_timeout: float = 2.0,
    ) -> bool:
        """
        同步采样状态。这是一个高层级的、易于理解的接口。
        :param sampling_on: True表示开启，False表示关闭
        :param retries: 重试次数
        :param retry_delay: 重试间隔
        :param command_timeout: 单次命令的超时时间
        :return: 操作是否成功
        """
        sampling_status = 1 if sampling_on else 0
        attempt = 0

        while attempt <= retries:
            try:
                print(
                    f"步骤1: 尝试将采样状态设置为 {'ON' if sampling_on else 'OFF'} (尝试 {attempt + 1})"
                )
                cmd_write = self._build_command(
                    wr_flag=1, cmd_type=1, cmd_data=sampling_status
                )
                response1 = self._send_and_wait_response(
                    cmd_write, timeout_sec=command_timeout
                )
                print(f"  -> 收到响应1: {response1}")

                if response1.get("cmd_data") != sampling_status:
                    raise ProtocolError("设备返回写入状态与请求不一致")

                print("步骤2: 再次读取状态以确认")
                cmd_read = self._build_command(wr_flag=0, cmd_type=1)
                response2 = self._send_and_wait_response(
                    cmd_read, timeout_sec=command_timeout
                )
                print(f"  -> 收到响应2: {response2}")

                if response2.get("ack_data") != 0xAA:
                    raise ProtocolError(
                        f"设备返回异常 ACK: {hex(response2.get('ack_data'))}"
                    )

                print("  -> [成功] 设备确认采样状态已同步。")
                return True

            except (TimeoutError, ConnectionError, ProtocolError) as exc:
                print(f"同步采样状态时发生错误: {exc}")
                attempt += 1
                if attempt > retries:
                    print("  -> 已达到最大重试次数，终止同步。")
                    return False
                if retry_delay > 0:
                    time.sleep(retry_delay)
