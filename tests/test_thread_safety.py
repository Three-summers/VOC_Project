"""线程安全压力测试。

目标：
- 多线程并发访问 FoupAcquisitionController 的共享状态，不发生异常/死锁
- 验证锁使用一致性带来的稳定性提升
"""

from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.foup_acquisition import FoupAcquisitionController


class _NoopSeriesModel:
    """最小可用曲线模型（避免引入 QtCharts 依赖）。"""

    def append_point(self, x, y):  # noqa: ANN001
        return None

    def clear(self) -> None:
        return None


class TestFoupAcquisitionThreadSafety(unittest.TestCase):
    def test_concurrent_handle_line_and_property_reads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "channel_config.json"
            controller = FoupAcquisitionController(
                series_models=[_NoopSeriesModel() for _ in range(3)],
                host="127.0.0.1",
                port=0,
                channel_config_path=config_path,
            )

            barrier = threading.Barrier(8)
            errors: list[BaseException] = []
            lock = threading.Lock()

            def writer() -> None:
                try:
                    barrier.wait(timeout=2.0)
                    for _ in range(300):
                        controller._handle_line("1.0,2.0,3.0")
                except BaseException as exc:  # noqa: BLE001 - 测试聚合异常
                    with lock:
                        errors.append(exc)

            def reader() -> None:
                try:
                    barrier.wait(timeout=2.0)
                    for _ in range(300):
                        _ = controller.running
                        _ = controller.statusMessage
                        _ = controller.channelCount
                        _ = controller.lastValue
                        _ = controller.getChannelValue(0)
                except BaseException as exc:  # noqa: BLE001 - 测试聚合异常
                    with lock:
                        errors.append(exc)

            threads: list[threading.Thread] = []
            for _ in range(4):
                threads.append(threading.Thread(target=writer, daemon=True))
            for _ in range(4):
                threads.append(threading.Thread(target=reader, daemon=True))

            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5.0)

            alive = [t for t in threads if t.is_alive()]
            if alive:
                self.fail(f"线程未能正常退出，疑似死锁/阻塞: {len(alive)}")

            if errors:
                self.fail(f"并发访问出现异常: {errors[0]!r}")

            self.assertEqual(controller.channelCount, 3)
