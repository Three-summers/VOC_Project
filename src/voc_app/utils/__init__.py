"""VOC 应用工具模块。

该包提供跨模块通用的基础设施能力，例如：
- 统一异常体系与错误处理装饰器
- 资源（socket/串口/文件）生命周期管理
"""

from __future__ import annotations

from .error_handler import (
    ConfigError,
    DependencyResolutionError,
    RegistryError,
    ResourceError,
    UnexpectedError,
    VOCError,
    handle_errors,
)
from .resource_manager import (
    BaseResourceManager,
    FileResourceManager,
    SerialResourceManager,
    SocketResourceManager,
)

__all__ = [
    "VOCError",
    "UnexpectedError",
    "ConfigError",
    "RegistryError",
    "DependencyResolutionError",
    "ResourceError",
    "handle_errors",
    "BaseResourceManager",
    "SocketResourceManager",
    "SerialResourceManager",
    "FileResourceManager",
]
