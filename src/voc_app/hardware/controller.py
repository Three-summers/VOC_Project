"""硬件控制器抽象层。

该文件在 core.interfaces.HardwareController 的基础上补充常用硬件能力：
- get_status(): 读取硬件状态（用于 GUI/日志/诊断）
- reset(): 将硬件恢复到可预期的初始状态

注意：
- 不强制依赖 PySide6；硬件层应可在纯 Python 环境导入与测试。
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod

from voc_app.core.interfaces import HardwareController


try:  # pragma: no cover - PySide6 在部分验证环境可能不存在
    from PySide6.QtCore import QObject

    class QObjectABCMeta(type(QObject), ABCMeta):
        """合并 QObject 与 ABC 的元类，避免多继承 metaclass 冲突。"""

except ModuleNotFoundError:  # pragma: no cover

    class QObjectABCMeta(ABCMeta):
        """无 PySide6 环境下的兼容元类。"""


class AbstractHardwareController(HardwareController, metaclass=ABCMeta):
    """硬件控制器基类，扩展核心接口。"""

    @abstractmethod
    def get_status(self) -> dict:
        """获取硬件状态。"""

    @abstractmethod
    def reset(self) -> None:
        """重置硬件。"""

