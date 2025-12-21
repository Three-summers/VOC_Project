"""VOC 核心抽象层。

该包用于承载与具体实现无关的核心能力：
- 抽象接口（硬件控制器、数据源、配置提供者）
- 线程安全组件注册表
- 统一配置管理（多源合并、覆盖、变更通知）
- 依赖注入容器（构造函数注入、单例/瞬态、自动装配）
"""

from __future__ import annotations

from .config import AppConfig, ConfigChangeEvent
from .container import Container, Lifecycle
from .interfaces import ConfigProvider, DataSource, HardwareController
from .registry import ComponentRegistry

__all__ = [
    "HardwareController",
    "DataSource",
    "ConfigProvider",
    "ComponentRegistry",
    "AppConfig",
    "ConfigChangeEvent",
    "Lifecycle",
    "Container",
]

