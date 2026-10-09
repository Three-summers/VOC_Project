"""E84 状态机业务时序测试（无需硬件）。

`voc_app.loadport.e84_passive` 目前没有任何测试。这里用假的 RPi.GPIO 模块驱动
真实状态机，覆盖两件事：

1. 一条正常的 Unload 握手走完并回到 IDLE（回归保护）；
2. B5：WAIT_L_REQ/WAIT_U_REQ 阶段的 60s 超时必须生效（曾因不消费
   timeout_expired 而永久卡死）；
3. B6：load/unload 方向必须在握手瞬间锁定，不能按实时 FOUP_status 二次判定。
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

from voc_app.loadport.e84_passive import E84Controller, E84State  # noqa: E402


ALL_INPUTS_IDLE = {
    "CS_0": False,
    "VALID": False,
    "TR_REQ": False,
    "BUSY": False,
    "COMPT": False,
}


def _make_controller() -> E84Controller:
    controller = E84Controller()
    controller.E84_InSig_Value = dict(ALL_INPUTS_IDLE)
    return controller


class E84HappyPathTests(unittest.TestCase):
    def test_unload_handshake_completes_and_returns_to_idle(self) -> None:
        controller = _make_controller()
        states: list[str] = []
        controller.state_changed.connect(states.append)
        starts: list[bool] = []
        controller.data_collection_start.connect(lambda: starts.append(True))

        # FOUP 在位 → 应当走 Unload 流程
        controller.FOUP_status = True
        controller.E84_InSig_Value.update({"CS_0": True, "VALID": True})
        controller._process_state()
        self.assertEqual(controller.state, E84State.WAIT_TR_REQ)
        self.assertEqual(starts, [True], "Unload 开始时应发出采集启动信号")

        controller.E84_InSig_Value["TR_REQ"] = True
        controller._process_state()
        self.assertEqual(controller.state, E84State.WAIT_BUSY)

        controller.E84_InSig_Value["BUSY"] = True
        controller._process_state()
        self.assertEqual(controller.state, E84State.WAIT_U_REQ)

        # 天车取走 FOUP → 按键释放
        controller.FOUP_status = False
        controller._process_state()
        self.assertEqual(controller.state, E84State.WAIT_COMPT)

        controller.E84_InSig_Value["COMPT"] = True
        controller._process_state()
        self.assertEqual(controller.state, E84State.WAIT_DONE)

        controller.E84_InSig_Value.update(
            {"CS_0": False, "VALID": False, "COMPT": False}
        )
        controller._process_state()
        self.assertEqual(controller.state, E84State.IDLE)
        self.assertIn("idle", states)


class E84TimingRegressionTests(unittest.TestCase):
    def test_wait_l_req_phase_honours_the_armed_timeout(self) -> None:
        """B5（已修复）：L_REQ/U_REQ 阶段武装了 60s 定时器却从不消费，卡住后无法恢复。"""
        controller = _make_controller()
        controller.FOUP_status = False
        controller.state = E84State.WAIT_L_REQ
        controller.E84_InSig_Value.update(
            {"CS_0": True, "VALID": True, "TR_REQ": True, "BUSY": True}
        )
        # 模拟 LongTimer 已到期（QTimer 由事件循环触发，这里直接置标志）
        controller.timeout_expired = True

        controller._process_state()

        self.assertEqual(
            controller.state,
            E84State.IDLE,
            "等待 L_REQ 超时后应复位到 IDLE，而不是永久卡住",
        )

    def test_direction_is_latched_at_handoff(self) -> None:
        """B6（已修复）：load/unload 方向在 WAIT_BUSY 处按实时 FOUP_status 二次判定，
        FOUP 被提前提走会走错分支。"""
        controller = _make_controller()
        controller.FOUP_status = True  # FOUP 在位 → 本次是 Unload
        controller.E84_InSig_Value.update({"CS_0": True, "VALID": True})
        controller._process_state()
        self.assertEqual(controller.state, E84State.WAIT_TR_REQ)

        controller.E84_InSig_Value["TR_REQ"] = True
        controller._process_state()
        self.assertEqual(controller.state, E84State.WAIT_BUSY)

        # 天车在 BUSY 阶段已经把 FOUP 提走
        controller.FOUP_status = False
        controller.E84_InSig_Value["BUSY"] = True
        controller._process_state()

        self.assertEqual(
            controller.state,
            E84State.WAIT_U_REQ,
            "方向应在握手时锁定为 Unload，不能因 FOUP 已离位改判为 Load",
        )


if __name__ == "__main__":
    unittest.main()
