import sys
import os
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

# 性能配置必须在导入 PySide6 之前应用
from voc_app.gui.performance_config import apply_performance_settings, get_spectrum_config_for_env
apply_performance_settings()

from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from PySide6.QtCharts import QChartView, QAbstractSeries

# 非树莓环境调试：临时禁用 loadport 硬件线程的导入，避免 RPi.GPIO 依赖阻塞 GUI 启动
# from voc_app.loadport.e84_thread import E84ControllerThread
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


class LoadportBridge(QObject):
    """负责启动 loadport 线程并将错误/状态推送到 GUI"""

    def __init__(
        self,
        worker,
        alarm_store: AlarmStore,
        title_panel: QObject | None,
        foup_controller: QObject | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._alarm_store = alarm_store
        self._title_panel = title_panel
        self._worker = worker
        self._foup_controller = foup_controller

        self._worker.started_controller.connect(self._on_started)
        self._worker.stopped_controller.connect(self._on_stopped)
        self._worker.error.connect(self._on_error)
        self._worker.e84_warning.connect(self._on_warning)
        self._worker.e84_fatal_error.connect(self._on_fatal)
        self._worker.e84_state_changed.connect(self._on_state_changed)
        if hasattr(self._worker, "all_keys_set"):
            self._worker.all_keys_set.connect(self._on_all_keys_set)

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
        self._set_title_message("E84 三键已落下，自动启动采集")
        if self._foup_controller:
            self._foup_controller.startAcquisition() # type: ignore

if __name__ == "__main__":
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
        chart_generators_instances.append(generator)
        for _ in range(10):
            generator.generate_new_point()

    # 预创建最多8个FOUP通道的series models（支持动态多通道数据）
    foup_series_models = []
    max_foup_channels = 8
    for i in range(max_foup_channels):
        label = f"FOUP 通道 {i + 1}"
        series_model = SeriesTableModel(max_rows=60, parent=chart_list_model)
        chart_list_model.addSeries(label, series_model)
        foup_series_models.append(series_model)

    engine.rootContext().setContextProperty("chartListModel", chart_list_model)

    # 频谱分析模型和模拟器
    spectrum_model = SpectrumDataModel(bin_count=256)
    spectrum_simulator = SpectrumSimulator(spectrum_model)
    spectrum_simulator.intervalMs = 50  # 20 Hz 更新率
    spectrum_simulator.start()  # 自动启动模拟器
    engine.rootContext().setContextProperty("spectrumModel", spectrum_model)
    engine.rootContext().setContextProperty("spectrumSimulator", spectrum_simulator)

    foup_acquisition = FoupAcquisitionController(
        foup_series_models,
        spectrum_model=spectrum_model,
        spectrum_simulator=None,
    )
    engine.rootContext().setContextProperty("foupAcquisition", foup_acquisition)

    # 将性能配置传递给 QML，让频谱图组件根据环境调整效果
    spectrum_perf_config = get_spectrum_config_for_env()
    engine.rootContext().setContextProperty("spectrumPerfConfig", spectrum_perf_config)

    alarm_store = AlarmStore()
    # alarm_store.addAlarm("2025-11-10 18:24:00", "Temperature above threshold")
    # alarm_store.addAlarm("2025-11-10 18:25:30", "Pressure sensor offline")
    # alarm_store.addAlarm("2025-11-10 18:25:31", "Pressure sensor offline.")
    # alarm_store.addAlarm("2025-11-10 18:25:32", "Pressure sensor offline..")
    # alarm_store.addAlarm("2025-11-10 18:25:33", "Pressure sensor offline...")
    engine.rootContext().setContextProperty("alarmStore", alarm_store)

    data_update_timer = QTimer()
    data_update_timer.setInterval(1000)
    data_update_timer.timeout.connect(
        lambda: [gen.generate_new_point() for gen in chart_generators_instances]
    )
    data_update_timer.start()

    loadport_bridge = None
    # 根据环境变量决定是否启用 E84 桥接（方便非树莓派环境下的调试）
    disable_e84_bridge = os.environ.get("DISABLE_E84_BRIDGE", "").lower() in {
        "1",
        "true",
        "yes",
    }
    enable_e84_bridge = not disable_e84_bridge
    if enable_e84_bridge:
        try:
            from voc_app.loadport.e84_thread import E84ControllerThread

            worker = E84ControllerThread()
            loadport_bridge = LoadportBridge(
                worker=worker,
                alarm_store=alarm_store,
                title_panel=None,
                foup_controller=foup_acquisition,
            )
            loadport_bridge.start()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"未启动 E84 桥接: {exc}")

    qml_file = APP_DIR / "qml" / "main.qml"
    engine.load(str(qml_file))

    if not engine.rootObjects():
        sys.exit(-1)

    # 暴露出消息框属性
    # root_obj = engine.rootObjects()[0]
    # main_item = root_obj.findChild(QObject, "title_message")
    # if main_item != None:
    #     main_item.setProperty("systemMessage", "Hello World")

    # 启动后如存在 CSV 日志，预先解析一份，便于 DataLog/FileView 直接展示
    # if csv_file_manager.csvFiles:
    #     csv_file_manager.parse_csv_file(csv_file_manager.csvFiles[0])

    app.aboutToQuit.connect(foup_acquisition.stopAcquisition)
    # app.aboutToQuit.connect(spectrum_simulator.stop)
    if loadport_bridge:
        app.aboutToQuit.connect(loadport_bridge.shutdown)

    sys.exit(app.exec())
