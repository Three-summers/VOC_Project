import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import (
    QObject,
    QTimer,
    Slot,
)
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 当最后一个窗口被关闭时，不要自动退出应用程序，以在 qml 动态调用 quit 退出
    app.setQuitOnLastWindowClosed(False)
    engine = QQmlApplicationEngine()

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

    sys.exit(app.exec())
