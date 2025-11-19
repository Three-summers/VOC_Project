import sys
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject, QTimer, Slot

from socket_client import Client, SocketCommunicator
from qml_socket_client_bridge import QmlSocketClientBridge

# 将项目根目录加入 sys.path，便于导入 sibling 模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

NEW_LOADPORT_DIR = PROJECT_ROOT / "new_loadport"
if str(NEW_LOADPORT_DIR) not in sys.path:
    sys.path.append(str(NEW_LOADPORT_DIR))

from new_loadport.e84_thread import E84ControllerThread
from csv_model import (
    CsvFileManager,
    ChartDataListModel,
    ChartDataGenerator,
    SeriesTableModel,
)
from alarm_store import AlarmStore
from file_tree_browser import FilePreviewController


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


class LoadportBridge(QObject):
    """负责启动 loadport 线程并将错误/状态推送到 GUI"""

    def __init__(self, alarm_store: AlarmStore, title_panel: QObject | None, parent=None):
        super().__init__(parent)
        self._alarm_store = alarm_store
        self._title_panel = title_panel
        self._worker = E84ControllerThread(self)

        self._worker.started_controller.connect(self._on_started)
        self._worker.stopped_controller.connect(self._on_stopped)
        self._worker.error.connect(self._on_error)
        self._worker.e84_warning.connect(self._on_warning)
        self._worker.e84_fatal_error.connect(self._on_fatal)
        self._worker.e84_state_changed.connect(self._on_state_changed)

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
    log_dir = (Path(__file__).resolve().parent / "Log").resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    engine.rootContext().setContextProperty("fileRootPath", str(log_dir))

    chart_list_model = ChartDataListModel()

    chart_generators_instances = []
    for i in range(4):
        # 每秒追加一次点，只保留最近 60 秒的数据窗口
        series_model = SeriesTableModel(max_rows=60, parent=chart_list_model)
        generator = ChartDataGenerator(series_model)
        chart_list_model.addSeries(f"Chart {i + 1}", series_model)
        chart_generators_instances.append(generator)

        for _ in range(10):
            generator.generate_new_point()

    engine.rootContext().setContextProperty("chartListModel", chart_list_model)

    alarm_store = AlarmStore()
    alarm_store.addAlarm("2025-11-10 18:24:00", "Temperature above threshold")
    alarm_store.addAlarm("2025-11-10 18:25:30", "Pressure sensor offline")
    alarm_store.addAlarm("2025-11-10 18:25:31", "Pressure sensor offline.")
    alarm_store.addAlarm("2025-11-10 18:25:32", "Pressure sensor offline..")
    alarm_store.addAlarm("2025-11-10 18:25:33", "Pressure sensor offline...")
    engine.rootContext().setContextProperty("alarmStore", alarm_store)

    data_update_timer = QTimer()
    data_update_timer.setInterval(1000)
    data_update_timer.timeout.connect(
        lambda: [gen.generate_new_point() for gen in chart_generators_instances]
    )
    data_update_timer.start()

    qml_file = Path("./qml") / "main.qml"
    engine.load(qml_file)

    if not engine.rootObjects():
        sys.exit(-1)

    # 暴露出消息框属性
    root_obj = engine.rootObjects()[0]
    main_item = root_obj.findChild(QObject, "title_message")
    main_item.setProperty("systemMessage", "Hello World")

    # 启动后如存在 CSV 日志，预先解析一份，便于 DataLog/FileView 直接展示
    # if csv_file_manager.csvFiles:
    #     csv_file_manager.parse_csv_file(csv_file_manager.csvFiles[0])

    # 启动 loadport 后台线程，将错误/状态推送到 Alarm 与 TitlePanel
    bridge = LoadportBridge(alarm_store=alarm_store, title_panel=main_item)
    bridge.start()
    app.aboutToQuit.connect(bridge.shutdown)

    sys.exit(app.exec())
