from enum import StrEnum
import time

from PySide6.QtCore import QObject, QTimer, Signal

from voc_app.loadport.gpio_controller import GPIOController


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

    def __init__(self, refresh_interval: float = 0.2):
        """使用PySide6定时逻辑的E84控制器"""

        super().__init__()
        self.refresh_interval = refresh_interval

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

        self.E84_SigPin = GPIOController(
            self.E84_InSig, self.E84_OutSig, IN_PUL_UP, SIG_OFF
        )
        self.E84_InfoPin = GPIOController(
            self.E84_FoupKey, self.E84_InfoLED, IN_PUL_DOWN, LED_OFF
        )
        self.E84_InSig_Value = self.E84_SigPin.read_all_inputs()
        self.E84_Key_Value = self.E84_InfoPin.read_all_inputs()
        self.E84_Key_Old_Value = self.E84_Key_Value.copy()

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
        """停止定时器并清理状态"""

        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        self._stop_timeout()

    def _run_cycle(self):
        self.Refresh_Input()
        self._process_state()

    def _process_state(self):
        if self.prev_state != self.state:
            print(f"当前状态:{self.state.value}")
            self.state_changed.emit(self.state.value)
            self.prev_state = self.state

        if self.state == E84State.IDLE:
            if self.E84Handoff():
                self.state = E84State.WAIT_TR_REQ

        elif self.state == E84State.WAIT_TR_REQ:
            wait_status = self.E84_wait_TR_REQ()
            if wait_status == 1:
                message = "等待 TR_REQ 信号超时，状态重置为 IDLE"
                print(message)
                self.warning.emit(message)
                self.state = E84State.IDLE
            elif wait_status == 2:
                self.state = E84State.WAIT_BUSY

        elif self.state == E84State.WAIT_BUSY:
            wait_status = self.E84_wait_BUSY()
            if wait_status == 1:
                message = "等待 BUSY 信号超时，状态重置为 IDLE"
                print(message)
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
                print(message)
                self.warning.emit(message)
                self.state = E84State.IDLE
            elif wait_status == 2:
                self.state = E84State.WAIT_COMPT

        elif self.state == E84State.WAIT_U_REQ:
            wait_status = self.E84_wait_U_REQ()
            if wait_status == 1:
                message = "U_REQ 阶段检测到信号中断，状态重置为 IDLE"
                print(message)
                self.warning.emit(message)
                self.state = E84State.IDLE
            elif wait_status == 2:
                self.state = E84State.WAIT_COMPT

        elif self.state == E84State.WAIT_COMPT:
            wait_status = self.E84_wait_COMPT()
            if wait_status == 1:
                message = "等待 COMPT 信号超时，状态重置为 IDLE"
                print(message)
                self.warning.emit(message)
                self.state = E84State.IDLE
            elif wait_status == 2:
                self.state = E84State.WAIT_DONE

        elif self.state == E84State.WAIT_DONE:
            wait_status = self.E84_wait_DONE()
            if wait_status == 1:
                message = "等待 DONE 判定超时，状态重置为 IDLE"
                print(message)
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
                print("FOUP 落回")
            else:
                print("FOUP 移走")

        if self.E84_InSig_Value["GO"]:
            self.E84_InfoPin.set_output("SENSOR_LED", LED_ON)
        else:
            message = "GO 信号为低，SENSOR_LED 熄灭"
            print(message)
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
            print("检测到握手请求")
            if self.FOUP_status:
                self.E84_SigPin.set_output("U_REQ", SIG_ON)
                self.E84_InfoPin.set_output("UNLOAD_LED", LED_ON)
                print("set U_REQ ON")
            else:
                self.E84_SigPin.set_output("L_REQ", SIG_ON)
                self.E84_InfoPin.set_output("LOAD_LED", LED_ON)
                print("set L_REQ ON")

            self.E84_ResetTimer(ShortTimer)
            return 1
        return 0

    def E84_wait_TR_REQ(self):
        if self._consume_timeout():
            self.E84_ResetSig()
            return 1
        if self.E84_InSig_Value["TR_REQ"]:
            self.E84_SigPin.set_output("READY", SIG_ON)
            print("set READY ON")
            self.E84_ResetTimer(ShortTimer)
            return 2
        return 0

    def E84_wait_BUSY(self):
        if self._consume_timeout():
            self.E84_ResetSig()
            return 1
        if self.E84_InSig_Value["BUSY"]:
            self.E84_ResetTimer(LongTimer)
            print("GET BUSY")
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
            print("set L_REQ OFF")
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
            print("set U_REQ OFF")
            return 2
        return 0

    def E84_wait_COMPT(self):
        if self._consume_timeout():
            self.E84_ResetSig()
            return 1
        if self.E84_InSig_Value["COMPT"]:
            self.E84_SigPin.set_output("READY", SIG_OFF)
            self.E84_ResetTimer(ShortTimer)
            print("set READY OFF")
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
            print(f"{current_time} TRANS OVER:")
            return 2
        return 0

    def E84_main(self):
        """兼容旧入口，直接启动循环"""

        self.start()
