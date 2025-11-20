from PySide6.QtCore import QObject, QThread, Signal, Slot, QMetaObject, Qt

from voc_app.loadport.E84Passive import E84Controller


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
            self.controller = E84Controller(**self._controller_kwargs)
            self.controller.start()
            self.started.emit(self.controller)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))

    @Slot()
    def stop_controller(self) -> None:
        if self.controller:
            self.controller.stop()
            self.controller.deleteLater()
            self.controller = None
        self.stopped.emit()


class E84ControllerThread(QObject):
    """官方推荐写法：QObject + QThread 组合"""

    started_controller = Signal()
    stopped_controller = Signal()
    error = Signal(str)
    controller_ready = Signal(E84Controller)
    e84_state_changed = Signal(str)
    e84_warning = Signal(str)
    e84_fatal_error = Signal(str)
    system_event = Signal(str, str)

    def __init__(self, parent: QObject | None = None, **controller_kwargs):
        super().__init__(parent)
        self._thread = QThread(self)
        self._worker = _E84Worker(**controller_kwargs)
        self._controller: E84Controller | None = None
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.start_controller)
        self._worker.started.connect(self._on_worker_started)
        self._worker.stopped.connect(self._on_worker_stopped)
        self._worker.error.connect(self._handle_worker_error)

    @Slot()
    def start(self) -> None:
        if not self._thread.isRunning():
            self._thread.start()

    @Slot()
    def stop(self) -> None:
        if self._thread.isRunning():
            QMetaObject.invokeMethod(
                self._worker,
                "stop_controller",
                Qt.ConnectionType.QueuedConnection,
            )
            self._thread.quit()
            self._thread.wait()

    def _on_worker_started(self, controller: E84Controller) -> None:
        self._controller = controller
        self._connect_controller_signals(controller)
        self.controller_ready.emit(controller)
        self.started_controller.emit()

    def _on_worker_stopped(self) -> None:
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

    @Slot(str)
    def _handle_worker_error(self, message: str) -> None:
        self.error.emit(message)
        self.system_event.emit("thread_error", message)

    def _connect_controller_signals(self, controller: E84Controller) -> None:
        controller.state_changed.connect(self._relay_controller_state)
        controller.warning.connect(self._relay_controller_warning)
        controller.fatal_error.connect(self._relay_controller_fatal)

    def _disconnect_controller_signals(self) -> None:
        if not self._controller:
            return
        try:
            self._controller.state_changed.disconnect(self._relay_controller_state)
            self._controller.warning.disconnect(self._relay_controller_warning)
            self._controller.fatal_error.disconnect(self._relay_controller_fatal)
        except TypeError:
            pass
        self._controller = None
