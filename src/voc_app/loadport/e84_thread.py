from PySide6.QtCore import QObject, QThread, Signal, Slot, QMetaObject, Qt

from voc_app.loadport.e84_passive import E84Controller
from voc_app.logging_config import get_logger

logger = get_logger(__name__)


class _E84Worker(QObject):
    """在独立线程中创建并驱动 E84 控制器"""

    started = Signal(E84Controller)
    stopped = Signal()
    error = Signal(str)

    def __init__(self, **controller_kwargs):
        super().__init__()
        self._controller_kwargs = controller_kwargs
        self.controller: E84Controller | None = None

    @Slot()
    def start_controller(self) -> None:
        try:
            logger.info("E84 Worker: 正在启动控制器...")
            self.controller = E84Controller(**self._controller_kwargs)
            self.controller.start()
            logger.info("E84 Worker: 控制器启动成功")
            self.started.emit(self.controller)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"E84 Worker: 控制器启动失败 - {exc}")
            self.error.emit(str(exc))

    @Slot()
    def stop_controller(self) -> None:
        # 先摘掉引用，保证本方法重复执行也安全（R17）
        controller = self.controller
        self.controller = None
        if controller is not None:
            logger.info("E84 Worker: 正在停止控制器...")
            try:
                controller.stop()
            except Exception as exc:  # noqa: BLE001
                logger.error(f"E84 Worker: 停止控制器失败 - {exc}")
            finally:
                # 在工作线程内安排销毁，避免主线程跨线程析构定时器
                controller.deleteLater()
            logger.info("E84 Worker: 控制器已停止")
        self.stopped.emit()


class E84ControllerThread(QObject):
    """官方推荐写法：QObject + QThread 组合"""

    # 停止时等待 worker 清理完成的上限；超时才强制终止，避免界面卡死
    STOP_WAIT_MS = 5000

    started_controller = Signal()
    stopped_controller = Signal()
    error = Signal(str)
    controller_ready = Signal(E84Controller)
    e84_state_changed = Signal(str)
    e84_warning = Signal(str)
    e84_fatal_error = Signal(str)
    system_event = Signal(str, str)
    all_keys_set = Signal()

    def __init__(self, parent: QObject | None = None, **controller_kwargs):
        super().__init__(parent)
        self._thread = QThread(self)
        self._worker = _E84Worker(**controller_kwargs)
        self._controller: E84Controller | None = None
        self._stopped_notified = False
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.start_controller)
        self._worker.started.connect(self._on_worker_started)
        self._worker.stopped.connect(self._on_worker_stopped)
        # 清理完成后由 worker 线程自己退出事件循环：DirectConnection 保证
        # quit() 在 worker 线程执行，主线程只需要有界 wait()（R17）。
        self._worker.stopped.connect(
            self._thread.quit, Qt.ConnectionType.DirectConnection
        )
        self._worker.error.connect(self._handle_worker_error)

    @Slot()
    def start(self) -> None:
        if not self._thread.isRunning():
            self._stopped_notified = False
            self._thread.start()

    @Slot()
    def stop(self) -> None:
        if self._thread.isRunning():
            # 排队执行清理，然后有界等待线程真正退出，避免 quit() 抢在
            # 排队的 stop_controller 之前（R17）。
            QMetaObject.invokeMethod(
                self._worker,
                "stop_controller",  # type: ignore
                Qt.ConnectionType.QueuedConnection,
            )
            if not self._thread.wait(self.STOP_WAIT_MS):
                logger.error(
                    f"E84 线程未在 {self.STOP_WAIT_MS} ms 内完成清理，强制终止"
                )
                self._thread.terminate()
                self._thread.wait(1000)
        self._on_worker_stopped()

    def _on_worker_started(self, controller: E84Controller) -> None:
        self._controller = controller
        self._connect_controller_signals(controller)
        self.controller_ready.emit(controller)
        self.started_controller.emit()

    def _on_worker_stopped(self) -> None:
        # 可能被 worker 信号与 stop() 各触发一次，必须幂等（R17）
        if self._stopped_notified:
            return
        self._stopped_notified = True
        self._disconnect_controller_signals()
        self.stopped_controller.emit()

    @Slot(str)
    def _relay_controller_state(self, state: str) -> None:
        self.e84_state_changed.emit(state)
        self.system_event.emit("e84_state", state)

    @Slot(str)
    def _relay_controller_warning(self, message: str) -> None:
        self.e84_warning.emit(message)
        self.system_event.emit("e84_warning", message)

    @Slot(str)
    def _relay_controller_fatal(self, message: str) -> None:
        self.e84_fatal_error.emit(message)
        self.system_event.emit("e84_fatal_error", message)

    @Slot()
    def _relay_all_keys_set(self) -> None:
        self.all_keys_set.emit()
        self.system_event.emit("e84_all_keys_set", "true")

    @Slot(str)
    def _handle_worker_error(self, message: str) -> None:
        self.error.emit(message)
        self.system_event.emit("thread_error", message)

    def _connect_controller_signals(self, controller: E84Controller) -> None:
        controller.state_changed.connect(self._relay_controller_state)
        controller.warning.connect(self._relay_controller_warning)
        controller.fatal_error.connect(self._relay_controller_fatal)
        controller.all_keys_set.connect(self._relay_all_keys_set)

    def _disconnect_controller_signals(self) -> None:
        if not self._controller:
            return
        try:
            self._controller.state_changed.disconnect(self._relay_controller_state)
            self._controller.warning.disconnect(self._relay_controller_warning)
            self._controller.fatal_error.disconnect(self._relay_controller_fatal)
            self._controller.all_keys_set.disconnect(self._relay_all_keys_set)
        except (TypeError, RuntimeError):
            # TypeError：信号未连接；RuntimeError：C++ 对象已随工作线程销毁
            pass
        self._controller = None
