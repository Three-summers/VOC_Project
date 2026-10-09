from enum import StrEnum
import time

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from voc_app.loadport.gpio_controller import GPIOController
from voc_app.logging_config import get_logger

logger = get_logger(__name__)


SIG_ON = False
SIG_OFF = True

LED_ON = False
LED_OFF = True

ShortTimer = 2.0
LongTimer = 60.0

KeyDebounceSec = 0.2

IN_PUL_UP = 1
IN_PUL_DOWN = 2


class _InfoKeyOnlyController(GPIOController):
    """【临时】只读 FOUP 按键、完全不动 E84 信息灯的控制器。

    E84 信息灯的引脚（GPIO7/8/12/18/23/24/25）与状态指示灯（GPIO7 红、GPIO25 黄）
    冲突，而现场这些 E84 信息灯已不再使用，因此：

    - 构造时不再 setup 任何输出引脚（调用方传空输出字典）；
    - ``set_output()`` 变成空操作，原有约 20 处写灯调用点无需改动。

    恢复 E84 信息灯时，把 ``E84_InfoPin`` 换回 ``GPIOController`` 并传回
    ``E84_InfoLED`` 即可。
    """

    def set_output(self, pin_name: str, state: bool) -> None:  # noqa: ARG002
        return


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
        """使用PySide6定时逻辑的E84控制器

        安全语义固定（R01/R02/R04）：

        - CS_0/VALID 被撤销时撤回输出并回到 IDLE；
        - Load 完成必须三键全落（完整落位），而不是任意一键；
        - ``stop()`` 时撤回 READY/L_REQ/U_REQ 等输出。
        """

        super().__init__()
        self.refresh_interval = refresh_interval
        self._key_debounce_ms = int(KeyDebounceSec * 1000)

        # GO(BCM22) 已在现场确认未接线、不携带信息，2026-10-09 从接口中彻底删除：
        # 既不再读入，也不再作为握手前提（原 R01 判定只剩 CS_0 + VALID）。
        self.E84_InSig = {
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

        # 【临时】仅作引脚记录：这些 E84 信息灯已停用（见 _InfoKeyOnlyController），
        # 控制器不再申请/驱动它们，避免与状态指示灯 GPIO7/GPIO25 冲突。
        # SENSOR_LED(GPIO23) 随 GO 输入一起删除，不再出现在配置里。
        self.E84_InfoLED = {
            "CODE_LED": 18,
            "CHARGE_LED": 7,
            "PLACED_LED": 8,
            "LOAD_LED": 25,
            "UNLOAD_LED": 24,
            "ALARM_LED": 12,
        }

        self.E84_InSig_Value = {
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

        self._keys_all_set: bool = False
        self.E84_Key_Raw_Value = self.E84_Key_Value.copy()
        self._pending_key_value: dict[str, bool] | None = None

        self.FOUP_status = True
        self.FOUP_old_status = True
        # FOUP_docked 表示"完整落位"（三键全落），与"检测到载具"（任意一键）区分（R02）
        self.FOUP_docked = False

        self.state = E84State.IDLE
        self.prev_state = None
        self.led_cnt = 0
        self._actuator_error_latched = False
        self._error_latch_reported = False
        # 本次传输方向（True=卸载）。在 E84Handoff 时锁定，避免中途 FOUP
        # 已离位导致 WAIT_BUSY 阶段把卸载误判成装载。
        self._unload_flow: bool | None = None

        self.E84_SigPin = GPIOController(
            self.E84_InSig, self.E84_OutSig, IN_PUL_UP, SIG_OFF
        )
        # 【临时】E84 信息灯停用：其引脚与状态指示灯冲突（GPIO7/GPIO25），
        # 现场也不再使用这些 E84 灯。这里只保留 FOUP 按键输入，
        # 输出字典传空、set_output 为空操作，因此不会再申请或驱动任何灯的引脚。
        # 原实现：GPIOController(self.E84_FoupKey, self.E84_InfoLED, IN_PUL_DOWN, LED_OFF)
        self.E84_InfoPin = _InfoKeyOnlyController(
            self.E84_FoupKey, {}, IN_PUL_DOWN, LED_OFF
        )
        self.E84_InSig_Value = self.E84_SigPin.read_all_inputs()
        self.E84_Key_Value = self.E84_InfoPin.read_all_inputs()
        self.E84_Key_Raw_Value = self.E84_Key_Value.copy()

        self._key_debounce_timer = QTimer(self)
        self._key_debounce_timer.setSingleShot(True)
        self._key_debounce_timer.timeout.connect(self._on_key_debounce_timeout)

        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_timeout)
        self.timeout_expired = False

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(int(self.refresh_interval * 1000))
        self.refresh_timer.timeout.connect(self._run_cycle)

        self.Refresh_Input()

    def start(self):
        """启动周期性刷新与状态机运行"""

        if not self.refresh_timer.isActive():
            self.refresh_timer.start()

    def stop(self):
        """停止定时器并清理状态。

        R04：不能只停定时器。已经输出的 READY/L_REQ/U_REQ 必须显式撤回，
        否则软件停止监控后外部仍可能看到有效握手信号。
        """

        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        self._stop_timeout()
        self._key_debounce_timer.stop()
        self._pending_key_value = None
        # R04：不能只停定时器。已经输出的 READY/L_REQ/U_REQ 必须显式撤回，
        # 否则软件停止监控后外部仍可能看到有效握手信号。
        self._enter_safe_idle_state()

    def _enter_safe_idle_state(self) -> None:
        """回到 IDLE 并撤回握手输出（R04）。"""

        self._unload_flow = None
        self.state = E84State.IDLE
        self.prev_state = None
        self.E84_ResetSig()
        self.E84_InfoPin.set_output("LOAD_LED", LED_OFF)
        self.E84_InfoPin.set_output("UNLOAD_LED", LED_OFF)
        logger.info("E84 已进入安全停机状态：READY/L_REQ/U_REQ 已撤回")

    def _run_cycle(self):
        self.Refresh_Input()
        self._process_state()

    def _process_state(self):
        if self._actuator_error_latched:
            if not self._error_latch_reported:
                message = "执行机构异常锁存，E84 READY 保持低电平，等待复位"
                logger.warning(message)
                self.warning.emit(message)
                self._error_latch_reported = True
            self.state = E84State.IDLE
            self.E84_ResetSig()
            self.E84_InfoPin.set_output("LOAD_LED", LED_OFF)
            self.E84_InfoPin.set_output("UNLOAD_LED", LED_OFF)
            if self.prev_state != self.state:
                self.state_changed.emit(self.state.value)
                self.prev_state = self.state
            return

        if self.prev_state != self.state:
            logger.debug(f"当前状态:{self.state.value}")
            self.state_changed.emit(self.state.value)
            self.prev_state = self.state

        if self.state == E84State.IDLE:
            if self.E84Handoff():
                self.state = E84State.WAIT_TR_REQ
                # Unload 流程开始时发出 START 信号（VALID=1 之后，TR_REQ 之前）
                if self._unload_flow:
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
                # 使用握手时锁定的方向，而不是实时 FOUP_status
                unload_flow = (
                    self._unload_flow
                    if self._unload_flow is not None
                    else self.FOUP_status
                )
                self.state = (
                    E84State.WAIT_U_REQ if unload_flow else E84State.WAIT_L_REQ
                )

        elif self.state == E84State.WAIT_L_REQ:
            wait_status = self.E84_wait_L_REQ()
            if wait_status == 1:
                message = "L_REQ 阶段超时或信号中断，状态重置为 IDLE"
                logger.warning(message)
                self.warning.emit(message)
                self.state = E84State.IDLE
            elif wait_status == 2:
                self.state = E84State.WAIT_COMPT

        elif self.state == E84State.WAIT_U_REQ:
            wait_status = self.E84_wait_U_REQ()
            if wait_status == 1:
                message = "U_REQ 阶段超时或信号中断，状态重置为 IDLE"
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
                if self.FOUP_status:
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

    def _on_key_debounce_timeout(self) -> None:
        """非阻塞按键消抖：到期后确认输入已稳定再提交。"""

        if self._pending_key_value is None:
            return

        current_key_value = self.E84_InfoPin.read_all_inputs()
        if current_key_value == self._pending_key_value:
            self.E84_Key_Value = current_key_value
            self._pending_key_value = None
            return

        self._pending_key_value = current_key_value
        self._key_debounce_timer.start(self._key_debounce_ms)

    def Refresh_Input(self):
        self.E84_InSig_Value = self.E84_SigPin.read_all_inputs()
        self.E84_Key_Raw_Value = self.E84_InfoPin.read_all_inputs()
        # 只有在按键状态发生变化时才进行处理，避免频繁处理相同状态。
        # 注意：不要使用 time.sleep 阻塞 Qt 事件循环；改为 QTimer 单次定时确认输入稳定后再提交。
        if self.E84_Key_Raw_Value != self.E84_Key_Value:
            if self._pending_key_value != self.E84_Key_Raw_Value:
                self._pending_key_value = self.E84_Key_Raw_Value
                self._key_debounce_timer.start(self._key_debounce_ms)

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
        # 区分"检测到载具"（任意一键）与"完整落位"（三键全落，R02）
        self.FOUP_docked = bool(all_keys_on)

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

    @Slot()
    def set_ready_low_for_error(self) -> None:
        """执行机构上报错误时，强制拉低 READY 信号。"""

        self._actuator_error_latched = True
        self._error_latch_reported = False
        self._unload_flow = None
        self.state = E84State.IDLE
        self.prev_state = None
        self.E84_ResetSig()
        self.E84_InfoPin.set_output("LOAD_LED", LED_OFF)
        self.E84_InfoPin.set_output("UNLOAD_LED", LED_OFF)
        self.E84_SigPin.set_output("READY", SIG_OFF)
        logger.error("执行机构异常，锁存故障并强制 READY OFF")

    @Slot()
    def clear_ready_low_error_latch(self) -> None:
        """清除执行机构错误锁存，恢复 E84 正常握手。"""

        if not self._actuator_error_latched:
            logger.info("执行机构错误锁存未激活，忽略复位请求")
            return
        self._actuator_error_latched = False
        self._error_latch_reported = False
        self._unload_flow = None
        self.state = E84State.IDLE
        self.prev_state = None
        self.E84_ResetSig()
        logger.info("执行机构错误锁存已清除，E84 可恢复握手")

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

    def _handshake_active(self) -> bool:
        """E84 握手的前提输入是否仍然有效（R01）。

        GO 已在现场确认未接线（2026-10-09 删除），不再参与判定；握手前提就是
        标准的 CS_0 + VALID。
        """

        return bool(
            self.E84_InSig_Value["CS_0"] and self.E84_InSig_Value["VALID"]
        )

    def _handshake_revoked(self) -> bool:
        """握手前提被撤销时返回 True（R01）。

        R01：进入各阶段后如果 CS_0/VALID 被撤销，只保持 TR_REQ（或残留
        BUSY）不应继续输出 READY。安全做法是撤回输出并回到 IDLE。
        """

        return not self._handshake_active()

    def E84Handoff(self):
        if (
            self.E84_InSig_Value["CS_0"]
            and self.E84_InSig_Value["VALID"]
        ):
            logger.debug("检测到握手请求")
            # 方向在握手瞬间锁定：FOUP 在位=卸载，否则=装载。
            # 传输过程中 FOUP 可能已经被天车提走，后续判断不能再看实时状态。
            self._unload_flow = self.FOUP_status
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
        if self._handshake_revoked():
            # R01：只保持 TR_REQ 但 CS_0/VALID 已撤销时，不得置 READY
            logger.warning("握手前提已撤销（CS_0/VALID），撤回输出并回到 IDLE")
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
        if self._handshake_revoked():
            # R01：握手撤销后必须撤回已经置起的 READY
            logger.warning("握手前提已撤销（CS_0/VALID），撤回 READY 并回到 IDLE")
            self.E84_ResetSig()
            return 1
        if self.E84_InSig_Value["BUSY"]:
            self.E84_ResetTimer(LongTimer)
            logger.debug("GET BUSY")
            return 2
        return 0

    def E84_wait_L_REQ(self):
        if self._consume_timeout():
            # 下位机/天车保持信号但 FOUP 一直不落位：必须能超时复位，
            # 否则状态机会永久停在 WAIT_L_REQ（L_REQ、READY 一直输出）。
            self.E84_ResetSig()
            return 1
        if self._handshake_revoked():
            logger.warning("握手前提已撤销（CS_0/VALID），撤回 L_REQ 并回到 IDLE")
            self.E84_ResetSig()
            return 1
        if (
            not self.E84_InSig_Value["CS_0"]
            or not self.E84_InSig_Value["VALID"]
            or not self.E84_InSig_Value["TR_REQ"]
            or not self.E84_InSig_Value["BUSY"]
        ):
            self.E84_ResetSig()
            return 1
        # R02：完整落位（三键全落）才确认装载完成；只检测到载具不能撤回 L_REQ
        if self.FOUP_docked:
            self.E84_SigPin.set_output("L_REQ", SIG_OFF)
            self.E84_ResetTimer(LongTimer)
            logger.debug("set L_REQ OFF")
            return 2
        return 0

    def E84_wait_U_REQ(self):
        if self._consume_timeout():
            # 同上：FOUP 一直不被取走时也要能复位
            self.E84_ResetSig()
            return 1
        if self._handshake_revoked():
            logger.warning("握手前提已撤销（CS_0/VALID），撤回 U_REQ 并回到 IDLE")
            self.E84_ResetSig()
            return 1
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
        if self._handshake_revoked():
            logger.warning("握手前提已撤销（CS_0/VALID），撤回 READY 并回到 IDLE")
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
            self._unload_flow = None
            current_time = time.strftime("%H:%M:%S", time.localtime())
            logger.info(f"{current_time} TRANS OVER")
            return 2
        return 0

    def E84_main(self):
        """兼容旧入口，直接启动循环"""

        self.start()
