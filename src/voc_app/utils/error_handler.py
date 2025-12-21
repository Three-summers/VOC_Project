"""统一错误处理与异常体系。

设计目标：
1) 提供应用级异常类层次结构，便于上层统一捕获与展示
2) 提供统一错误处理装饰器，减少重复 try/except
3) 集成日志记录，确保异常可追踪
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional, ParamSpec, TypeVar

from voc_app.logging_config import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class VOCError(Exception):
    """VOC 应用基础异常类。

    说明：
    - 建议业务代码优先抛出 VOCError 及其子类，便于统一处理
    - 允许携带上下文信息（context）用于定位问题
    """

    message: str
    context: Optional[dict[str, Any]] = None

    def __str__(self) -> str:  # pragma: no cover - dataclass 默认不友好
        if not self.context:
            return self.message
        return f"{self.message} | context={self.context}"


class UnexpectedError(VOCError):
    """未预期异常（用于包装非 VOCError 的异常）。"""


class ConfigError(VOCError):
    """配置相关异常。"""


class RegistryError(VOCError):
    """组件注册表相关异常。"""


class DependencyResolutionError(VOCError):
    """依赖注入容器解析失败异常。"""


class ResourceError(VOCError):
    """资源管理相关异常（socket/串口/文件等）。"""


def handle_errors(
    *,
    logger_instance=None,
    reraise: bool = True,
    default: Any = None,
    wrap_unexpected: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """统一错误处理装饰器。

    Args:
        logger_instance: 指定日志器；为空时使用模块默认日志器
        reraise: 是否在记录日志后继续抛出异常；False 则返回 default
        default: reraise=False 时的返回值
        wrap_unexpected: 是否将非 VOCError 的异常包装成 UnexpectedError

    Returns:
        装饰器函数
    """

    active_logger = logger_instance or logger

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:  # type: ignore[override]
            try:
                return fn(*args, **kwargs)
            except VOCError as exc:
                active_logger.error(f"捕获应用异常: {exc}", exc_info=True)
                if reraise:
                    raise
                return default  # type: ignore[return-value]
            except Exception as exc:  # noqa: BLE001
                active_logger.error(f"捕获未预期异常: {exc}", exc_info=True)
                if reraise:
                    if wrap_unexpected:
                        raise UnexpectedError("发生未预期异常", context={"fn": fn.__name__}) from exc
                    raise
                return default  # type: ignore[return-value]

        return wrapper

    return decorator

