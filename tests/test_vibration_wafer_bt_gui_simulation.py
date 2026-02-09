"""vibration_wafer_bt_gui 模拟模式冒烟测试

- Date: 2026-01-16
- Executor: Codex

说明：
- 该测试不依赖 bleak/真实 BLE 设备，仅验证 simulation 模式能驱动模型产生数据点。
- 不创建 QML ChartView（避免 headless 环境下 QtCharts 的已知崩溃）。
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# 必须在导入 PySide6 之前设置（否则 Qt 平台插件可能初始化失败）
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = ROOT_DIR / "vibration_wafer_bt_gui"
SRC_DIR = PROJECT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtGui import QGuiApplication

from vibration_wafer_bt_gui.ble_controller import BleChartController
from vibration_wafer_bt_gui.series_model import SeriesTableModel


_app = None


def get_app() -> QGuiApplication:
    global _app
    if _app is None:
        _app = QGuiApplication.instance()
        if _app is None:
            _app = QGuiApplication([])
    return _app


class TestVibrationWaferBtGuiSimulation(unittest.TestCase):
    def test_simulation_produces_points(self):
        _ = get_app()

        ax_x_model = SeriesTableModel(max_rows=200)
        ax_y_model = SeriesTableModel(max_rows=200)
        ax_z_model = SeriesTableModel(max_rows=200)
        controller = BleChartController(ax_x_model, ax_y_model, ax_z_model)

        controller.startSimulation()

        loop = QEventLoop()
        QTimer.singleShot(200, loop.quit)
        loop.exec()

        controller.stop()

        self.assertGreater(ax_x_model.rowCount(), 0)
        self.assertGreater(ax_y_model.rowCount(), 0)
        self.assertGreater(ax_z_model.rowCount(), 0)

