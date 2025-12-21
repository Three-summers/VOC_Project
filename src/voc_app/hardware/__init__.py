"""VOC 硬件抽象层。

说明：
该包负责承载“与 GUI 解耦”的硬件控制逻辑与实现：
- 抽象接口扩展（AbstractHardwareController）
- 控制器工厂（HardwareControllerFactory）
- 具体硬件实现（如 loadport/E84）
"""

from __future__ import annotations

from .controller import AbstractHardwareController
from .factory import HardwareControllerFactory

__all__ = [
    "AbstractHardwareController",
    "HardwareControllerFactory",
]

