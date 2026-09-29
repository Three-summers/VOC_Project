"""端到端：模拟下位机 → 下载 → 界面数据模型（A5 的核心业务目标）。

用真实的 TCP 长度前缀协议起一个假下位机（与 voc_251028 的
socket_cmd_server.c 行为一致：get_function_version_info 回 "VOC,V1.0.0"，
get <dir> 递归下发 D_START/FILE/D_END），验证：

    _download_logs() → 落盘到数据目录 → refresh_csv_files() → parse_csv_file()
    → 数据模型有数据点

这条链路以前是断的（文件列表不刷新 + 设备时间戳解析不了 → 图表永远空白）。
"""

from __future__ import annotations

import socket
import struct
import time
import sys
import threading
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app import app_paths
from voc_app.gui.csv_model import CsvFileManager
from voc_app.gui.foup_acquisition import FoupAcquisitionController

REMOTE_ROOT = "/home/root/files"
DEVICE_CSV = (
    "timestamp, area_data, mark_data, AQ7PID, PM_AVG, PD_AVG, FM_AVG, PumpM_AVG\n"
    "2026-02-26 10:30:00.123,12,3,1.5,2.5,3.5,4.5,5.5\n"
    "2026-02-26 10:30:01.223,12,3,1.6,2.6,3.6,4.6,5.6\n"
)


def _send_prefixed(conn: socket.socket, text: str) -> None:
    payload = text.encode("utf-8")
    conn.sendall(struct.pack(">I", len(payload)) + payload)


def _recv_exact(conn: socket.socket, size: int) -> bytes | None:
    data = bytearray()
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            return None
        data.extend(chunk)
    return bytes(data)


class _DeviceStub:
    """最小下位机替身：只实现版本查询与目录下发。"""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self._ready = threading.Event()
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(2)
        self.port = self._server.getsockname()[1]

    def start(self) -> None:
        threading.Thread(target=self._serve, daemon=True).start()
        self._ready.wait(timeout=2.0)

    def _serve(self) -> None:
        self._ready.set()
        while True:
            try:
                conn, _addr = self._server.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        with conn:
            while True:
                header = _recv_exact(conn, 4)
                if not header:
                    return
                (length,) = struct.unpack(">I", header)
                payload = _recv_exact(conn, length) if length else b""
                if payload is None:
                    return
                command = payload.decode("utf-8").strip()
                if command == "get_function_version_info":
                    _send_prefixed(conn, "VOC,V1.0.0")
                elif command.startswith("get "):
                    self._stream_directory(conn, command[4:].strip())
                elif command.endswith("_start"):
                    # 下位机 start 命令不回 ACK，只开始推送数据
                    threading.Thread(
                        target=self._push_samples, args=(conn,), daemon=True
                    ).start()
                else:
                    _send_prefixed(conn, "ACK")

    def _push_samples(self, conn: socket.socket, count: int = 5) -> None:
        """模拟下位机测试模式：0.5s 一个单值数据帧。"""
        for index in range(count):
            try:
                _send_prefixed(conn, f"{100.0 + index:.6f}\n")
            except OSError:
                return
            time.sleep(0.05)

    def _stream_directory(self, conn: socket.socket, client_path: str) -> None:
        _send_prefixed(conn, f"D_START {client_path}")
        for path in sorted(self.data_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(self.data_dir).as_posix()
            client_file = f"{client_path.rstrip('/')}/{relative}"
            data = path.read_bytes()
            _send_prefixed(conn, f"FILE {client_file} {len(data)}")
            conn.sendall(data)
        _send_prefixed(conn, f"D_END {client_path}")


class DownloadToUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.device_files = Path(app_paths.get_log_directory()) / "device_source"
        (self.device_files / "csv_file").mkdir(parents=True, exist_ok=True)
        (self.device_files / "csv_file" / "data202602261030.csv").write_text(
            DEVICE_CSV, encoding="utf-8"
        )
        self.server = _DeviceStub(self.device_files)
        self.server.start()
        self.controller = FoupAcquisitionController(
            series_models=[], host="127.0.0.1", port=self.server.port
        )
        self.controller.normalModeRemotePath = REMOTE_ROOT

    def test_downloaded_device_csv_becomes_chartable_points(self) -> None:
        saved_files = self.controller._download_logs()

        self.assertTrue(saved_files, "应当下载到设备 CSV")
        log_dir = Path(app_paths.get_log_directory())
        manager = CsvFileManager(log_dir=log_dir)
        manager.refresh_csv_files()

        downloaded = [
            name for name in manager.csvFiles if name.endswith("data202602261030.csv")
        ]
        self.assertTrue(downloaded, f"下载的文件应出现在列表中: {manager.csvFiles}")

        manager.parse_csv_file(manager.latest_csv_file())
        points = manager.dataModel.get(0)["dataPoints"]
        self.assertEqual(len(points), 2, "设备格式 CSV 必须解析出数据点")
        self.assertAlmostEqual(points[0]["y"], 12.0, places=6)

    def test_zero_file_download_is_reported_as_error(self) -> None:
        empty = Path(app_paths.get_log_directory()) / "empty_source"
        empty.mkdir(parents=True, exist_ok=True)
        stub = _DeviceStub(empty)
        stub.start()
        controller = FoupAcquisitionController(
            series_models=[], host="127.0.0.1", port=stub.port
        )
        controller.normalModeRemotePath = REMOTE_ROOT
        errors: list[str] = []
        controller.errorOccurred.connect(errors.append)

        files = controller._download_logs()
        controller._report_download(files)

        self.assertEqual(files, [])
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()


class _RecordingSeriesModel:
    """线程安全的曲线模型替身。"""

    def __init__(self) -> None:
        self._points: list[tuple[float, float]] = []

    def append_point(self, x: float, y: float) -> None:
        self._points.append((float(x), float(y)))

    def clear(self) -> None:
        self._points = []

    @property
    def points(self) -> list[tuple[float, float]]:
        return list(self._points)


class RealtimeStreamTests(unittest.TestCase):
    def test_test_mode_stream_fills_series_model(self) -> None:
        """测试模式：连接 → 版本 → 采样类型 → start → 数据点进入曲线"""
        from PySide6.QtCore import QCoreApplication

        app = QCoreApplication.instance() or QCoreApplication([])
        source = Path(app_paths.get_log_directory()) / "stream_source"
        source.mkdir(parents=True, exist_ok=True)
        stub = _DeviceStub(source)
        stub.start()

        model = _RecordingSeriesModel()
        controller = FoupAcquisitionController(
            series_models=[model], host="127.0.0.1", port=stub.port
        )
        controller.startAcquisition()

        deadline = time.time() + 5.0
        while time.time() < deadline and len(model.points) < 2:
            app.processEvents()
            time.sleep(0.01)

        controller.stopAcquisition()
        app.processEvents()
        controller._cleanup()

        self.assertGreaterEqual(
            len(model.points), 2, "实时曲线必须收到数据点（跨线程信号要投递到主线程）"
        )
        values = [y for _x, y in model.points]
        self.assertAlmostEqual(values[0], 100.0, places=3)
        self.assertEqual(controller.serverType, "VOC")
