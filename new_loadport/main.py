import signal
import sys
from PySide6.QtCore import QObject, QCoreApplication

from e84_thread import E84ControllerThread


class ConsoleBridge(QObject):
    """简单的信号桥，演示如何接收线程事件"""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

    def on_state_changed(self, state: str) -> None:
        print(f"[主线程] 状态更新: {state}")

    def on_warning(self, message: str) -> None:
        print(f"[主线程] 警告: {message}")

    def on_error(self, message: str) -> None:
        print(f"[主线程] 线程错误: {message}")


def main():
    """PySide6 事件循环入口，演示线程化控制器"""

    app = QCoreApplication(sys.argv)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    console = ConsoleBridge()
    worker = E84ControllerThread()

    worker.started_controller.connect(lambda: print("[主线程] E84 线程已启动"))
    worker.stopped_controller.connect(lambda: print("[主线程] E84 线程已停止"))
    worker.error.connect(console.on_error)
    worker.e84_state_changed.connect(console.on_state_changed)
    worker.e84_warning.connect(console.on_warning)

    def on_controller_ready(controller):
        controller.state_changed.connect(console.on_state_changed)
        controller.warning.connect(console.on_warning)

    worker.controller_ready.connect(on_controller_ready)

    worker.start()
    app.aboutToQuit.connect(worker.stop)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
