"""GPIO 控制器封装。

说明：
- RPi.GPIO 属于可选依赖（仅树莓派环境需要）。为保证开发/测试环境可导入，本模块会在缺少依赖时延迟报错。
"""

from __future__ import annotations

try:  # 可选依赖：仅树莓派环境需要
    import RPi.GPIO as GPIO  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    GPIO = None  # type: ignore[assignment]

from voc_app.logging_config import get_logger
from voc_app.utils.error_handler import ResourceError

logger = get_logger(__name__)


class GPIOController:
    def __init__(
        self,
        input_pins_config: dict[str, int],
        output_pins_config: dict[str, int],
        PUL_Status: int,
        default_state: bool,
    ) -> None:
        """
        初始化GPIO控制器
        :param input_pins_config: 输入引脚配置字典 {名称: BCM编号}
        :param output_pins_config: 输出引脚配置字典 {名称: BCM编号}
        """
        if GPIO is None:
            raise ResourceError("RPi.GPIO 未安装，无法初始化 GPIOController")

        self._cleaned = False
        GPIO.setmode(GPIO.BCM)

        # 保存引脚配置
        self.input_pins: dict[str, int] = input_pins_config
        self.output_pins: dict[str, int] = output_pins_config

        # 初始化输入引脚
        for pin_name, pin_num in self.input_pins.items():
            if PUL_Status == 1:
                GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            else:
                GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        # 初始化输出引脚
        for pin_name, pin_num in self.output_pins.items():
            GPIO.setup(pin_num, GPIO.OUT)
            if default_state:
                GPIO.output(pin_num, GPIO.HIGH)
            else:
                GPIO.output(pin_num, GPIO.LOW)

    def read_input(self, pin_name: str) -> int:
        """
        读取指定输入引脚状态
        :param pin_name: 输入引脚名称
        :return: GPIO.HIGH 或 GPIO.LOW
        """
        if pin_name not in self.input_pins:
            raise ValueError(f"未知输入引脚: {pin_name}")
        return GPIO.input(self.input_pins[pin_name])

    def read_all_inputs(self) -> dict[str, bool]:
        """读取所有输入引脚状态"""
        return {name: not self.read_input(name) for name in self.input_pins}

    def set_output(self, pin_name: str, state: bool) -> None:
        """
        设置单个输出引脚状态
        :param pin_num: BCM编号
        :param state: GPIO.HIGH 或 GPIO.LOW
        """
        if pin_name not in self.output_pins:
            raise ValueError(f"未知输出引脚: {pin_name}")
        GPIO.output(self.output_pins[pin_name], state)

    def set_all_outputs(self, state: bool) -> None:
        """设置所有输出引脚状态"""
        for pin in self.output_pins:
            self.set_output(pin, state)
    '''    
    def toggle_output(self, pin_num):
        """翻转单个输出引脚状态"""
        current = GPIO.input(pin_num)
        self.set_output(pin_num, not current)
    
    def toggle_all_outputs(self):
        """翻转所有输出引脚状态"""
        for pin in self.output_pins:
            self.toggle_output(pin)
    '''

    def cleanup(self) -> None:
        """释放GPIO资源"""
        if GPIO is None:
            return
        if self._cleaned:
            return
        self._cleaned = True
        GPIO.cleanup()
        logger.info("GPIO资源已释放")

    def __enter__(self) -> "GPIOController":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.cleanup()
        return False
