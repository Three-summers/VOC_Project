"""测试 utils 工具模块。"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import voc_app.utils.resource_manager as resource_manager_module
from voc_app.utils import (
    FileResourceManager,
    ResourceError,
    SerialResourceManager,
    SocketResourceManager,
    UnexpectedError,
    VOCError,
    handle_errors,
)


class TestErrorHandler(unittest.TestCase):
    """测试统一错误处理与异常体系。"""

    def test_voc_error_str(self) -> None:
        err = VOCError("消息", context={"a": 1})
        self.assertIn("消息", str(err))
        self.assertIn("context", str(err))

    def test_handle_errors_reraise(self) -> None:
        @handle_errors()
        def fn() -> None:
            raise VOCError("测试异常")

        with self.assertRaises(VOCError):
            fn()

    def test_handle_errors_default_return(self) -> None:
        @handle_errors(reraise=False, default=123)
        def fn() -> int:
            raise VOCError("测试异常")

        self.assertEqual(fn(), 123)

    def test_handle_errors_wrap_unexpected(self) -> None:
        @handle_errors()
        def fn() -> None:
            raise ValueError("boom")

        with self.assertRaises(UnexpectedError):
            fn()

    def test_handle_errors_no_wrap_unexpected(self) -> None:
        @handle_errors(wrap_unexpected=False)
        def fn() -> None:
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            fn()


class TestResourceManager(unittest.TestCase):
    """测试资源管理器。"""

    def test_file_resource_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "a" / "b.txt"
            with FileResourceManager(file_path, mode="w", encoding="utf-8") as f:
                f.write("hello")
            self.assertTrue(file_path.exists())
            with open(file_path, "r", encoding="utf-8") as f:  # noqa: PTH123
                self.assertEqual(f.read(), "hello")

    def test_serial_resource_manager_with_factory(self) -> None:
        closed = {"value": False}

        class DummySerial:
            is_open = True

            def close(self) -> None:
                closed["value"] = True

        def factory(**kwargs):
            return DummySerial()

        manager = SerialResourceManager("COM1", serial_factory=factory)
        with manager as ser:
            self.assertIsNotNone(ser)
            self.assertFalse(closed["value"])
        self.assertTrue(closed["value"])

        manager.close()  # 幂等
        self.assertTrue(closed["value"])

    def test_socket_resource_manager(self) -> None:
        calls: dict[str, object] = {"connected": False, "closed": False, "shutdown": False}

        class DummySocket:
            def settimeout(self, timeout: float) -> None:
                calls["timeout"] = timeout

            def connect(self, addr) -> None:  # noqa: ANN001
                calls["connected"] = True
                calls["addr"] = addr

            def shutdown(self, how: int) -> None:
                calls["shutdown"] = True

            def close(self) -> None:
                calls["closed"] = True

        with patch.object(resource_manager_module.socket, "socket", return_value=DummySocket()):
            with SocketResourceManager("127.0.0.1", 12345, timeout=1.0) as sock:
                self.assertIsInstance(sock, DummySocket)
                self.assertTrue(calls["connected"])

        self.assertTrue(calls["shutdown"])
        self.assertTrue(calls["closed"])

    def test_socket_shutdown_oserror_is_ignored(self) -> None:
        calls: dict[str, object] = {"closed": False}

        class DummySocket:
            def settimeout(self, timeout: float) -> None:
                return None

            def connect(self, addr) -> None:  # noqa: ANN001
                return None

            def shutdown(self, how: int) -> None:
                raise OSError("already closed")

            def close(self) -> None:
                calls["closed"] = True

        with patch.object(resource_manager_module.socket, "socket", return_value=DummySocket()):
            with SocketResourceManager("127.0.0.1", 12345, timeout=1.0):
                pass

        self.assertTrue(calls["closed"])

    def test_resource_error_on_open_failure(self) -> None:
        class BadManager(FileResourceManager):
            def _open(self):  # type: ignore[override]
                raise RuntimeError("fail")

        manager = BadManager("x.txt")
        with self.assertRaises(ResourceError):
            manager.open()


if __name__ == "__main__":
    unittest.main()
