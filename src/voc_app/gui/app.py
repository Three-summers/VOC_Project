import sys
import os
import threading
from pathlib import Path

# 路径设置必须在导入 voc_app 之前，以支持 python app.py 直接运行
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from datetime import datetime

from voc_app.logging_config import get_logger

logger = get_logger(__name__)

# 可选依赖：仅在树莓派环境存在 RPi.GPIO 时启用
try:
    import RPi.GPIO as GPIO  # type: ignore

    _HAS_RPI_GPIO = True
    _RPI_GPIO_IMPORT_ERROR = None
except Exception as exc:  # noqa: BLE001
    GPIO = None  # type: ignore[assignment]
    _HAS_RPI_GPIO = False
    _RPI_GPIO_IMPORT_ERROR = exc

# 性能配置必须在导入 PySide6 之前应用
from voc_app.gui.performance_config import (
    apply_performance_settings,
    get_spectrum_config_for_env,
)

apply_performance_settings()

from PySide6.QtCore import QObject, QMetaObject, QTimer, Qt, Signal, Slot
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from PySide6.QtCharts import QChartView, QAbstractSeries
from voc_app.gui.socket_client import Client, SocketCommunicator
from voc_app.gui.qml_socket_client_bridge import QmlSocketClientBridge
from voc_app.gui.csv_model import (
    CsvFileManager,
    ChartDataListModel,
    ChartDataGenerator,
    SeriesTableModel,
)
from voc_app.gui.alarm_store import AlarmStore
from voc_app.gui.spectrum_model import SpectrumDataModel, SpectrumSimulator
from voc_app.gui.file_tree_browser import FilePreviewController
from voc_app.gui.foup_acquisition import FoupAcquisitionController
from voc_app.loadport.ascii_serial import AsciiSerialClient


# 验证用户密钥
class AuthenticationManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._users = {"admin": "123456", "user": "user"}

    @Slot(str, str, result=bool)
    def login(self, username, password):
        if username in self._users and self._users[username] == password:
            return True
        return False


# 在后端隐藏特定图例，QML 中无此 API
class ChartLegendHelper(QObject):
    @Slot(QObject, list)
    def hideSeriesInLegend(self, chartView, series_list):
        if not series_list or len(series_list) == 0:
            return

        # 不要从 chartView 拿 chart，而是从 Series 反向获取，这是因为 QML 直接传无法获取对象
        # 任何一个已经添加到图表中的 Series 都可以通过 .chart() 方法获取其父图表
        first_series = series_list[0]

        # 注意：这里调用的是 C++ 的 chart() 方法，不是属性
        chart = first_series.chart()

        # 再次判空（如果 Series 还没被添加到图表，这里可能是 None）
        if not chart:
            logger.warning("Series is not attached to any chart yet.")
            return

        for series in series_list:
            if series:
                markers = chart.legend().markers(series)
                for marker in markers:
                    marker.setVisible(False)


