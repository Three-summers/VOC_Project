"""线程安全组件注册表。

注册表用于按“组件类型 + 名称”管理组件，便于后续插件化与依赖注入装配。
"""

from __future__ import annotations

import threading
from typing import Any, Dict, TypeVar

from voc_app.logging_config import get_logger
from voc_app.utils import RegistryError

logger = get_logger(__name__)

T = TypeVar("T")


class ComponentRegistry:
    """线程安全组件注册表。

设计要点：
1) 以 (category, name) 作为唯一键
2) category 通常为抽象基类（如 HardwareController, DataSource）
3) 支持可选的类型校验（validate=True）
4) 所有读写操作线程安全
"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._store: dict[type[Any], dict[str, Any]] = {}

    def register(
        self,
        category: type[T],
        name: str,
        component: Any,
        *,
        overwrite: bool = False,
        validate: bool = True,
    ) -> None:
        """注册组件。

        Args:
            category: 组件分类（通常为接口/抽象类）
            name: 组件名称
            component: 组件对象/类/工厂（注册表本身不约束其形态）
            overwrite: 是否允许覆盖同名组件
            validate: 是否进行 isinstance/issubclass 校验（尽力校验）
        """

        if not name:
            raise RegistryError("组件名称不能为空", context={"category": str(category)})

        with self._lock:
            bucket = self._store.setdefault(category, {})
            if (not overwrite) and name in bucket:
                raise RegistryError(
                    "组件已存在，禁止覆盖",
                    context={"category": getattr(category, "__name__", str(category)), "name": name},
                )

            if validate:
                self._validate_registration(category, name, component)

            bucket[name] = component
            logger.debug(
                "注册组件: category=%s name=%s component=%s",
                getattr(category, "__name__", str(category)),
                name,
                getattr(component, "__name__", type(component).__name__),
            )

    def get(self, category: type[T], name: str, default: Any = None) -> Any:
        """获取组件；不存在时返回 default。"""
        with self._lock:
            return self._store.get(category, {}).get(name, default)

    def require(self, category: type[T], name: str) -> Any:
        """获取组件；不存在则抛出异常。"""
        with self._lock:
            bucket = self._store.get(category, {})
            if name not in bucket:
                raise RegistryError(
                    "未找到组件",
                    context={"category": getattr(category, "__name__", str(category)), "name": name},
                )
            return bucket[name]

    def unregister(self, category: type[T], name: str) -> None:
        """取消注册组件；不存在则忽略。"""
        with self._lock:
            bucket = self._store.get(category)
            if not bucket:
                return
            bucket.pop(name, None)
            if not bucket:
                self._store.pop(category, None)

    def list_names(self, category: type[T]) -> list[str]:
        """列出指定分类下已注册的名称列表。"""
        with self._lock:
            return sorted(self._store.get(category, {}).keys())

    def categories(self) -> list[type[Any]]:
        """列出当前注册表中的分类列表。"""
        with self._lock:
            return list(self._store.keys())

    def items(self, category: type[T]) -> Dict[str, Any]:
        """返回指定分类下的浅拷贝字典（name -> component）。"""
        with self._lock:
            return dict(self._store.get(category, {}))

    def clear(self) -> None:
        """清空注册表。"""
        with self._lock:
            self._store.clear()

    @staticmethod
    def _validate_registration(category: type[T], name: str, component: Any) -> None:
        """尽力进行类型校验（不引入额外依赖）。"""
        try:
            if isinstance(component, type):
                if not issubclass(component, category):
                    raise RegistryError(
                        "注册组件类型不匹配",
                        context={
                            "category": getattr(category, "__name__", str(category)),
                            "name": name,
                            "component": getattr(component, "__name__", str(component)),
                        },
                    )
                return

            if not isinstance(component, category):
                raise RegistryError(
                    "注册组件实例类型不匹配",
                    context={
                        "category": getattr(category, "__name__", str(category)),
                        "name": name,
                        "component": type(component).__name__,
                    },
                )
        except TypeError:
            # category 可能是 Protocol/typing 对象，isinstance/issubclass 不可用
            return
