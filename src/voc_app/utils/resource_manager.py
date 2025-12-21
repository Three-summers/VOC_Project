"""资源管理工具（上下文管理器）。

目的：为 socket / 串口 / 文件等资源提供一致的生命周期管理，避免资源泄漏。
"""

from __future__ import annotations

import socket
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Generic, IO, Optional, TypeVar

from voc_app.logging_config import get_logger
from voc_app.utils.error_handler import ResourceError

logger = get_logger(__name__)

T = TypeVar("T")

try:  # 可选依赖：允许在测试环境中替换 serial_factory
    import serial  # type: ignore
except ImportError:  # pragma: no cover
    serial = None

SerialFactory = Callable[..., Any]


class BaseResourceManager(ABC, Generic[T]):
    """资源管理器基类（上下文管理器）。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._resource: Optional[T] = None

    def open(self) -> T:
        """打开资源并返回资源对象。"""
        with self._lock:
            if self._resource is not None:
                return self._resource
            try:
                self._resource = self._open()
            except Exception as exc:  # noqa: BLE001
                raise ResourceError("打开资源失败", context={"error": str(exc)}) from exc
            return self._resource

    def acquire(self) -> T:
        """兼容别名：acquire() == open()。"""
        return self.open()

    def close(self) -> None:
        """关闭资源（幂等）。"""
        with self._lock:
            if self._resource is None:
                return
            resource = self._resource
            self._resource = None
        try:
            self._close(resource)
        except Exception as exc:  # noqa: BLE001
            raise ResourceError("关闭资源失败", context={"error": str(exc)}) from exc

    def release(self) -> None:
        """兼容别名：release() == close()。"""
        self.close()

    def __enter__(self) -> T:
        return self.open()

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.close()
        return False

    @abstractmethod
    def _open(self) -> T:
        """打开资源的具体实现。"""

    @abstractmethod
    def _close(self, resource: T) -> None:
        """关闭资源的具体实现。"""


class SocketResourceManager(BaseResourceManager[socket.socket]):
    """Socket 资源管理器（TCP 客户端）。"""

    def __init__(
        self,
        host: str,
        port: int,
        *,
        timeout: Optional[float] = 5.0,
        family: int = socket.AF_INET,
        sock_type: int = socket.SOCK_STREAM,
    ) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._timeout = timeout
        self._family = family
        self._sock_type = sock_type

    def _open(self) -> socket.socket:
        sock = socket.socket(self._family, self._sock_type)
        if self._timeout is not None:
            sock.settimeout(self._timeout)
        sock.connect((self._host, self._port))
        return sock

    def _close(self, resource: socket.socket) -> None:
        try:
            resource.shutdown(socket.SHUT_RDWR)
        except OSError:
            # 可能已关闭或未连接
            pass
        resource.close()


class SerialResourceManager(BaseResourceManager[Any]):
    """串口资源管理器（pyserial.Serial）。"""

    def __init__(
        self,
        port: str,
        *,
        baudrate: int = 115200,
        timeout: float = 1.0,
        serial_factory: Optional[SerialFactory] = None,
    ) -> None:
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial_factory = serial_factory or self._default_serial_factory

    def _default_serial_factory(self, **kwargs: Any) -> Any:
        if serial is None:
            raise ResourceError("pyserial 未安装，无法创建串口资源")
        return serial.Serial(**kwargs)

    def _open(self) -> Any:
        return self._serial_factory(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )

    def _close(self, resource: Any) -> None:
        try:
            is_open = getattr(resource, "is_open", True)
            if is_open:
                resource.close()
        except Exception as exc:  # noqa: BLE001
            logger.error(f"关闭串口失败: {exc}", exc_info=True)
            raise


class FileResourceManager(BaseResourceManager[IO[Any]]):
    """文件资源管理器。"""

    def __init__(
        self,
        path: str | Path,
        *,
        mode: str = "r",
        encoding: Optional[str] = "utf-8",
    ) -> None:
        super().__init__()
        self._path = Path(path)
        self._mode = mode
        self._encoding = None if "b" in mode else encoding

    def _open(self) -> IO[Any]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        return open(self._path, mode=self._mode, encoding=self._encoding)  # noqa: PTH123

    def _close(self, resource: IO[Any]) -> None:
        resource.close()
