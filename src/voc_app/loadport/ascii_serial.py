from typing import Optional, Callable, Dict
from serial_device import GenericSerialDevice, GenericSerialCommand


class AsciiSerialClient:
    """
    STM32 业务客户端 (组合模式)。

    它不继承 GenericSerialDevice，而是持有一个 device 实例。
    这样对外暴露的 API 更干净，只暴露业务方法 (home, get_param)，
    屏蔽了底层的 send_raw, serial_factory 等细节。
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        message_callback: Optional[Callable[[str], None]] = None,
    ):
        # 1. 初始化私有状态
        self._rx_buffer = bytearray()
        self._message_callback = message_callback

        # 2. 准备命令表
        # 在组合模式下，我们先把命令定义好，再传给内部设备
        command_table = self._build_command_table()

        # 3. 实例化内部设备 (核心：组合)
        # 注意：我们将自己的 _parse_chunk 方法传给内部设备作为回调
        self.device = GenericSerialDevice(
            port=port,
            baudrate=baudrate,
            command_table=command_table,
            parser=self._parse_chunk,  # 注入解析逻辑
        )

    # --------------------------------------------------------------
    # 核心：解析逻辑 (私有)
    # 这里的逻辑属于"业务层"，负责把碎片拼成 STM32 的行
    # --------------------------------------------------------------
    def _parse_chunk(
        self, chunk: bytes, device_instance: "GenericSerialDevice"
    ) -> None:
        """
        作为 parser 注入给 GenericSerialDevice。
        每当底层收到数据，都会回调这个方法。
        """
        self._rx_buffer.extend(chunk)

        while b"\n" in self._rx_buffer:
            line_bytes, _, remaining = self._rx_buffer.partition(b"\n")
            self._rx_buffer = remaining

            try:
                line_str = (
                    line_bytes.replace(b"\r", b"")
                    .decode("utf-8", errors="ignore")
                    .strip()
                )
            except Exception:
                continue

            if line_str:
                self._handle_valid_line(line_str)

    def _handle_valid_line(self, line: str) -> None:
        """处理完整的业务行"""
        # 简单打印日志
        print(f"[STM32] << {line}")

        # 可以在这里处理特定协议，比如 "Unknown"
        if line.startswith("Unknown:"):
            print(f"⚠️ 协议错误: {line}")

        # 通知上层应用
        if self._message_callback:
            self._message_callback(line)

    # --------------------------------------------------------------
    # 核心：命令定义 (私有)
    # --------------------------------------------------------------
    def _build_command_table(self) -> Dict[str, GenericSerialCommand]:
        return {
            "get": GenericSerialCommand(
                name="get", build_frame=lambda target: f"get {target}\n".encode("utf-8")
            ),
            "servo_on": GenericSerialCommand(
                name="servo_on",
                build_frame=lambda enable: f"servo_{'on' if enable else 'off'}\n".encode(
                    "utf-8"
                ),
            ),
            "home": GenericSerialCommand(name="home", build_frame=lambda: b"home\n"),
            "lock": GenericSerialCommand(name="lock", build_frame=lambda: b"lock\n"),
            "unlock": GenericSerialCommand(
                name="unlock", build_frame=lambda: b"unlock\n"
            ),
            "connect": GenericSerialCommand(
                name="connect", build_frame=lambda: b"connect\n"
            ),
            "disconnect": GenericSerialCommand(
                name="disconnect", build_frame=lambda: b"disconnect\n"
            ),
        }

    # --------------------------------------------------------------
    # 生命周期代理 (Delegation)
    # 只暴露必要的生命周期方法
    # --------------------------------------------------------------
    def connect(self):
        self.device.start()

    def disconnect(self):
        self.device.stop()

    def __enter__(self):
        self.device.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.device.stop()

    # --------------------------------------------------------------
    # 业务 API (Public)
    # --------------------------------------------------------------
    def get_param(self, target: str) -> None:
        self.device.send_command("get", target=target)

    def set_servo(self, enable: bool) -> None:
        self.device.send_command("servo_on", enable=enable)

    def home(self) -> None:
        self.device.send_command("home")

    def set_lock(self) -> None:
        self.device.send_command("lock")

    def set_unlock(self) -> None:
        self.device.send_command("unlock")

    def set_connect(self) -> None:
        self.device.send_command("connect")

    def set_unconnect(self) -> None:
        self.device.send_command("unconnect")
