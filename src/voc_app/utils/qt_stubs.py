"""Qt 兼容桩（PySide6 缺失时的最小替代）。

用途：
- 在开发/验证环境缺少 PySide6 时，仍可导入依赖 QtCore 的模块以运行单元测试
- 提供 Signal/Property/QTimer 的最小行为子集，避免引入真实 Qt 事件循环

注意：
- 该模块仅作为“缺少 PySide6 的兜底”，生产环境应安装 PySide6
"""

from __future__ import annotations


class QObject:  # pragma: no cover - 仅用于无 PySide6 环境兜底
    def __init__(self, parent: object | None = None) -> None:
        self._parent = parent

    def deleteLater(self) -> None:
        return None


class _BoundSignal:  # pragma: no cover - 仅用于无 PySide6 环境兜底
    def __init__(self) -> None:
        self._slots: list[object] = []

    def connect(self, slot) -> None:  # noqa: ANN001
        self._slots.append(slot)

    def disconnect(self, slot=None) -> None:  # noqa: ANN001
        if slot is None:
            self._slots.clear()
            return
        try:
            self._slots.remove(slot)
        except ValueError:
            return

    def emit(self, *args, **kwargs) -> None:  # noqa: ANN001
        for slot in list(self._slots):
            try:
                slot(*args, **kwargs)
            except Exception:
                # 测试环境的简化信号机制：保持与 Qt 类似的“发射不崩溃”语义
                continue


class Signal:  # pragma: no cover - 仅用于无 PySide6 环境兜底
    """描述符：为每个 QObject 实例提供独立的信号对象。"""

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        self._name = ""

    def __set_name__(self, owner, name: str) -> None:  # noqa: ANN001
        self._name = name

    def __get__(self, instance, owner):  # noqa: ANN001
        if instance is None:
            return self
        registry = instance.__dict__.setdefault("_qt_signals", {})
        if self._name not in registry:
            registry[self._name] = _BoundSignal()
        return registry[self._name]


def Slot(*args, **kwargs):  # noqa: ANN001
    def decorator(func):
        return func

    return decorator


class Property:  # pragma: no cover - 仅用于无 PySide6 环境兜底
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        return None

    def __call__(self, fget):  # noqa: ANN001
        return property(fget)


class QTimer:  # pragma: no cover - 仅用于无 PySide6 环境兜底
    def __init__(self, parent: object | None = None) -> None:
        self._parent = parent
        self._active = False
        self._interval_ms = 0
        self._single_shot = False
        self.timeout = _BoundSignal()

    @staticmethod
    def singleShot(msec: int, callback) -> None:  # noqa: ANN001, ARG002
        # 测试环境无需真实计时，直接执行回调即可覆盖流程
        callback()

    def setSingleShot(self, single_shot: bool) -> None:
        self._single_shot = bool(single_shot)

    def setInterval(self, interval_ms: int) -> None:
        self._interval_ms = int(interval_ms)

    def start(self, interval_ms: int | None = None) -> None:
        if interval_ms is not None:
            self._interval_ms = int(interval_ms)
        self._active = True

    def stop(self) -> None:
        self._active = False

    def isActive(self) -> bool:
        return bool(self._active)

