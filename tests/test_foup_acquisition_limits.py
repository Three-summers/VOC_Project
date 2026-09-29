"""FOUP 通道 OOC/OOS 超限报警测试。

业务规则：
- 只有"显示开关为真"的限界才参与判定（预设里把无意义的下限关掉，
  例如 VOC 的下限、Noise 的下限）；
- 同一通道同一帧最多上报一次，优先 OOS（更严重）；
- 报警文案不含实时数值，保证 AlarmStore 的 60s 去重可以抑制刷屏。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.foup_acquisition import FoupAcquisitionController


class _SeriesModelStub:
    def __init__(self) -> None:
        self.points: list[tuple[float, float]] = []

    def append_point(self, x: float, y: float) -> None:
        self.points.append((x, y))

    def clear(self) -> None:
        self.points = []


class FoupLimitAlarmTests(unittest.TestCase):
    def setUp(self) -> None:
        self.models = [_SeriesModelStub() for _ in range(2)]
        self.controller = FoupAcquisitionController(series_models=self.models)
        self.violations: list[tuple[str, str]] = []
        self.controller.limitViolation.connect(
            lambda level, message: self.violations.append((level, message))
        )
        # 先喂一帧：确定通道数并进入默认前缀命名空间（VOC / 1 通道）
        self.controller._handle_line("50.0")
        self.violations.clear()
        # 在生效的命名空间下设置测试用限界：OOC 80/20，OOS 90/10，全部可见
        self.controller.setChannelTitle(0, "VOC")
        self.controller.setChannelUnit(0, "ppb")
        self.controller.setChannelLimits(0, 80.0, 20.0, 90.0, 10.0, 50.0)
        self.controller.setShowLimits(0, True, True, True, True, True)
        self.violations.clear()

    def test_no_violation_inside_limits(self) -> None:
        self.controller._handle_line("50.0")
        self.assertEqual(self.violations, [])

    def test_ooc_upper_violation(self) -> None:
        self.controller._handle_line("85.0")
        self.assertEqual(len(self.violations), 1)
        level, message = self.violations[0]
        self.assertEqual(level, "OOC")
        self.assertIn("VOC", message)
        self.assertIn("80", message)

    def test_oos_upper_violation(self) -> None:
        self.controller._handle_line("95.0")
        self.assertEqual(len(self.violations), 1)
        level, message = self.violations[0]
        self.assertEqual(level, "OOS")
        self.assertIn("90", message)

    def test_oos_lower_violation(self) -> None:
        self.controller._handle_line("5.0")
        self.assertEqual(len(self.violations), 1)
        self.assertEqual(self.violations[0][0], "OOS")

    def test_hidden_limit_is_not_monitored(self) -> None:
        """显示开关关闭的限界不参与报警判定"""
        self.controller.setShowLimits(0, True, False, True, False, True)
        self.controller._handle_line("5.0")  # 低于下限，但下限已关闭
        self.assertEqual(self.violations, [])

    def test_nan_value_does_not_alarm(self) -> None:
        self.controller._handle_line("nan")
        self.assertEqual(self.violations, [])

    def test_message_is_stable_for_dedup(self) -> None:
        """同一越限重复出现时文案必须一致，否则 AlarmStore 无法去重"""
        self.controller._handle_line("85.0")
        self.controller._handle_line("86.0")
        self.assertEqual(len(self.violations), 2)
        self.assertEqual(self.violations[0][1], self.violations[1][1])

    def test_multi_channel_reports_each_channel_once(self) -> None:
        self.controller.setChannelTitle(1, "TEMP")
        self.controller.setChannelLimits(1, 80.0, 20.0, 90.0, 10.0, 50.0)
        self.controller.setShowLimits(1, True, True, True, True, True)
        self.controller._handle_line("85.0,95.0")
        levels = [level for level, _ in self.violations]
        self.assertEqual(sorted(levels), ["OOC", "OOS"])

    def test_no_alarm_before_any_data(self) -> None:
        self.controller._handle_line("")
        self.assertEqual(self.violations, [])


if __name__ == "__main__":
    unittest.main()
