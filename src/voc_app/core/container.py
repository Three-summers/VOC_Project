"""依赖注入容器（构造函数注入 + 自动装配）。"""

from __future__ import annotations

import inspect
import threading
from dataclasses import dataclass
from enum import Enum
import types
import typing
from typing import Any, Callable, Optional, TypeVar, get_args, get_origin, get_type_hints

from voc_app.logging_config import get_logger
from voc_app.utils import DependencyResolutionError

logger = get_logger(__name__)

T = TypeVar("T")


class Lifecycle(str, Enum):
    """组件生命周期。"""

    SINGLETON = "singleton"
    TRANSIENT = "transient"


_UNSET = object()


@dataclass
class _Provider:
    factory: Callable[["Container", list[type[Any]]], Any]
    lifecycle: Lifecycle
    instance: Any = _UNSET


class Container:
    """轻量依赖注入容器。

特性：
1) 构造函数注入：根据 __init__ 参数类型注解解析依赖
2) 生命周期：单例 / 瞬态
3) 自动装配：未显式注册的具体类也可按注解递归构造
"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._providers: dict[type[Any], _Provider] = {}

    # ------------------------------------------------------------------
    # 注册 API
    # ------------------------------------------------------------------
    def register_instance(self, abstract: type[T], instance: T) -> None:
        """注册单例实例。"""

        def factory(_: "Container", __: list[type[Any]]) -> T:
            return instance

        with self._lock:
            self._providers[abstract] = _Provider(factory=factory, lifecycle=Lifecycle.SINGLETON)

    def register_factory(
        self,
        abstract: type[T],
        factory: Callable[..., T],
        *,
        lifecycle: Lifecycle = Lifecycle.TRANSIENT,
    ) -> None:
        """注册工厂函数。"""

        def provider(container: "Container", stack: list[type[Any]]) -> T:
            return container._call_with_injection(factory, stack=stack)

        with self._lock:
            self._providers[abstract] = _Provider(factory=provider, lifecycle=lifecycle)

    def register_class(
        self,
        abstract: type[T],
        implementation: type[T],
        *,
        lifecycle: Lifecycle = Lifecycle.TRANSIENT,
    ) -> None:
        """注册实现类（支持自动装配其构造依赖）。"""

        def provider(container: "Container", stack: list[type[Any]]) -> T:
            return container._construct(implementation, stack=stack)

        with self._lock:
            self._providers[abstract] = _Provider(factory=provider, lifecycle=lifecycle)

    # ------------------------------------------------------------------
    # 解析 API
    # ------------------------------------------------------------------
    def resolve(self, abstract: type[T]) -> T:
        """解析并返回指定类型实例。"""
        return self._resolve(abstract, stack=[])

    def try_resolve(self, abstract: type[T]) -> Optional[T]:
        """尝试解析；失败返回 None。"""
        try:
            return self.resolve(abstract)
        except DependencyResolutionError:
            return None

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _resolve(self, abstract: Any, stack: list[type[Any]]) -> Any:
        abstract = self._unwrap_annotation(abstract)

        if abstract is Container:
            return self

        if not isinstance(abstract, type):
            raise DependencyResolutionError(
                "无法解析非类型依赖",
                context={"dependency": str(abstract)},
            )

        if abstract in stack:
            chain = " -> ".join([c.__name__ for c in stack] + [abstract.__name__])
            raise DependencyResolutionError("检测到循环依赖", context={"chain": chain})

        stack.append(abstract)
        try:
            provider = self._providers.get(abstract)
            if provider is not None:
                return self._get_from_provider(provider, stack)

            # 未注册：尝试自动装配具体类
            if inspect.isclass(abstract) and not inspect.isabstract(abstract):
                return self._construct(abstract, stack)

            raise DependencyResolutionError(
                "未注册依赖且无法自动装配",
                context={"dependency": abstract.__name__},
            )
        finally:
            stack.pop()

    def _get_from_provider(self, provider: _Provider, stack: list[type[Any]]) -> Any:
        if provider.lifecycle == Lifecycle.SINGLETON and provider.instance is not _UNSET:
            return provider.instance

        instance = provider.factory(self, stack)

        if provider.lifecycle == Lifecycle.SINGLETON:
            provider.instance = instance
        return instance

    def _construct(self, cls: type[Any], stack: list[type[Any]]) -> Any:
        ctor = cls.__init__
        signature = inspect.signature(ctor)
        try:
            type_hints = get_type_hints(ctor, include_extras=True)
        except Exception:  # noqa: BLE001
            type_hints = {}

        kwargs: dict[str, Any] = {}
        for name, param in signature.parameters.items():
            if name == "self":
                continue
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue

            annotation = type_hints.get(name, param.annotation)
            if annotation is inspect._empty:
                if param.default is not inspect._empty:
                    continue
                raise DependencyResolutionError(
                    "构造函数参数缺少类型注解",
                    context={"class": cls.__name__, "param": name},
                )

            resolved = self._resolve_param(annotation, param, stack)
            if resolved is _UNSET:
                continue
            kwargs[name] = resolved

        try:
            return cls(**kwargs)
        except TypeError as exc:
            raise DependencyResolutionError(
                "构造实例失败",
                context={"class": cls.__name__, "error": str(exc), "kwargs": list(kwargs.keys())},
            ) from exc

    def _resolve_param(self, annotation: Any, param: inspect.Parameter, stack: list[type[Any]]) -> Any:
        annotation = self._unwrap_annotation(annotation)
        origin = get_origin(annotation)

        # Optional[T] / Union[T, None]
        if origin in (typing.Union, types.UnionType):
            raw_args = get_args(annotation)
            non_none_args = [a for a in raw_args if a is not type(None)]
            if len(non_none_args) == 1 and len(raw_args) != len(non_none_args):
                try:
                    return self._resolve(non_none_args[0], stack)
                except DependencyResolutionError:
                    if param.default is not inspect._empty:
                        return _UNSET
                    raise

        if not isinstance(annotation, type):
            if param.default is not inspect._empty:
                return _UNSET
            raise DependencyResolutionError(
                "无法解析构造函数参数类型",
                context={"param": param.name, "annotation": str(annotation)},
            )

        return self._resolve(annotation, stack)

    @staticmethod
    def _unwrap_annotation(annotation: Any) -> Any:
        """解包 Annotated[T, ...] 等常见包装。"""
        origin = get_origin(annotation)
        if origin is typing.Annotated:
            args = get_args(annotation)
            if args:
                return args[0]
        return annotation

    def _call_with_injection(self, fn: Callable[..., Any], stack: list[type[Any]]) -> Any:
        signature = inspect.signature(fn)
        try:
            type_hints = get_type_hints(fn, include_extras=True)
        except Exception:  # noqa: BLE001
            type_hints = {}

        kwargs: dict[str, Any] = {}
        for name, param in signature.parameters.items():
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            annotation = type_hints.get(name, param.annotation)
            if annotation is inspect._empty:
                if param.default is not inspect._empty:
                    continue
                raise DependencyResolutionError(
                    "工厂函数参数缺少类型注解",
                    context={"fn": getattr(fn, "__name__", str(fn)), "param": name},
                )
            kwargs[name] = self._resolve(self._unwrap_annotation(annotation), stack)

        try:
            return fn(**kwargs)
        except TypeError as exc:
            raise DependencyResolutionError(
                "调用工厂函数失败",
                context={"fn": getattr(fn, "__name__", str(fn)), "error": str(exc)},
            ) from exc
