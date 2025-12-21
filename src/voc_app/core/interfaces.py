"""核心抽象接口定义（抽象基类）。

说明：
该文件仅定义最小稳定接口，具体实现应放在其他模块中。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class HardwareController(ABC):
    """硬件控制器抽象基类。"""

    @abstractmethod
    def start(self) -> None:
        """启动硬件控制器。"""
        ...

    @abstractmethod
    def stop(self) -> None:
        """停止硬件控制器。"""
        ...

    @abstractmethod
    def is_running(self) -> bool:
        """返回当前控制器是否处于运行状态。"""
        ...


class DataSource(ABC):
    """数据源抽象基类。"""

    @abstractmethod
    def connect(self) -> None:
        """连接数据源。"""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """断开数据源连接。"""
        ...

    @abstractmethod
    def read_data(self) -> Any:
        """读取一份数据（数据结构由具体实现决定）。"""
        ...


class ConfigProvider(ABC):
    """配置提供者抽象基类。"""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值。"""
        ...

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """设置配置值。"""
        ...

    @abstractmethod
    def load(self) -> None:
        """从配置源加载配置。"""
        ...

    @abstractmethod
    def save(self) -> None:
        """保存配置到持久化介质。"""
        ...
