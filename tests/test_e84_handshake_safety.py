"""E84 握手撤销、落位判定与停机输出的安全回归（R01 / R02 / R04）。

R01：进入 WAIT_TR_REQ / WAIT_BUSY 后撤销 GO/CS_0/VALID，状态机仍会置 READY，
     对已经撤销的请求继续响应。
R02：任意一颗落位传感器有效就把 FOUP 当成完整落位，载具未正确落位时就撤回
     L_REQ，内部状态与 HO_AVBL/ES 不一致。
R04：stop() 只停定时器，不撤回 READY / L_REQ / U_REQ 等硬件输出。

三项都用假的 RPi.GPIO 驱动真实状态机；安全行为固定，不提供关闭开关。
"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class _FakeRPiGPIO(types.ModuleType):
    BCM = "BCM"
    IN = "IN"
    OUT = "OUT"
    PUD_UP = "PUD_UP"
    PUD_DOWN = "PUD_DOWN"
    HIGH = 1
    LOW = 0

    def __init__(self) -> None:
        super().__init__("RPi.GPIO")
        self.levels: dict[int, int] = {}
        self.mode = None

    def setmode(self, mode) -> None:
        self.mode = mode

    def setup(self, pin, direction, **kwargs) -> None:
        self.levels.setdefault(pin, self.LOW)

    def output(self, pin, state) -> None:
        self.levels[pin] = state

    def input(self, pin) -> int:
        return self.levels.get(pin, self.LOW)

    def cleanup(self) -> None:
        self.levels.clear()


class _FakeRPi(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("RPi")
        self.GPIO = _FakeRPiGPIO()


if "RPi" not in sys.modules:
    sys.modules["RPi"] = _FakeRPi()
    sys.modules["RPi.GPIO"] = sys.modules["RPi"].GPIO  # type: ignore[attr-defined]

from voc_app.loadport.e84_passive import (  # noqa: E402
    LED_OFF,
    LED_ON,
    SIG_OFF,
    SIG_ON,
    E84Controller,
    E84State,
)

GPIO = sys.modules["RPi.GPIO"]


ALL_INPUTS_IDLE = {
    "GO": False,
    "CS_0": False,
    "VALID": False,
    "TR_REQ": False,
    "BUSY": False,
    "COMPT": False,
}

HANDSHAKE_ACTIVE = {"GO": True, "CS_0": True, "VALID": True}


def _make_controller() -> E84Controller:
    controller = E84Controller()
    controller.E84_InSig_Value = dict(ALL_INPUTS_IDLE)
    return controller


def _output_on(controller: E84Controller, name: str) -> bool:
    """SIG_ON/LED_ON 在底层都是 False（低有效）。"""
    return GPIO.levels.get(controller.E84_OutSig[name], SIG_OFF) is SIG_ON


def _led_on(controller: E84Controller, name: str) -> bool:
    return GPIO.levels.get(controller.E84_InfoLED[name], LED_OFF) is LED_ON


# ------------------------------------------------------------------ R01


class E84HandshakeRevokeTests(unittest.TestCase):
    def test_revoked_handshake_does_not_raise_ready(self) -> None:
        controller = _make_controller()
        controller.state = E84State.WAIT_TR_REQ
        # 握手前提已撤销，但 TR_REQ 仍是高
        controller.E84_InSig_Value.update(
            {"GO": False, "CS_0": True, "VALID": True, "TR_REQ": True}
        )

        controller._process_state()

        self.assertEqual(
            controller.state,
            E84State.IDLE,
            "握手已撤销时不能进入 WAIT_BUSY",
        )
        self.assertFalse(
            _output_on(controller, "READY"),
            "握手撤销后不得再置 READY",
        )

    def test_revoked_handshake_withdraws_ready_in_wait_busy(self) -> None:
        controller = _make_controller()
        controller.state = E84State.WAIT_BUSY
        controller.E84_SigPin.set_output("READY", SIG_ON)
        controller.E84_InSig_Value.update(
            {"GO": False, "CS_0": True, "VALID": True, "TR_REQ": True, "BUSY": False}
        )

        controller._process_state()

        self.assertEqual(controller.state, E84State.IDLE)
        self.assertFalse(
            _output_on(controller, "READY"),
            "WAIT_BUSY 阶段握手撤销必须撤回 READY",
        )

    def test_revoked_handshake_resets_in_wait_l_req(self) -> None:
        controller = _make_controller()
        controller.state = E84State.WAIT_L_REQ
        controller.E84_SigPin.set_output("L_REQ", SIG_ON)
        controller.E84_InSig_Value.update(
            {"GO": False, "CS_0": True, "VALID": True, "TR_REQ": True, "BUSY": True}
        )

        controller._process_state()

        self.assertEqual(controller.state, E84State.IDLE)
        self.assertFalse(_output_on(controller, "L_REQ"))

    def test_active_handshake_still_reaches_busy(self) -> None:
        controller = _make_controller()
        controller.state = E84State.WAIT_TR_REQ
        controller.E84_InSig_Value.update({**HANDSHAKE_ACTIVE, "TR_REQ": True})

        controller._process_state()

        self.assertEqual(controller.state, E84State.WAIT_BUSY)
        self.assertTrue(_output_on(controller, "READY"))


# ------------------------------------------------------------------ R02


class E84DockingTests(unittest.TestCase):
    def test_partial_keys_are_detected_but_not_docked(self) -> None:
        controller = _make_controller()
        controller.E84_Key_Value = {"KEY_0": True, "KEY_1": False, "KEY_2": False}
        controller.E84_Key_Raw_Value = dict(controller.E84_Key_Value)

        controller.Refresh_Input()

        self.assertTrue(controller.FOUP_status, "任意一键有效应视为检测到载具")
        self.assertFalse(
            controller.FOUP_docked,
            "只有一颗传感器有效不能视为完整落位",
        )

    def test_all_keys_are_docked(self) -> None:
        controller = _make_controller()
        controller.E84_Key_Value = {"KEY_0": True, "KEY_1": True, "KEY_2": True}
        controller.E84_Key_Raw_Value = dict(controller.E84_Key_Value)

        controller.Refresh_Input()

        self.assertTrue(controller.FOUP_docked)

    def test_load_completion_requires_full_docking(self) -> None:
        controller = _make_controller()
        controller.state = E84State.WAIT_L_REQ
        controller.FOUP_status = True
        controller.FOUP_docked = False
        controller.E84_SigPin.set_output("L_REQ", SIG_ON)
        controller.E84_InSig_Value.update(
            {"GO": True, "CS_0": True, "VALID": True, "TR_REQ": True, "BUSY": True}
        )

        controller._process_state()

        self.assertEqual(
            controller.state,
            E84State.WAIT_L_REQ,
            "载具未完整落位时不能确认装载完成",
        )
        self.assertTrue(
            _output_on(controller, "L_REQ"),
            "未完整落位前不得撤回 L_REQ",
        )

        controller.FOUP_docked = True
        controller._process_state()

        self.assertEqual(controller.state, E84State.WAIT_COMPT)
        self.assertFalse(_output_on(controller, "L_REQ"))


# ------------------------------------------------------------------ R04


class E84SafeStopTests(unittest.TestCase):
    def test_stop_withdraws_all_handshake_outputs(self) -> None:
        controller = _make_controller()
        controller.state = E84State.WAIT_BUSY
        controller._unload_flow = True
        controller.E84_SigPin.set_output("READY", SIG_ON)
        controller.E84_SigPin.set_output("U_REQ", SIG_ON)
        controller.E84_SigPin.set_output("L_REQ", SIG_ON)
        controller.E84_InfoPin.set_output("LOAD_LED", LED_ON)
        controller.E84_InfoPin.set_output("UNLOAD_LED", LED_ON)

        controller.stop()

        self.assertEqual(controller.state, E84State.IDLE)
        self.assertIsNone(controller._unload_flow)
        for name in ("READY", "U_REQ", "L_REQ"):
            self.assertFalse(
                _output_on(controller, name),
                f"停机后 {name} 必须撤回",
            )
        self.assertFalse(_led_on(controller, "LOAD_LED"))
        self.assertFalse(_led_on(controller, "UNLOAD_LED"))


if __name__ == "__main__":
    unittest.main()
