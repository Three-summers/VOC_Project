from typing import Union

from DeviceController import DeviceController
from SerialManager import SerialManager


class CMDSerialController(DeviceController):
    """面向采样协议的串口控制器，复用 DeviceController 的命令流程"""

    def __init__(self, serial_manager: SerialManager):
        super().__init__(serial_manager)

    @classmethod
    def from_port(
        cls, port: str, baudrate: int = 115200, timeout: float = 1.0
    ) -> "CMDSerialController":
        """根据串口配置创建控制器，方便兼容旧用法"""

        manager = SerialManager(port=port, baudrate=baudrate, timeout=timeout)
        if not manager.open():
            raise ConnectionError(f"无法打开串口 {port}")
        return cls(manager)

    def simpling_sync(
        self,
        sampling_status: Union[int, bool],
        retries: int = 2,
        retry_delay: float = 0.2,
        command_timeout: float = 2.0,
    ) -> bool:
        """兼容旧接口：允许配置重试与超时"""

        sampling_on = bool(sampling_status)
        return self.sync_sampling_status(
            sampling_on,
            retries=retries,
            retry_delay=retry_delay,
            command_timeout=command_timeout,
        )

    def close(self) -> None:
        """关闭底层串口资源"""

        self.manager.close()

    def __enter__(self) -> "CMDSerialController":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
