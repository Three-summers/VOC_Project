"""E84 控制器（loadport）实现。

改造目标：
- 实现 voc_app.hardware.controller.AbstractHardwareController 接口
- 保留原有信号定义与状态机逻辑
- GPIO 配置从 core.config 读取（缺失则使用默认值）
- 异常处理统一使用 utils.error_handler 的异常体系进行包装与日志记录

注意：
当前环境可能缺少 PySide6 / RPi.GPIO，本实现不依赖 PySide6；
GPIO 访问通过 gpio_controller.GPIOController 抽象，可注入 FakeGPIOController 用于测试。
"""

from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Any, Callable, Optional

from voc_app.core.config import AppConfig
from voc_app.core.interfaces import ConfigProvider
from voc_app.hardware.controller import AbstractHardwareController
from voc_app.logging_config import get_logger
from voc_app.utils import UnexpectedError

from .gpio_controller import GPIOController

logger = get_logger(__name__)


try:  # pragma: no cover - Py3.11+ 才有 enum.StrEnum
    from enum import StrEnum  # type: ignore
except ImportError:  # pragma: no cover

    class StrEnum(str, Enum):
        """兼容 Py3.10 的 StrEnum（行为满足本项目使用场景）。"""


class Signal:
    """轻量信号实现（无 PySide6 环境的兼容层）。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: list[Callable[..., Any]] = []

    def connect(self, callback: Callable[..., Any]) -> None:
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def disconnect(self, callback: Callable[..., Any]) -> None:
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def emit(self, *args: Any, **kwargs: Any) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for callback in subscribers:
            callback(*args, **kwargs)


SIG_ON = False
SIG_OFF = True

LED_ON = False
LED_OFF = True

ShortTimer = 2.0
LongTimer = 60.0

IN_PUL_UP = 1
IN_PUL_DOWN = 2


class E84State(StrEnum):
    """E84 状态机的字符串枚举。"""

    IDLE = "idle"
    WAIT_TR_REQ = "wait_tr_req"
    WAIT_BUSY = "wait_busy"
    WAIT_L_REQ = "wait_l_req"
    WAIT_U_REQ = "wait_u_req"
    WAIT_COMPT = "wait_compt"
    WAIT_DONE = "wait_done"


DEFAULT_E84_IN_SIG: dict[str, int] = {
    "GO": 22,
    "CS_0": 9,
    "VALID": 10,
    "TR_REQ": 5,
    "BUSY": 6,
    "COMPT": 13,
}

DEFAULT_E84_OUT_SIG: dict[str, int] = {
    "READY": 4,
    "L_REQ": 2,
    "U_REQ": 3,
    "HO_AVBL": 17,
    "ES": 27,
}

DEFAULT_E84_FOUP_KEY: dict[str, int] = {
    "KEY_0": 21,
    "KEY_1": 20,
    "KEY_2": 16,
}

DEFAULT_E84_INFO_LED: dict[str, int] = {
    "CODE_LED": 18,
    "CHARGE_LED": 7,
    "PLACED_LED": 8,
    "LOAD_LED": 25,
    "UNLOAD_LED": 24,
    "SENSOR_LED": 23,
    "ALARM_LED": 12,
}


def _as_str_int_dict(value: Any, *, default: dict[str, int]) -> dict[str, int]:
    if not isinstance(value, dict):
        return dict(default)
    result: dict[str, int] = {}
    for k, v in value.items():
        if isinstance(k, str) and isinstance(v, int):
            result[k] = v
    return result or dict(default)


class E84Controller(AbstractHardwareController):
    """E84 控制器（状态机 + GPIO 读写）。"""

    def __init__(
        self,
        refresh_interval: float = 0.2,
        *,
        config: Optional[ConfigProvider] = None,
        gpio_controller_cls: type[GPIOController] = GPIOController,
        sleep_func: Callable[[float], None] = time.sleep,
        debounce_interval: float = 0.2,
    ) -> None:
        self.refresh_interval = float(refresh_interval)
        self._sleep = sleep_func
        self._debounce_interval = float(debounce_interval)

        self.state_changed: Signal = Signal()
        self.warning: Signal = Signal()
        self.fatal_error: Signal = Signal()
        self.all_keys_set: Signal = Signal()
        self.data_collection_start: Signal = Signal()
        self.data_collection_stop: Signal = Signal()

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._config: ConfigProvider = config or AppConfig()
        if config is None and isinstance(self._config, AppConfig):
            self._config.load()

        cfg_interval = self._config.get("hardware.loadport.e84.refresh_interval", self.refresh_interval)
        try:
            self.refresh_interval = float(cfg_interval)
        except (TypeError, ValueError):
            pass

        self.E84_InSig = _as_str_int_dict(
            self._config.get("hardware.loadport.e84.in_sig", DEFAULT_E84_IN_SIG),
            default=DEFAULT_E84_IN_SIG,
        )

        self.E84_OutSig = _as_str_int_dict(
            self._config.get("hardware.loadport.e84.out_sig", DEFAULT_E84_OUT_SIG),
            default=DEFAULT_E84_OUT_SIG,
        )

        self.E84_FoupKey = _as_str_int_dict(
            self._config.get("hardware.loadport.e84.foup_key", DEFAULT_E84_FOUP_KEY),
            default=DEFAULT_E84_FOUP_KEY,
        )

        self.E84_InfoLED = _as_str_int_dict(
            self._config.get("hardware.loadport.e84.info_led", DEFAULT_E84_INFO_LED),
            default=DEFAULT_E84_INFO_LED,
        )

        self.E84_InSig_Value: dict[str, bool] = {k: False for k in self.E84_InSig}
        self.E84_Key_Value: dict[str, bool] = {k: False for k in self.E84_FoupKey}
        self.E84_Key_Old_Value = dict(self.E84_Key_Value)
        self._keys_all_set: bool = False

        self.FOUP_status = True
        self.FOUP_old_status = True

        self.state: E84State = E84State.IDLE
        self.prev_state: Optional[E84State] = None
        self.led_cnt = 0

        self._timeout_deadline: Optional[float] = None

        self.E84_SigPin = gpio_controller_cls(self.E84_InSig, self.E84_OutSig, IN_PUL_UP, SIG_OFF)
        self.E84_InfoPin = gpio_controller_cls(self.E84_FoupKey, self.E84_InfoLED, IN_PUL_DOWN, LED_OFF)

        self.E84_InSig_Value = self.E84_SigPin.read_all_inputs()
        self.E84_Key_Value = self.E84_InfoPin.read_all_inputs()
        self.E84_Key_Old_Value = dict(self.E84_Key_Value)

        self.Refresh_Input()

    # ------------------------------------------------------------------
    # HardwareController / AbstractHardwareController 接口
    # ------------------------------------------------------------------
    def start(self) -> None:
        """启动控制循环。"""

        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="E84ControllerLoop", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """停止控制循环。"""

        with self._lock:
            self._stop_event.set()
            thread = self._thread
            self._thread = None
            self._stop_timeout()

        if thread and thread.is_alive():
            thread.join(timeout=max(1.0, self.refresh_interval * 2))

    def is_running(self) -> bool:
        """返回控制器是否处于运行状态。"""

        with self._lock:
            return bool(self._thread and self._thread.is_alive() and not self._stop_event.is_set())

    def get_status(self) -> dict:
        with self._lock:
            return {
                "running": self.is_running(),
                "state": self.state.value,
                "foup_status": bool(self.FOUP_status),
                "inputs": dict(self.E84_InSig_Value),
                "keys": dict(self.E84_Key_Value),
                "keys_all_set": bool(self._keys_all_set),
            }

    def reset(self) -> None:
        with self._lock:
            self.E84_ResetSig()
            self.state = E84State.IDLE
            self.prev_state = None
            self._keys_all_set = False

    # ------------------------------------------------------------------
    # 内部循环
    # ------------------------------------------------------------------
    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            cycle_started = time.monotonic()
            self._run_cycle()
            elapsed = time.monotonic() - cycle_started
            sleep_s = max(0.0, self.refresh_interval - elapsed)
            if sleep_s > 0:
                self._stop_event.wait(timeout=sleep_s)

    def _run_cycle(self) -> None:
        try:
            self.Refresh_Input()
            self._process_state()
        except Exception as exc:  # noqa: BLE001
            err = UnexpectedError("E84 控制循环异常", context={"error": str(exc)})
            logger.error(str(err), exc_info=True)
            self.fatal_error.emit(str(err))
            self.stop()

    def _consume_timeout(self) -> bool:
        deadline = self._timeout_deadline
        if deadline is None:
            return False
        if time.monotonic() >= deadline:
            self._timeout_deadline = None
            return True
        return False

    def _stop_timeout(self) -> None:
        self._timeout_deadline = None

    # 用于 Foup 坐落完成后的预操作
    def _key_set_callback(self) -> None:
        self.all_keys_set.emit()

    # ------------------------------------------------------------------
    # 兼容原实现的方法名（保持状态机逻辑）
    # ------------------------------------------------------------------
    def Refresh_Input(self) -> None:  # noqa: N802 - 保持历史命名
        self.E84_InSig_Value = self.E84_SigPin.read_all_inputs()
        self.E84_Key_Value = self.E84_InfoPin.read_all_inputs()
        if self.E84_Key_Old_Value != self.E84_Key_Value:
            self._sleep(self._debounce_interval)
            self.E84_Key_Value = self.E84_InfoPin.read_all_inputs()
            self.E84_Key_Old_Value = dict(self.E84_Key_Value)

        any_key = (
            self.E84_Key_Value.get("KEY_0", False)
            or self.E84_Key_Value.get("KEY_1", False)
            or self.E84_Key_Value.get("KEY_2", False)
        )
        all_keys_on = (
            self.E84_Key_Value.get("KEY_0", False)
            and self.E84_Key_Value.get("KEY_1", False)
            and self.E84_Key_Value.get("KEY_2", False)
        )

        if any_key:
            self.FOUP_status = True
            self.E84_InfoPin.set_output("PLACED_LED", LED_ON)
            if all_keys_on:
                if not self._keys_all_set:
                    self._keys_all_set = True
                    self._key_set_callback()
                self.E84_SigPin.set_output("HO_AVBL", SIG_ON)
                self.E84_SigPin.set_output("ES", SIG_ON)
                self.E84_InfoPin.set_output("ALARM_LED", LED_OFF)
            else:
                self._keys_all_set = False
                self.E84_SigPin.set_output("HO_AVBL", SIG_OFF)
                self.E84_SigPin.set_output("ES", SIG_OFF)
                self.E84_InfoPin.set_output("ALARM_LED", LED_ON)
        else:
            self._keys_all_set = False
            self.FOUP_status = False
            self.E84_SigPin.set_output("HO_AVBL", SIG_ON)
            self.E84_SigPin.set_output("ES", SIG_ON)
            self.E84_InfoPin.set_output("PLACED_LED", LED_OFF)
            self.E84_InfoPin.set_output("ALARM_LED", LED_OFF)

        if self.FOUP_status != self.FOUP_old_status:
            self.FOUP_old_status = self.FOUP_status
            logger.info("FOUP 落回" if self.FOUP_old_status else "FOUP 移走")

        if self.E84_InSig_Value.get("GO", False):
            self.E84_InfoPin.set_output("SENSOR_LED", LED_ON)
        else:
            message = "GO 信号为低，SENSOR_LED 熄灭"
            logger.debug(message)
            self.warning.emit(message)
            self.E84_InfoPin.set_output("SENSOR_LED", LED_OFF)

        if self.led_cnt > 10:
            self.led_cnt = 0
        self.led_cnt += 1

        if self.led_cnt == 5:
            self.E84_InfoPin.set_output("CODE_LED", LED_ON)
        elif self.led_cnt == 10:
            self.E84_InfoPin.set_output("CODE_LED", LED_OFF)

    def E84_ResetSig(self) -> None:  # noqa: N802 - 保持历史命名
        self.E84_SigPin.set_output("L_REQ", SIG_OFF)
        self.E84_SigPin.set_output("U_REQ", SIG_OFF)
        self.E84_SigPin.set_output("READY", SIG_OFF)
        self._stop_timeout()

    def E84_TestOutPin(self) -> None:  # noqa: N802 - 保持历史命名
        self.E84_SigPin.set_all_outputs(SIG_OFF)
        self._sleep(1)
        self.E84_SigPin.set_all_outputs(SIG_ON)
        self._sleep(1)

    def E84_ResetTimer(self, interval: float) -> None:  # noqa: N802 - 保持历史命名
        self._timeout_deadline = None
        if interval > 0:
            self._timeout_deadline = time.monotonic() + float(interval)

    def E84Handoff(self) -> int:  # noqa: N802 - 保持历史命名
        if (
            self.E84_InSig_Value.get("GO", False)
            and self.E84_InSig_Value.get("CS_0", False)
            and self.E84_InSig_Value.get("VALID", False)
        ):
            logger.debug("检测到握手请求")
            if self.FOUP_status:
                self.E84_SigPin.set_output("U_REQ", SIG_ON)
                self.E84_InfoPin.set_output("UNLOAD_LED", LED_ON)
                logger.debug("set U_REQ ON")
            else:
                self.E84_SigPin.set_output("L_REQ", SIG_ON)
                self.E84_InfoPin.set_output("LOAD_LED", LED_ON)
                logger.debug("set L_REQ ON")

            self.E84_ResetTimer(ShortTimer)
            return 1
        return 0

    def E84_wait_TR_REQ(self) -> int:  # noqa: N802 - 保持历史命名
        if self._consume_timeout():
            self.E84_ResetSig()
            return 1
        if self.E84_InSig_Value.get("TR_REQ", False):
            self.E84_SigPin.set_output("READY", SIG_ON)
            logger.debug("set READY ON")
            self.E84_ResetTimer(ShortTimer)
            return 2
        return 0

    def E84_wait_BUSY(self) -> int:  # noqa: N802 - 保持历史命名
        if self._consume_timeout():
            self.E84_ResetSig()
            return 1
        if self.E84_InSig_Value.get("BUSY", False):
            self.E84_ResetTimer(LongTimer)
            logger.debug("GET BUSY")
            return 2
        return 0

    def E84_wait_L_REQ(self) -> int:  # noqa: N802 - 保持历史命名
        if (
            not self.E84_InSig_Value.get("CS_0", False)
            or not self.E84_InSig_Value.get("VALID", False)
            or not self.E84_InSig_Value.get("TR_REQ", False)
            or not self.E84_InSig_Value.get("BUSY", False)
        ):
            self.E84_ResetSig()
            return 1
        if self.FOUP_status:
            self.E84_SigPin.set_output("L_REQ", SIG_OFF)
            self.E84_ResetTimer(LongTimer)
            logger.debug("set L_REQ OFF")
            return 2
        return 0

    def E84_wait_U_REQ(self) -> int:  # noqa: N802 - 保持历史命名
        if (
            not self.E84_InSig_Value.get("CS_0", False)
            or not self.E84_InSig_Value.get("VALID", False)
            or not self.E84_InSig_Value.get("TR_REQ", False)
            or not self.E84_InSig_Value.get("BUSY", False)
        ):
            self.E84_ResetSig()
            return 1
        if not self.FOUP_status:
            self.E84_SigPin.set_output("U_REQ", SIG_OFF)
            self.E84_ResetTimer(LongTimer)
            logger.debug("set U_REQ OFF")
            return 2
        return 0

    def E84_wait_COMPT(self) -> int:  # noqa: N802 - 保持历史命名
        if self._consume_timeout():
            self.E84_ResetSig()
            return 1
        if self.E84_InSig_Value.get("COMPT", False):
            self.E84_SigPin.set_output("READY", SIG_OFF)
            self.E84_ResetTimer(ShortTimer)
            logger.debug("set READY OFF")
            return 2
        return 0

    def E84_wait_DONE(self) -> int:  # noqa: N802 - 保持历史命名
        if self._consume_timeout():
            self.E84_ResetSig()
            return 1
        if (
            not self.E84_InSig_Value.get("CS_0", False)
            and not self.E84_InSig_Value.get("VALID", False)
            and not self.E84_InSig_Value.get("COMPT", False)
        ):
            self.E84_ResetTimer(ShortTimer)
            self._stop_timeout()
            self.E84_InfoPin.set_output("LOAD_LED", LED_OFF)
            self.E84_InfoPin.set_output("UNLOAD_LED", LED_OFF)
            current_time = time.strftime("%H:%M:%S", time.localtime())
            logger.info(f"{current_time} TRANS OVER")
            return 2
        return 0

    def _process_state(self) -> None:
        if self.prev_state != self.state:
            logger.debug(f"当前状态:{self.state.value}")
            self.state_changed.emit(self.state.value)
            self.prev_state = self.state

        if self.state == E84State.IDLE:
            if self.E84Handoff():
                self.state = E84State.WAIT_TR_REQ
                if self.FOUP_status:
                    logger.info("Unload 流程开始，发出数据采集 START 信号")
                    self.data_collection_start.emit()

        elif self.state == E84State.WAIT_TR_REQ:
            wait_status = self.E84_wait_TR_REQ()
            if wait_status == 1:
                message = "等待 TR_REQ 信号超时，状态重置为 IDLE"
                logger.warning(message)
                self.warning.emit(message)
                self.state = E84State.IDLE
            elif wait_status == 2:
                self.state = E84State.WAIT_BUSY

        elif self.state == E84State.WAIT_BUSY:
            wait_status = self.E84_wait_BUSY()
            if wait_status == 1:
                message = "等待 BUSY 信号超时，状态重置为 IDLE"
                logger.warning(message)
                self.warning.emit(message)
                self.state = E84State.IDLE
            elif wait_status == 2:
                self.state = E84State.WAIT_U_REQ if self.FOUP_status else E84State.WAIT_L_REQ

        elif self.state == E84State.WAIT_L_REQ:
            wait_status = self.E84_wait_L_REQ()
            if wait_status == 1:
                message = "L_REQ 阶段检测到信号中断，状态重置为 IDLE"
                logger.warning(message)
                self.warning.emit(message)
                self.state = E84State.IDLE
            elif wait_status == 2:
                self.state = E84State.WAIT_COMPT

        elif self.state == E84State.WAIT_U_REQ:
            wait_status = self.E84_wait_U_REQ()
            if wait_status == 1:
                message = "U_REQ 阶段检测到信号中断，状态重置为 IDLE"
                logger.warning(message)
                self.warning.emit(message)
                self.state = E84State.IDLE
            elif wait_status == 2:
                self.state = E84State.WAIT_COMPT

        elif self.state == E84State.WAIT_COMPT:
            wait_status = self.E84_wait_COMPT()
            if wait_status == 1:
                message = "等待 COMPT 信号超时，状态重置为 IDLE"
                logger.warning(message)
                self.warning.emit(message)
                self.state = E84State.IDLE
            elif wait_status == 2:
                self.state = E84State.WAIT_DONE
                if not self.FOUP_status:
                    logger.info("Load 流程完成，发出数据采集 STOP 信号")
                    self.data_collection_stop.emit()

        elif self.state == E84State.WAIT_DONE:
            wait_status = self.E84_wait_DONE()
            if wait_status == 1:
                message = "等待 DONE 判定超时，状态重置为 IDLE"
                logger.warning(message)
                self.warning.emit(message)
                self.state = E84State.IDLE
            elif wait_status == 2:
                self.state = E84State.IDLE

    def E84_main(self) -> None:  # noqa: N802 - 兼容旧入口
        """兼容旧入口，直接启动循环。"""

        self.start()
