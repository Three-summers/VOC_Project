from __future__ import annotations

from contextlib import ExitStack
from enum import StrEnum
import time

try:  # pragma: no cover - PySide6 在部分验证环境可能不存在
    from PySide6.QtCore import QObject, QTimer, Signal
except ModuleNotFoundError:  # pragma: no cover
    from voc_app.utils.qt_stubs import QObject, QTimer, Signal  # type: ignore

from voc_app.loadport.gpio_controller import GPIOController
from voc_app.logging_config import get_logger
from voc_app.utils.error_handler import VOCError, handle_errors

logger = get_logger(__name__)


SIG_ON = False
SIG_OFF = True

LED_ON = False
LED_OFF = True

ShortTimer = 2.0
LongTimer = 60.0

IN_PUL_UP = 1
IN_PUL_DOWN = 2


class E84State(StrEnum):
    """E84状态机的字符串枚举"""

    IDLE = "idle"
    WAIT_TR_REQ = "wait_tr_req"
    WAIT_BUSY = "wait_busy"
    WAIT_L_REQ = "wait_l_req"
    WAIT_U_REQ = "wait_u_req"
    WAIT_COMPT = "wait_compt"
    WAIT_DONE = "wait_done"


class E84Controller(QObject):
    state_changed = Signal(str)
    warning = Signal(str)
    fatal_error = Signal(str)
    all_keys_set = Signal()
    # FOUP 数据采集信号
    data_collection_start = Signal()  # Unload 时发出，通知开始采集
    data_collection_stop = Signal()  # Load 完成时发出，通知停止采集

    def __init__(self, refresh_interval: float = 0.2):
        """使用 PySide6 定时逻辑的 E84 控制器。

        资源管理与异常处理：
        - GPIO 资源通过 ExitStack 统一托管，close() 时释放，避免资源泄漏
        - QTimer 在 stop()/close() 中保证停止，防止对象销毁后仍触发回调
        - 定时回调异常会记录详细日志，并通过 fatal_error 信号上报，同时主动停止循环
        """

        super().__init__()
        self.refresh_interval = refresh_interval
        self._resource_stack = ExitStack()
        self._closed = False

        self.E84_InSig = {
            "GO": 22,
            "CS_0": 9,
            "VALID": 10,
            "TR_REQ": 5,
            "BUSY": 6,
            "COMPT": 13,
        }

        self.E84_OutSig = {
            "READY": 4,
            "L_REQ": 2,
            "U_REQ": 3,
            "HO_AVBL": 17,
            "ES": 27,
        }

        self.E84_FoupKey = {
            "KEY_0": 21,
            "KEY_1": 20,
            "KEY_2": 16,
        }

        self.E84_InfoLED = {
            "CODE_LED": 18,
            "CHARGE_LED": 7,
            "PLACED_LED": 8,
            "LOAD_LED": 25,
            "UNLOAD_LED": 24,
            "SENSOR_LED": 23,
            "ALARM_LED": 12,
        }

        self.E84_InSig_Value = {
            "GO": False,
            "CS_0": False,
            "VALID": False,
            "TR_REQ": False,
            "BUSY": False,
            "COMPT": False,
        }

        self.E84_Key_Value = {
            "KEY_0": False,
            "KEY_1": False,
            "KEY_2": False,
        }

        self.E84_Key_Old_Value = self.E84_Key_Value.copy()
        self._keys_all_set: bool = False

        self.FOUP_status = True
        self.FOUP_old_status = True

        self.state = E84State.IDLE
        self.prev_state = None
        self.led_cnt = 0

        try:
            self.E84_SigPin = GPIOController(
                self.E84_InSig, self.E84_OutSig, IN_PUL_UP, SIG_OFF
            )
            self._resource_stack.callback(self.E84_SigPin.cleanup)
            self.E84_InfoPin = GPIOController(
                self.E84_FoupKey, self.E84_InfoLED, IN_PUL_DOWN, LED_OFF
            )
            self._resource_stack.callback(self.E84_InfoPin.cleanup)
            self.E84_InSig_Value = self.E84_SigPin.read_all_inputs()
            self.E84_Key_Value = self.E84_InfoPin.read_all_inputs()
            self.E84_Key_Old_Value = self.E84_Key_Value.copy()
        except (VOCError, OSError, ValueError) as exc:
            logger.error(f"GPIO 初始化失败: {exc}", exc_info=True)
            # 初始化失败时已无法保证对象完整构建，标记为 closed 避免 __del__ 再次触发 close()
            self._closed = True
            self._resource_stack.close()
            raise

        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_timeout)
        self.timeout_expired = False

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(int(self.refresh_interval * 1000))
        self.refresh_timer.timeout.connect(self._run_cycle)

        try:
            self.Refresh_Input()
        except (VOCError, OSError, ValueError) as exc:
            logger.error(f"初始化刷新输入失败: {exc}", exc_info=True)
            self._closed = True
            self._resource_stack.close()
            raise

    @handle_errors(logger_instance=logger, reraise=False)
    def start(self):
        """启动周期性刷新与状态机运行"""

        if not self.refresh_timer.isActive():
            self.refresh_timer.start()

    @handle_errors(logger_instance=logger, reraise=False)
    def stop(self):
        """停止定时器并清理状态"""

        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        self._stop_timeout()

    def _run_cycle(self):
        try:
            self._run_cycle_impl()
        except VOCError as exc:
            self._handle_fatal_error(f"E84 运行异常: {exc}", exc)

    @handle_errors(logger_instance=logger)
    def _run_cycle_impl(self) -> None:
        """周期性循环的核心逻辑（带统一错误处理与日志）。"""
        self.Refresh_Input()
        self._process_state()

    def _handle_fatal_error(self, message: str, exc: BaseException | None = None) -> None:
        """处理不可恢复错误：记录日志、发出 fatal_error、停止循环并释放资源。"""
        logger.error(message, exc_info=exc is not None)
        try:
            self.fatal_error.emit(message)
        except RuntimeError:
            pass
        self.stop()
        self.close()

    def _process_state(self):
        if self.prev_state != self.state:
            logger.debug(f"当前状态:{self.state.value}")
            self.state_changed.emit(self.state.value)
            self.prev_state = self.state

        if self.state == E84State.IDLE:
            if self.E84Handoff():
                self.state = E84State.WAIT_TR_REQ
                # Unload 流程开始时发出 START 信号（VALID=1 之后，TR_REQ 之前）
                if self.FOUP_status:
                    logger.info("Unload 流程开始，发出数据采集 START 信号")
                    self.data_collection_start.emit()
                    # TODO: 这里可以添加具体的数据采集启动操作

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
                self.state = (
                    E84State.WAIT_U_REQ if self.FOUP_status else E84State.WAIT_L_REQ
                )

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
                # Load 流程完成时发出 STOP 信号（COMPT=1 之后）
                if not self.FOUP_status:
                    logger.info("Load 流程完成，发出数据采集 STOP 信号")
                    self.data_collection_stop.emit()
                    # TODO: 这里可以添加具体的数据采集停止和数据读取操作

        elif self.state == E84State.WAIT_DONE:
            wait_status = self.E84_wait_DONE()
            if wait_status == 1:
                message = "等待 DONE 判定超时，状态重置为 IDLE"
                logger.warning(message)
                self.warning.emit(message)
                self.state = E84State.IDLE
            elif wait_status == 2:
                self.state = E84State.IDLE

    def _on_timeout(self):
        self.timeout_expired = True

    def _consume_timeout(self) -> bool:
        if self.timeout_expired:
            self.timeout_expired = False
            return True
        return False

    def _stop_timeout(self):
        self.timeout_timer.stop()
        self.timeout_expired = False

    # 用于 Foup 坐落完成后的预操作
    def _key_set_callback(self):
        self.all_keys_set.emit()

    def Refresh_Input(self):
        self.E84_InSig_Value = self.E84_SigPin.read_all_inputs()
        self.E84_Key_Value = self.E84_InfoPin.read_all_inputs()
        if self.E84_Key_Old_Value != self.E84_Key_Value:
            time.sleep(0.2)
            self.E84_Key_Value = self.E84_InfoPin.read_all_inputs()
            self.E84_Key_Old_Value = self.E84_Key_Value.copy()

        any_key = (
            self.E84_Key_Value["KEY_0"]
            or self.E84_Key_Value["KEY_1"]
            or self.E84_Key_Value["KEY_2"]
        )
        all_keys_on = (
            self.E84_Key_Value["KEY_0"]
            and self.E84_Key_Value["KEY_1"]
            and self.E84_Key_Value["KEY_2"]
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
            if self.FOUP_old_status:
                logger.info("FOUP 落回")
            else:
                logger.info("FOUP 移走")

        if self.E84_InSig_Value["GO"]:
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

    def E84_ResetSig(self):
        self.E84_SigPin.set_output("L_REQ", SIG_OFF)
        self.E84_SigPin.set_output("U_REQ", SIG_OFF)
        self.E84_SigPin.set_output("READY", SIG_OFF)
        self._stop_timeout()

    def E84_TestOutPin(self):
        self.E84_SigPin.set_all_outputs(SIG_OFF)
        time.sleep(1)
        self.E84_SigPin.set_all_outputs(SIG_ON)
        time.sleep(1)

    def E84_ResetTimer(self, interval: float):
        self.timeout_timer.stop()
        self.timeout_expired = False
        if interval > 0:
            self.timeout_timer.start(int(interval * 1000))

    def E84Handoff(self):
        if (
            self.E84_InSig_Value["GO"]
            and self.E84_InSig_Value["CS_0"]
            and self.E84_InSig_Value["VALID"]
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

    def E84_wait_TR_REQ(self):
        if self._consume_timeout():
            self.E84_ResetSig()
            return 1
        if self.E84_InSig_Value["TR_REQ"]:
            self.E84_SigPin.set_output("READY", SIG_ON)
            logger.debug("set READY ON")
            self.E84_ResetTimer(ShortTimer)
            return 2
        return 0

    def E84_wait_BUSY(self):
        if self._consume_timeout():
            self.E84_ResetSig()
            return 1
        if self.E84_InSig_Value["BUSY"]:
            self.E84_ResetTimer(LongTimer)
            logger.debug("GET BUSY")
            return 2
        return 0

    def E84_wait_L_REQ(self):
        if (
            not self.E84_InSig_Value["CS_0"]
            or not self.E84_InSig_Value["VALID"]
            or not self.E84_InSig_Value["TR_REQ"]
            or not self.E84_InSig_Value["BUSY"]
        ):
            self.E84_ResetSig()
            return 1
        if self.FOUP_status:
            self.E84_SigPin.set_output("L_REQ", SIG_OFF)
            self.E84_ResetTimer(LongTimer)
            logger.debug("set L_REQ OFF")
            return 2
        return 0

    def E84_wait_U_REQ(self):
        if (
            not self.E84_InSig_Value["CS_0"]
            or not self.E84_InSig_Value["VALID"]
            or not self.E84_InSig_Value["TR_REQ"]
            or not self.E84_InSig_Value["BUSY"]
        ):
            self.E84_ResetSig()
            return 1
        if not self.FOUP_status:
            self.E84_SigPin.set_output("U_REQ", SIG_OFF)
            self.E84_ResetTimer(LongTimer)
            logger.debug("set U_REQ OFF")
            return 2
        return 0

    def E84_wait_COMPT(self):
        if self._consume_timeout():
            self.E84_ResetSig()
            return 1
        if self.E84_InSig_Value["COMPT"]:
            self.E84_SigPin.set_output("READY", SIG_OFF)
            self.E84_ResetTimer(ShortTimer)
            logger.debug("set READY OFF")
            return 2
        return 0

    def E84_wait_DONE(self):
        if self._consume_timeout():
            self.E84_ResetSig()
            return 1
        if (
            not self.E84_InSig_Value["CS_0"]
            and not self.E84_InSig_Value["VALID"]
            and not self.E84_InSig_Value["COMPT"]
        ):
            self.E84_ResetTimer(ShortTimer)
            self._stop_timeout()
            self.E84_InfoPin.set_output("LOAD_LED", LED_OFF)
            self.E84_InfoPin.set_output("UNLOAD_LED", LED_OFF)
            current_time = time.strftime("%H:%M:%S", time.localtime())
            logger.info(f"{current_time} TRANS OVER")
            return 2
        return 0

    def E84_main(self):
        """兼容旧入口，直接启动循环"""

        self.start()

    @handle_errors(logger_instance=logger, reraise=False)
    def close(self) -> None:
        """释放资源（幂等）。"""
        if self._closed:
            return
        self._closed = True

        # 先停定时器，避免资源释放后仍触发回调
        try:
            refresh_timer = getattr(self, "refresh_timer", None)
            if refresh_timer is not None and refresh_timer.isActive():
                refresh_timer.stop()
        except RuntimeError:
            pass
        try:
            timeout_timer = getattr(self, "timeout_timer", None)
            if timeout_timer is not None and timeout_timer.isActive():
                timeout_timer.stop()
        except RuntimeError:
            pass

        # 尝试断开回调，避免 deleteLater 后仍触发
        try:
            if refresh_timer is not None:
                refresh_timer.timeout.disconnect(self._run_cycle)
        except (TypeError, RuntimeError):
            pass
        try:
            if timeout_timer is not None:
                timeout_timer.timeout.disconnect(self._on_timeout)
        except (TypeError, RuntimeError):
            pass

        # 释放 GPIO 等资源
        try:
            stack = getattr(self, "_resource_stack", None)
            if stack is not None:
                stack.close()
        finally:
            logger.debug("E84Controller 资源已释放")

    def __enter__(self) -> "E84Controller":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.close()
        return False

    def __del__(self) -> None:  # pragma: no cover - 仅做泄漏提示
        if getattr(self, "_closed", True):
            return
        try:
            logger.warning("检测到 E84Controller 未显式 close()，已尝试自动释放资源")
        except Exception:
            return
        try:
            self.close()
        except Exception:
            pass