class LoadportActuatorController(QObject):
    """管理 lock/insert 两套串口执行机构，并提供可复用的动作函数。"""

    actionSucceeded = Signal(str)
    actionFailed = Signal(str)
    serialErrorDetected = Signal(str, str)
    requestE84ErrorRecovery = Signal()

    def __init__(
        self,
        lock_client: AsciiSerialClient,
        insert_client: AsciiSerialClient,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._lock_client = lock_client
        self._insert_client = insert_client
        self._action_lock = threading.Lock()
        self._lock_client.set_message_callback(self._on_lock_message)
        self._insert_client.set_message_callback(self._on_insert_message)

    def _on_lock_message(self, line: str) -> None:
        self._handle_device_message("lock", line)

    def _on_insert_message(self, line: str) -> None:
        self._handle_device_message("insert", line)

    def _handle_device_message(self, source: str, line: str) -> None:
        payload = (line or "").strip()
        if not payload:
            return
        logger.debug(f"[{source}] {payload}")
        if payload.lower().startswith("error:"):
            self._handle_stm32_error(source, payload)

    def _handle_stm32_error(self, source: str, payload: str) -> None:
        message = f"{source} 串口上报异常: {payload}"
        logger.error(message)
        self.serialErrorDetected.emit(source, payload)
        self._on_stm32_error_placeholder(source, payload)

    def _on_stm32_error_placeholder(self, source: str, payload: str) -> None:
        """占位：后续可在此补充复位、重试或急停等恢复动作。"""
        logger.info(f"占位处理: source={source}, payload={payload}")

    def _ensure_connected(self, client: AsciiSerialClient, name: str) -> None:
        if client.is_connected:
            return
        logger.info(f"{name} 串口未连接，自动重连")
        client.connect()

    def run_unlock_only(self) -> bool:
        """只执行解锁动作。"""

        with self._action_lock:
            try:
                self._ensure_connected(self._lock_client, "lock")
                self._lock_client.set_unlock()
                message = "动作完成：unlock"
                logger.info(message)
                self.actionSucceeded.emit(message)
                return True
            except Exception as exc:  # noqa: BLE001
                message = f"解锁动作失败: {exc}"
                logger.error(message)
                self.actionFailed.emit(message)
                return False

    def run_lock_only(self) -> bool:
        """只执行锁定动作。"""

        with self._action_lock:
            try:
                self._ensure_connected(self._lock_client, "lock")
                self._lock_client.set_lock()
                message = "动作完成：lock"
                logger.info(message)
                self.actionSucceeded.emit(message)
                return True
            except Exception as exc:  # noqa: BLE001
                message = f"锁定动作失败: {exc}"
                logger.error(message)
                self.actionFailed.emit(message)
                return False

    def run_lock_reset(self) -> bool:
        """只执行锁定机构 reset 动作。"""

        with self._action_lock:
            try:
                self._ensure_connected(self._lock_client, "lock")
                self._lock_client.reset()
                message = "动作完成：lock reset"
                logger.info(message)
                self.actionSucceeded.emit(message)
                return True
            except Exception as exc:  # noqa: BLE001
                message = f"锁定机构 reset 失败: {exc}"
                logger.error(message)
                self.actionFailed.emit(message)
                return False

    def run_insert_reset(self) -> bool:
        """只执行对插机构 reset 动作。"""

        with self._action_lock:
            try:
                self._ensure_connected(self._insert_client, "insert")
                self._insert_client.reset()
                message = "动作完成：insert reset"
                logger.info(message)
                self.actionSucceeded.emit(message)
                return True
            except Exception as exc:  # noqa: BLE001
                message = f"对插机构 reset 失败: {exc}"
                logger.error(message)
                self.actionFailed.emit(message)
                return False

    def run_insert_for_load(self) -> bool:
        """只执行对插动作（move_to_step 4）。"""

        with self._action_lock:
            try:
                self._ensure_connected(self._insert_client, "insert")
                self._insert_client.move_to_step(4)
                message = "动作完成：move_to_step(4)"
                logger.info(message)
                self.actionSucceeded.emit(message)
                return True
            except Exception as exc:  # noqa: BLE001
                message = f"对插动作失败: {exc}"
                logger.error(message)
                self.actionFailed.emit(message)
                return False

    def run_insert_for_unload(self) -> bool:
        """只执行取消对插动作（move_to_step 8）。"""

        with self._action_lock:
            try:
                self._ensure_connected(self._insert_client, "insert")
                self._insert_client.move_to_step(8)
                message = "动作完成：move_to_step(8)"
                logger.info(message)
                self.actionSucceeded.emit(message)
                return True
            except Exception as exc:  # noqa: BLE001
                message = f"取消对插动作失败: {exc}"
                logger.error(message)
                self.actionFailed.emit(message)
                return False

    def run_unlock_for_unload(self) -> bool:
        """Unload 阶段：先取消对插(move_to_step 8)，再解锁(unlock)。"""

        with self._action_lock:
            try:
                self._ensure_connected(self._insert_client, "insert")
                self._ensure_connected(self._lock_client, "lock")
                self._insert_client.move_to_step(8)
                self._lock_client.set_unlock()
                message = "Unload 动作完成：move_to_step(8) -> unlock"
                logger.info(message)
                self.actionSucceeded.emit(message)
                return True
            except Exception as exc:  # noqa: BLE001
                message = f"Unload 动作失败: {exc}"
                logger.error(message)
                self.actionFailed.emit(message)
                return False

    def run_lock_for_load(self) -> bool:
        """Load 阶段：先锁定(lock)，再对插(move_to_step 4)。"""

        with self._action_lock:
            try:
                self._ensure_connected(self._lock_client, "lock")
                self._ensure_connected(self._insert_client, "insert")
                self._lock_client.set_lock()
                self._insert_client.move_to_step(4)
                message = "Load 动作完成：lock -> move_to_step(4)"
                logger.info(message)
                self.actionSucceeded.emit(message)
                return True
            except Exception as exc:  # noqa: BLE001
                message = f"Load 动作失败: {exc}"
                logger.error(message)
                self.actionFailed.emit(message)
                return False

    @Slot(result=bool)
    def unlockForUnload(self) -> bool:
        """供 UI 手动触发：执行 Unload 阶段解锁动作。"""

        return self.run_unlock_for_unload()

    @Slot(result=bool)
    def lockForLoad(self) -> bool:
        """供 UI 手动触发：执行 Load 阶段加锁动作。"""

        return self.run_lock_for_load()

    @Slot(result=bool)
    def unlockOnly(self) -> bool:
        """供 UI 手动触发：仅解锁。"""

        return self.run_unlock_only()

    @Slot(result=bool)
    def lockOnly(self) -> bool:
        """供 UI 手动触发：仅锁定。"""

        return self.run_lock_only()

    @Slot(result=bool)
    def lockReset(self) -> bool:
        """供 UI 手动触发：仅锁定机构 reset。"""

        return self.run_lock_reset()

    @Slot(result=bool)
    def insertReset(self) -> bool:
        """供 UI 手动触发：仅对插机构 reset。"""

        return self.run_insert_reset()

    @Slot(result=bool)
    def insertForLoad(self) -> bool:
        """供 UI 手动触发：仅对插（step 4）。"""

        return self.run_insert_for_load()

    @Slot(result=bool)
    def insertForUnload(self) -> bool:
        """供 UI 手动触发：仅取消对插（step 8）。"""

        return self.run_insert_for_unload()

    @Slot(result=bool)
    def recoverE84FromError(self) -> bool:
        """供 UI 手动触发：请求清除 E84 错误锁存并恢复握手。"""

        try:
            self.requestE84ErrorRecovery.emit()
            message = "已发送 E84 故障复位请求"
            logger.info(message)
            self.actionSucceeded.emit(message)
            return True
        except Exception as exc:  # noqa: BLE001
            message = f"发送 E84 故障复位请求失败: {exc}"
            logger.error(message)
            self.actionFailed.emit(message)
            return False


class LoadportBridge(QObject):
    """负责启动 loadport 线程并将错误/状态推送到 GUI"""

    def __init__(
        self,
        worker,
        alarm_store: AlarmStore,
        title_panel: QObject | None,
        foup_controller: QObject | None = None,
        actuator_controller: LoadportActuatorController | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._alarm_store = alarm_store
        self._title_panel = title_panel
        self._worker = worker
        self._foup_controller = foup_controller
        self._actuator_controller = actuator_controller
        self._controller = None
        self._pending_ready_low_due_to_error = False
        self._pending_error_recovery_request = False
        self._actuator_error_latched = False

        self._worker.started_controller.connect(self._on_started)
        self._worker.stopped_controller.connect(self._on_stopped)
        self._worker.error.connect(self._on_error)
        self._worker.e84_warning.connect(self._on_warning)
        self._worker.e84_fatal_error.connect(self._on_fatal)
        self._worker.e84_state_changed.connect(self._on_state_changed)
        if hasattr(self._worker, "controller_ready"):
            self._worker.controller_ready.connect(self._on_controller_ready)
        if hasattr(self._worker, "all_keys_set"):
            self._worker.all_keys_set.connect(self._on_all_keys_set)
        if self._actuator_controller:
            self._actuator_controller.serialErrorDetected.connect(
                self._on_actuator_serial_error
            )
            self._actuator_controller.requestE84ErrorRecovery.connect(
                self._on_request_e84_error_recovery
            )

    def start(self):
        """启动后台线程"""
        self._worker.start()

    def shutdown(self):
        """停止后台线程，确保退出时安全清理"""
        self._worker.stop()

    def _current_timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _set_title_message(self, message: str):
        """更新标题栏消息区域"""
        if self._title_panel:
            self._title_panel.setProperty("systemMessage", message)

    def _append_alarm(self, level: str, text: str):
        """发送报警并更新标题栏"""
        message = f"[{level}] {text}"
        timestamp = self._current_timestamp()
        if self._alarm_store:
            self._alarm_store.addAlarm(timestamp, message)
        self._set_title_message(message)

    def _on_started(self):
        self._set_title_message("Loadport 线程已启动")

    def _on_stopped(self):
        self._disconnect_controller_data_signals()
        self._pending_ready_low_due_to_error = False
        self._pending_error_recovery_request = False
        self._actuator_error_latched = False
        self._set_title_message("Loadport 线程已停止")

    def _on_error(self, message: str):
        self._append_alarm("ERROR", message)

    def _on_warning(self, message: str):
        self._append_alarm("WARNING", message)

    def _on_fatal(self, message: str):
        self._append_alarm("FATAL", message)

    def _on_state_changed(self, state: str):
        self._set_title_message(f"E84 状态: {state}")

    def _on_all_keys_set(self):
        self._set_title_message("E84 三键已落下，等待 Unload 触发采集命令")
        if self._foup_controller and not hasattr(
            self._foup_controller, "e84StartDataCollectionForUnload"
        ):
            self._foup_controller.startAcquisition()  # type: ignore

    def _on_controller_ready(self, controller) -> None:
        self._disconnect_controller_data_signals()
        self._controller = controller
        try:
            controller.data_collection_start.connect(self._on_data_collection_start)
            controller.data_collection_stop.connect(self._on_data_collection_stop)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"绑定 data_collection 信号失败: {exc}")
        if self._pending_ready_low_due_to_error and self._force_e84_ready_low_for_error():
            self._pending_ready_low_due_to_error = False
            self._actuator_error_latched = True
        if self._pending_error_recovery_request and self._clear_e84_error_latch():
            self._pending_error_recovery_request = False
            self._actuator_error_latched = False

    def _disconnect_controller_data_signals(self) -> None:
        if not self._controller:
            return
        try:
            self._controller.data_collection_start.disconnect(self._on_data_collection_start)
            self._controller.data_collection_stop.disconnect(self._on_data_collection_stop)
        except Exception:
            pass
        self._controller = None

    def _on_data_collection_start(self) -> None:
        self._set_title_message("E84 Unload 开始，执行解锁与采集启动")
        if self._actuator_controller and not self._actuator_controller.run_unlock_for_unload():
            self._append_alarm("ERROR", "Unload 解锁动作执行失败")
        if self._foup_controller and hasattr(
            self._foup_controller, "e84StartDataCollectionForUnload"
        ):
            ok = self._foup_controller.e84StartDataCollectionForUnload()  # type: ignore[attr-defined]
            if not ok:
                self._append_alarm("ERROR", "Unload 采集启动命令执行失败")

    def _on_data_collection_stop(self) -> None:
        self._set_title_message("E84 Load 完成，执行加锁与采集停止")
        if self._actuator_controller and not self._actuator_controller.run_lock_for_load():
            self._append_alarm("ERROR", "Load 加锁动作执行失败")
        if self._foup_controller and hasattr(
            self._foup_controller, "e84StopDataCollectionForLoad"
        ):
            ok = self._foup_controller.e84StopDataCollectionForLoad()  # type: ignore[attr-defined]
            if not ok:
                self._append_alarm("ERROR", "Load 采集停止命令执行失败")

    def _on_actuator_serial_error(self, source: str, payload: str) -> None:
        self._append_alarm("ERROR", f"{source} 串口上报异常: {payload}")
        self._actuator_error_latched = True
        if self._force_e84_ready_low_for_error():
            self._pending_ready_low_due_to_error = False
            return
        self._pending_ready_low_due_to_error = True

    def _on_request_e84_error_recovery(self) -> None:
        if not self._actuator_error_latched and not self._pending_ready_low_due_to_error:
            self._set_title_message("当前无 E84 故障锁存，无需复位")
            return
        if self._clear_e84_error_latch():
            self._pending_error_recovery_request = False
            self._pending_ready_low_due_to_error = False
            self._actuator_error_latched = False
            self._set_title_message("已请求清除 E84 故障锁存")
            return
        self._pending_error_recovery_request = True
        self._append_alarm("WARNING", "E84 控制器未就绪，故障复位请求已暂存")

    def _force_e84_ready_low_for_error(self) -> bool:
        controller = self._controller
        if controller is None:
            logger.warning("E84 控制器未就绪，暂存 READY 置低请求")
            return False
        if not hasattr(controller, "set_ready_low_for_error"):
            logger.warning("E84 控制器不支持 set_ready_low_for_error，忽略 READY 置低请求")
            return False
        try:
            invoked = QMetaObject.invokeMethod(
                controller,
                "set_ready_low_for_error",
                Qt.ConnectionType.QueuedConnection,
            )
            if not invoked:
                logger.warning("invoke set_ready_low_for_error 失败")
                return False
            logger.info("已请求 E84 READY 置低")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(f"请求 E84 READY 置低失败: {exc}")
            return False

    def _clear_e84_error_latch(self) -> bool:
        controller = self._controller
        if controller is None:
            logger.warning("E84 控制器未就绪，无法清除故障锁存")
            return False
        if not hasattr(controller, "clear_ready_low_error_latch"):
            logger.warning(
                "E84 控制器不支持 clear_ready_low_error_latch，忽略故障复位请求"
            )
            return False
        try:
            invoked = QMetaObject.invokeMethod(
                controller,
                "clear_ready_low_error_latch",
                Qt.ConnectionType.QueuedConnection,
            )
            if not invoked:
                logger.warning("invoke clear_ready_low_error_latch 失败")
                return False
            logger.info("已请求清除 E84 故障锁存")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(f"请求清除 E84 故障锁存失败: {exc}")
            return False


if __name__ == "__main__":
    if _HAS_RPI_GPIO and GPIO is not None:
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(25, GPIO.OUT)
            GPIO.output(25, GPIO.HIGH)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"RPi.GPIO 初始化失败，跳过 GPIO 置位: {exc}")
    elif _RPI_GPIO_IMPORT_ERROR is not None:
        logger.info(f"未检测到 RPi.GPIO，跳过 GPIO 置位: {_RPI_GPIO_IMPORT_ERROR}")

    app = QApplication(sys.argv)
    # 当最后一个窗口被关闭时，不要自动退出应用程序，以在 qml 动态调用 quit 退出
    app.setQuitOnLastWindowClosed(False)
    engine = QQmlApplicationEngine()

    socket_bridge = QmlSocketClientBridge(Client, SocketCommunicator)
    engine.rootContext().setContextProperty("clientBridge", socket_bridge)

    csv_file_manager = CsvFileManager()
    engine.rootContext().setContextProperty("csvFileManager", csv_file_manager)

    auth_manager = AuthenticationManager()
    engine.rootContext().setContextProperty("authManager", auth_manager)

    file_preview_controller = FilePreviewController()
    engine.rootContext().setContextProperty("fileController", file_preview_controller)
    log_dir = (APP_DIR / "Log").resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    engine.rootContext().setContextProperty("fileRootPath", str(log_dir))

    chart_legend_helper = ChartLegendHelper()
    engine.rootContext().setContextProperty("chartLegendHelper", chart_legend_helper)

    chart_list_model = ChartDataListModel()

    chart_generators_instances = []
    loadport_series_labels = ["Loadport 通道 1", "Loadport 通道 2"]
    for idx, label in enumerate(loadport_series_labels):
        series_model = SeriesTableModel(max_rows=60, parent=chart_list_model)
        generator = ChartDataGenerator(series_model)
        chart_list_model.addSeries(label, series_model)
        # chart_generators_instances.append(generator)
        # for _ in range(10):
        #     generator.generate_new_point()

    # 预创建最多8个FOUP通道的series models（支持动态多通道数据）
    foup_series_models = []
    max_foup_channels = 8
    for i in range(max_foup_channels):
        label = f"FOUP 通道 {i + 1}"
        # 这里给 30 行缓存，是因为太多数据可能会挤压坐标轴
        series_model = SeriesTableModel(max_rows=30, parent=chart_list_model)
        chart_list_model.addSeries(label, series_model)
        foup_series_models.append(series_model)

    engine.rootContext().setContextProperty("chartListModel", chart_list_model)

    # 频谱分析模型和模拟器
    spectrum_model = SpectrumDataModel(bin_count=256)
    # spectrum_simulator = SpectrumSimulator(spectrum_model)
    # spectrum_simulator.intervalMs = 50  # 20 Hz 更新率
    # spectrum_simulator.start()  # 自动启动模拟器
    engine.rootContext().setContextProperty("spectrumModel", spectrum_model)
    # engine.rootContext().setContextProperty("spectrumSimulator", spectrum_simulator)

    foup_acquisition = FoupAcquisitionController(
        foup_series_models,
        spectrum_model=spectrum_model,
    )
    engine.rootContext().setContextProperty("foupAcquisition", foup_acquisition)

    # 将性能配置传递给 QML，让频谱图组件根据环境调整效果
    spectrum_perf_config = get_spectrum_config_for_env()
    engine.rootContext().setContextProperty("spectrumPerfConfig", spectrum_perf_config)

    alarm_store = AlarmStore()
    # alarm_store.addAlarm("2025-11-10 18:24:00", "Temperature above threshold")
    engine.rootContext().setContextProperty("alarmStore", alarm_store)

    data_update_timer = QTimer()
    data_update_timer.setInterval(1000)
    data_update_timer.timeout.connect(
        lambda: [gen.generate_new_point() for gen in chart_generators_instances]
    )
    data_update_timer.start()

    loadport_bridge = None

    loadport_serial_lock_client = AsciiSerialClient(
        port="/dev/ttyUSB1",
        baudrate=115200,
        timeout=1.0,
    )
    loadport_serial_insert_client = AsciiSerialClient(
        port="/dev/ttyUSB2",
        baudrate=115200,
        timeout=1.0,
    )
    try:
        loadport_serial_lock_client.connect()
        loadport_serial_insert_client.connect()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Loadport 串口初始化失败: {exc}")
    for name, serial_client in (
        ("insert", loadport_serial_insert_client),
        ("lock", loadport_serial_lock_client),
    ):
        if not serial_client.is_connected:
            continue
        try:
            serial_client.home()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"{name} 串口回零失败: {exc}")

    loadport_actuator_controller = LoadportActuatorController(
        lock_client=loadport_serial_lock_client,
        insert_client=loadport_serial_insert_client,
    )

    def on_loadport_serial_error(source: str, payload: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alarm_store.addAlarm(timestamp, f"[ERROR] {source}: {payload}")
    engine.rootContext().setContextProperty(
        "loadportActuatorController",
        loadport_actuator_controller,
    )
    engine.rootContext().setContextProperty(
        "loadport_serial_lock_client",
        loadport_serial_lock_client,
    )
    engine.rootContext().setContextProperty(
        "loadport_serial_insert_client",
        loadport_serial_insert_client,
    )

    # 根据环境变量决定是否启用 E84 桥接（方便非树莓派环境下的调试）
    disable_e84_bridge = os.environ.get("DISABLE_E84_BRIDGE", "").lower() in {
        "1",
        "true",
        "yes",
    }
    serial_error_handled_by_bridge = False
    enable_e84_bridge = not disable_e84_bridge

    qml_file = APP_DIR / "qml" / "main.qml"
    engine.load(str(qml_file))

    if not engine.rootObjects():
        sys.exit(-1)

    root_obj = engine.rootObjects()[0]
    title_panel = root_obj.findChild(QObject, "title_message")
    if title_panel is None:
        logger.warning("未找到 TitlePanel(title_message)，状态消息将仅写入日志")

    if enable_e84_bridge:
        try:
            from voc_app.loadport.e84_thread import E84ControllerThread

            worker = E84ControllerThread()
            loadport_bridge = LoadportBridge(
                worker=worker,
                alarm_store=alarm_store,
                title_panel=title_panel,
                foup_controller=foup_acquisition,
                actuator_controller=loadport_actuator_controller,
            )
            loadport_bridge.start()
            serial_error_handled_by_bridge = True
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"未启动 E84 桥接: {exc}")

    if not serial_error_handled_by_bridge:
        loadport_actuator_controller.serialErrorDetected.connect(on_loadport_serial_error)

    # 暴露出消息框属性
    # main_item = root_obj.findChild(QObject, "title_message")
    # if main_item != None:
    #     main_item.setProperty("systemMessage", "Hello World")

    # 启动后如存在 CSV 日志，预先解析一份，便于 DataLog/FileView 直接展示
    # if csv_file_manager.csvFiles:
    #     csv_file_manager.parse_csv_file(csv_file_manager.csvFiles[0])

    app.aboutToQuit.connect(foup_acquisition.stopAcquisition)
    # app.aboutToQuit.connect(spectrum_simulator.stop)
    app.aboutToQuit.connect(loadport_serial_lock_client.disconnect)
    app.aboutToQuit.connect(loadport_serial_insert_client.disconnect)
    if loadport_bridge:
        app.aboutToQuit.connect(loadport_bridge.shutdown)

    sys.exit(app.exec())
