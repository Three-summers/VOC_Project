"""硬件控制器工厂。

设计目标：
1) 通过字符串类型创建硬件控制器，避免 GUI 层直接依赖具体实现
2) 支持注册自定义控制器（插件/扩展点）
3) 底层复用 core.registry.ComponentRegistry，保持一致的注册/校验语义
"""

from __future__ import annotations

from typing import Any, Optional, TypeVar

from voc_app.core.container import Container
from voc_app.core.interfaces import HardwareController
from voc_app.core.registry import ComponentRegistry

T = TypeVar("T", bound=HardwareController)


class HardwareControllerFactory:
    """硬件控制器工厂（type string -> 控制器类/实例）。"""

    def __init__(self, registry: Optional[ComponentRegistry] = None) -> None:
        self._registry = registry or ComponentRegistry()

    @property
    def registry(self) -> ComponentRegistry:
        return self._registry

    def register(
        self,
        kind: str,
        controller: type[T] | T,
        *,
        overwrite: bool = False,
        validate: bool = True,
    ) -> None:
        """注册硬件控制器。

        Args:
            kind: 控制器类型字符串（例如 \"loadport.e84\"）
            controller: 控制器类或实例
            overwrite: 是否允许覆盖
            validate: 是否进行 isinstance/issubclass 校验
        """

        self._registry.register(
            HardwareController,
            kind,
            controller,
            overwrite=overwrite,
            validate=validate,
        )

    def register_defaults(self, *, overwrite: bool = False) -> None:
        """注册项目内置的硬件控制器实现。"""

        from voc_app.hardware.loadport.e84_controller import E84Controller
        from voc_app.hardware.loadport.e84_thread import E84ControllerThread

        self.register("loadport.e84", E84Controller, overwrite=overwrite, validate=True)
        self.register("loadport.e84_thread", E84ControllerThread, overwrite=overwrite, validate=True)

    def create(
        self,
        kind: str,
        *,
        container: Optional[Container] = None,
        **kwargs: Any,
    ) -> HardwareController:
        """创建并返回指定类型的控制器实例。

        约定：
        - 若 registry 中注册的是“类”，优先通过 container 自动装配（仅当 kwargs 为空）；
          否则直接以 kwargs 构造。
        - 若 registry 中注册的是“实例”，直接返回该实例。
        """

        component = self._registry.require(HardwareController, kind)

        if isinstance(component, HardwareController):
            return component

        if isinstance(component, type):
            if container is not None and not kwargs:
                return container.resolve(component)
            return component(**kwargs)

        # 允许注册更灵活的工厂/可调用对象
        if callable(component):
            return component(**kwargs)

        raise TypeError(f"不支持的硬件控制器注册类型: kind={kind} type={type(component).__name__}")
