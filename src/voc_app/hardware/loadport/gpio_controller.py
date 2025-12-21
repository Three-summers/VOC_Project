"""GPIO 控制器（RPi.GPIO 适配）。

注意：
- RPi.GPIO 为可选依赖（pyproject.toml 的 optional-dependencies.rpi）。
- 本模块必须可在非树莓派环境导入；仅在实际访问 GPIO 时抛出清晰错误。
"""

from __future__ import annotations

from typing import Any, Optional

from voc_app.logging_config import get_logger

logger = get_logger(__name__)


try:  # pragma: no cover - 当前验证环境可能没有 RPi.GPIO
    import RPi.GPIO as _GPIO  # type: ignore

    _GPIO_IMPORT_ERROR: Optional[BaseException] = None
except ModuleNotFoundError as exc:  # pragma: no cover
    _GPIO = None
    _GPIO_IMPORT_ERROR = exc


class GPIOController:
    """GPIO 引脚读写封装。"""

    def __init__(
        self,
        input_pins_config: dict[str, int],
        output_pins_config: dict[str, int],
        pull_status: int,
        default_state: bool,
        *,
        gpio_module: Any = None,
    ) -> None:
        """初始化 GPIO 控制器。

        Args:
            input_pins_config: 输入引脚配置 {名称: BCM}
            output_pins_config: 输出引脚配置 {名称: BCM}
            pull_status: 1=上拉，其它=下拉（保持与历史实现一致）
            default_state: 输出引脚默认电平（True=HIGH，False=LOW）
            gpio_module: 允许注入自定义 GPIO 模块（用于测试/仿真）
        """

        gpio = gpio_module if gpio_module is not None else _GPIO
        if gpio is None:
            raise RuntimeError("RPi.GPIO 未安装，无法初始化 GPIOController") from _GPIO_IMPORT_ERROR

        self._gpio = gpio
        self._gpio.setmode(self._gpio.BCM)

        self.input_pins: dict[str, int] = dict(input_pins_config)
        self.output_pins: dict[str, int] = dict(output_pins_config)

        for _, pin_num in self.input_pins.items():
            if pull_status == 1:
                self._gpio.setup(pin_num, self._gpio.IN, pull_up_down=self._gpio.PUD_UP)
            else:
                self._gpio.setup(pin_num, self._gpio.IN, pull_up_down=self._gpio.PUD_DOWN)

        for _, pin_num in self.output_pins.items():
            self._gpio.setup(pin_num, self._gpio.OUT)
            self._gpio.output(pin_num, self._gpio.HIGH if default_state else self._gpio.LOW)

    def read_input(self, pin_name: str) -> int:
        """读取指定输入引脚状态（返回 GPIO.HIGH/LOW）。"""

        if pin_name not in self.input_pins:
            raise ValueError(f"未知输入引脚: {pin_name}")
        return self._gpio.input(self.input_pins[pin_name])

    def read_all_inputs(self) -> dict[str, bool]:
        """读取所有输入引脚状态（兼容历史：做一次 not 反相）。"""

        return {name: not bool(self.read_input(name)) for name in self.input_pins}

    def set_output(self, pin_name: str, state: bool) -> None:
        """设置单个输出引脚状态。"""

        if pin_name not in self.output_pins:
            raise ValueError(f"未知输出引脚: {pin_name}")
        self._gpio.output(self.output_pins[pin_name], state)

    def set_all_outputs(self, state: bool) -> None:
        """设置所有输出引脚状态。"""

        for pin in self.output_pins:
            self.set_output(pin, state)

    def cleanup(self) -> None:
        """释放 GPIO 资源。"""

        self._gpio.cleanup()
        logger.info("GPIO资源已释放")

