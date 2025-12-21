"""E84 控制器线程封装。

说明：
- 该模块提供与历史 `voc_app.loadport.e84_thread.E84ControllerThread` 类似的 API：start/stop + 多路事件信号。
- 为了让硬件层与 GUI 解耦，本实现不强依赖 PySide6/QThread；底层由 E84Controller 自身的循环线程驱动。
- GUI 可通过 LoadportBridge 订阅本类的信号，以保持 QML 层无需修改。
"""

from __future__ import annotations

from typing import Any, Optional

from voc_app.core.interfaces import HardwareController
from voc_app.logging_config import get_logger
from voc_app.utils import UnexpectedError

from .e84_controller import E84Controller, Signal

logger = get_logger(__name__)


class E84ControllerThread(HardwareController):
    """E84 控制器线程封装（兼容旧 API）。"""

    def __init__(self, **controller_kwargs: Any) -> None:
        self._controller_kwargs = dict(controller_kwargs)
        self._controller: Optional[E84Controller] = None

        self.started_controller: Signal = Signal()
        self.stopped_controller: Signal = Signal()
        self.error: Signal = Signal()
        self.controller_ready: Signal = Signal()
        self.e84_state_changed: Signal = Signal()
        self.e84_warning: Signal = Signal()
        self.e84_fatal_error: Signal = Signal()
        self.system_event: Signal = Signal()
        self.all_keys_set: Signal = Signal()

    # ------------------------------------------------------------------
    # HardwareController 接口
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._controller and self._controller.is_running():
            return

        try:
            controller = E84Controller(**self._controller_kwargs)
            self._controller = controller
            self._connect_controller_signals(controller)
            controller.start()
            self.controller_ready.emit(controller)
            self.started_controller.emit()
        except Exception as exc:  # noqa: BLE001
            err = UnexpectedError("E84 控制器启动失败", context={"error": str(exc)})
            logger.error(str(err), exc_info=True)
            self.error.emit(str(err))

    def stop(self) -> None:
        controller = self._controller
        if controller is not None:
            try:
                controller.stop()
            except Exception as exc:  # noqa: BLE001
                err = UnexpectedError("E84 控制器停止失败", context={"error": str(exc)})
                logger.error(str(err), exc_info=True)
                self.error.emit(str(err))
            finally:
                self._disconnect_controller_signals(controller)
                self._controller = None

        self.stopped_controller.emit()

    def is_running(self) -> bool:
        return bool(self._controller and self._controller.is_running())

    # ------------------------------------------------------------------
    # 事件转发
    # ------------------------------------------------------------------
    def _relay_controller_state(self, state: str) -> None:
        self.e84_state_changed.emit(state)
        self.system_event.emit("e84_state", state)

    def _relay_controller_warning(self, message: str) -> None:
        self.e84_warning.emit(message)
        self.system_event.emit("e84_warning", message)

    def _relay_controller_fatal(self, message: str) -> None:
        self.e84_fatal_error.emit(message)
        self.system_event.emit("e84_fatal_error", message)

    def _relay_all_keys_set(self) -> None:
        self.all_keys_set.emit()
        self.system_event.emit("e84_all_keys_set", "true")

    def _connect_controller_signals(self, controller: E84Controller) -> None:
        controller.state_changed.connect(self._relay_controller_state)
        controller.warning.connect(self._relay_controller_warning)
        controller.fatal_error.connect(self._relay_controller_fatal)
        controller.all_keys_set.connect(self._relay_all_keys_set)

    def _disconnect_controller_signals(self, controller: E84Controller) -> None:
        try:
            controller.state_changed.disconnect(self._relay_controller_state)
            controller.warning.disconnect(self._relay_controller_warning)
            controller.fatal_error.disconnect(self._relay_controller_fatal)
            controller.all_keys_set.disconnect(self._relay_all_keys_set)
        except Exception:  # noqa: BLE001
            # 兼容 Signal.disconnect 的容错行为
            pass

