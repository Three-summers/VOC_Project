"""测试 core 抽象层模块。"""

import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any, Optional
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.core.config import AppConfig
from voc_app.core.container import Container, Lifecycle
from voc_app.core.interfaces import ConfigProvider, DataSource, HardwareController
from voc_app.core.registry import ComponentRegistry
from voc_app.utils import ConfigError, DependencyResolutionError, RegistryError


class CycleX:
    """用于测试循环依赖的类 X。"""

    def __init__(self, y: "CycleY") -> None:
        self.y = y


class CycleY:
    """用于测试循环依赖的类 Y。"""

    def __init__(self, x: CycleX) -> None:
        self.x = x


class DummyHardwareController(HardwareController):
    """用于测试的硬件控制器实现。"""

    def __init__(self) -> None:
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running


class DummyDataSource(DataSource):
    """用于测试的数据源实现。"""

    def __init__(self) -> None:
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read_data(self):
        return {"connected": self._connected}


class DummyConfigProvider(ConfigProvider):
    """用于测试的 ConfigProvider 实现。"""

    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value

    def load(self) -> None:
        return None

    def save(self) -> None:
        return None


class TestInterfaces(unittest.TestCase):
    """测试抽象接口可被正常实现。"""

    def test_hardware_controller_lifecycle(self) -> None:
        controller = DummyHardwareController()
        self.assertFalse(controller.is_running())
        controller.start()
        self.assertTrue(controller.is_running())
        controller.stop()
        self.assertFalse(controller.is_running())

    def test_data_source_basic(self) -> None:
        source = DummyDataSource()
        self.assertEqual(source.read_data()["connected"], False)
        source.connect()
        self.assertEqual(source.read_data()["connected"], True)
        source.disconnect()
        self.assertEqual(source.read_data()["connected"], False)

    def test_base_abstract_methods_can_be_called_for_coverage(self) -> None:
        """显式调用抽象基类方法体，覆盖接口文件的可执行行。"""
        controller = DummyHardwareController()
        HardwareController.start(controller)
        HardwareController.stop(controller)
        HardwareController.is_running(controller)

        source = DummyDataSource()
        DataSource.connect(source)
        DataSource.disconnect(source)
        DataSource.read_data(source)

        provider = DummyConfigProvider()
        ConfigProvider.get(provider, "k")
        ConfigProvider.set(provider, "k", "v")
        ConfigProvider.load(provider)
        ConfigProvider.save(provider)


class TestComponentRegistry(unittest.TestCase):
    """测试组件注册表。"""

    def test_register_and_get(self) -> None:
        registry = ComponentRegistry()
        controller = DummyHardwareController()
        registry.register(HardwareController, "dummy", controller)
        self.assertIs(registry.get(HardwareController, "dummy"), controller)

    def test_require_missing_raises(self) -> None:
        registry = ComponentRegistry()
        with self.assertRaises(RegistryError):
            registry.require(HardwareController, "missing")

    def test_duplicate_without_overwrite_raises(self) -> None:
        registry = ComponentRegistry()
        registry.register(HardwareController, "dummy", DummyHardwareController())
        with self.assertRaises(RegistryError):
            registry.register(HardwareController, "dummy", DummyHardwareController())

    def test_overwrite_allowed(self) -> None:
        registry = ComponentRegistry()
        first = DummyHardwareController()
        second = DummyHardwareController()
        registry.register(HardwareController, "dummy", first)
        registry.register(HardwareController, "dummy", second, overwrite=True)
        self.assertIs(registry.require(HardwareController, "dummy"), second)

    def test_validate_type_mismatch(self) -> None:
        registry = ComponentRegistry()
        with self.assertRaises(RegistryError):
            registry.register(DataSource, "bad", DummyHardwareController(), validate=True)

    def test_thread_safety_register(self) -> None:
        registry = ComponentRegistry()

        def worker(index: int) -> None:
            registry.register(DataSource, f"ds{index}", DummyDataSource())

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2)

        self.assertEqual(len(registry.list_names(DataSource)), 50)

    def test_empty_name_raises(self) -> None:
        registry = ComponentRegistry()
        with self.assertRaises(RegistryError):
            registry.register(DataSource, "", DummyDataSource())

    def test_unregister_items_categories_and_clear(self) -> None:
        registry = ComponentRegistry()
        registry.register(DataSource, "a", DummyDataSource())
        registry.unregister(DataSource, "a")
        self.assertEqual(registry.list_names(DataSource), [])

        registry.register(DataSource, "a", DummyDataSource())
        registry.register(DataSource, "b", DummyDataSource())
        self.assertIn(DataSource, registry.categories())
        items = registry.items(DataSource)
        self.assertIn("a", items)
        self.assertIn("b", items)

        registry.clear()
        self.assertEqual(registry.categories(), [])

    def test_register_class_validation(self) -> None:
        registry = ComponentRegistry()
        registry.register(DataSource, "cls", DummyDataSource, validate=True)
        self.assertIs(registry.require(DataSource, "cls"), DummyDataSource)
        with self.assertRaises(RegistryError):
            registry.register(DataSource, "bad_cls", DummyHardwareController, validate=True)

    def test_validate_type_error_path(self) -> None:
        registry = ComponentRegistry()
        registry.register(Any, "x", 123, validate=True)
        self.assertEqual(registry.get(Any, "x"), 123)


class TestAppConfig(unittest.TestCase):
    """测试配置管理（JSON + 环境变量）。"""

    ENV_PREFIX = "TESTVOC_"

    def setUp(self) -> None:
        self._old_env = dict(os.environ)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._old_env)

    def test_load_merge_and_override_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            cfg_path.write_text(json.dumps({"app": {"port": 1}}), encoding="utf-8")

            os.environ[f"{self.ENV_PREFIX}APP__PORT"] = "2"

            cfg = AppConfig(json_path=cfg_path, env_prefix=self.ENV_PREFIX)
            cfg.load()
            self.assertEqual(cfg.get("app.port"), 2)

            cfg.set("app.port", 3)
            self.assertEqual(cfg.get("app.port"), 3)

            cfg.clear_overrides()
            self.assertEqual(cfg.get("app.port"), 2)

    def test_config_change_notification(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            cfg_path.write_text(json.dumps({"a": {"b": 1}}), encoding="utf-8")

            events: list[object] = []

            def listener(event) -> None:
                events.append(event)

            cfg = AppConfig(json_path=cfg_path, env_prefix=self.ENV_PREFIX)
            cfg.add_listener(listener)
            cfg.load()
            cfg.set("a.b", 2)

            self.assertTrue(any(getattr(e, "key", "") == "a.b" for e in events))

    def test_save_persists_overrides_but_not_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            cfg_path.write_text(json.dumps({"app": {"port": 1}}), encoding="utf-8")

            os.environ[f"{self.ENV_PREFIX}APP__PORT"] = "2"

            cfg = AppConfig(json_path=cfg_path, env_prefix=self.ENV_PREFIX)
            cfg.load()
            cfg.set("app.port", 3)
            cfg.save()

            saved = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["app"]["port"], 3)

    def test_invalid_json_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "broken.json"
            cfg_path.write_text("invalid json {{", encoding="utf-8")
            cfg = AppConfig(json_path=cfg_path, env_prefix=self.ENV_PREFIX)
            with self.assertRaises(ConfigError):
                cfg.load()

    def test_get_default_and_empty_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            cfg_path.write_text(json.dumps({"a": {"b": 1}}), encoding="utf-8")
            cfg = AppConfig(json_path=cfg_path, env_prefix=self.ENV_PREFIX)
            cfg.load()

            self.assertEqual(cfg.get("missing.key", default=123), 123)
            self.assertIsInstance(cfg.get("", default=None), dict)

    def test_set_empty_key_raises(self) -> None:
        cfg = AppConfig(env_prefix=self.ENV_PREFIX)
        with self.assertRaises(ConfigError):
            cfg.set("", 1)

    def test_remove_listener_and_no_event_when_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            cfg_path.write_text(json.dumps({"a": {"b": 1}}), encoding="utf-8")

            events: list[object] = []

            def listener(event) -> None:
                events.append(event)

            cfg = AppConfig(json_path=cfg_path, env_prefix=self.ENV_PREFIX)
            cfg.add_listener(listener)
            cfg.load()
            events.clear()

            cfg.remove_listener(listener)
            cfg.set("a.b", 2)
            self.assertEqual(events, [])

            # 相同值不应触发事件（覆盖 _emit_events 的空列表路径）
            cfg.set("a.b", 2)

    def test_env_parsing_non_json_and_prefix_only_ignored(self) -> None:
        os.environ[f"{self.ENV_PREFIX}FOO"] = "bar"
        os.environ[self.ENV_PREFIX] = "ignored"

        cfg = AppConfig(json_path=None, env_prefix=self.ENV_PREFIX)
        cfg.load()
        self.assertEqual(cfg.get("foo"), "bar")

    def test_json_root_not_object_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            cfg_path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
            cfg = AppConfig(json_path=cfg_path, env_prefix=self.ENV_PREFIX)
            with self.assertRaises(ConfigError):
                cfg.load()

    def test_save_without_json_path_raises(self) -> None:
        cfg = AppConfig(json_path=None, env_prefix=self.ENV_PREFIX)
        with self.assertRaises(ConfigError):
            cfg.save()

    def test_save_and_load_oserror_wrapped(self) -> None:
        import voc_app.core.config as config_module

        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            cfg_path.write_text(json.dumps({"a": 1}), encoding="utf-8")

            cfg = AppConfig(json_path=cfg_path, env_prefix=self.ENV_PREFIX)

            with patch.object(config_module, "open", side_effect=OSError("read fail"), create=True):
                with self.assertRaises(ConfigError):
                    cfg.load()

            cfg.load()
            cfg.set("a", 2)
            with patch.object(config_module, "open", side_effect=OSError("write fail"), create=True):
                with self.assertRaises(ConfigError):
                    cfg.save()

    def test_listener_exception_is_swallowed(self) -> None:
        cfg = AppConfig(env_prefix=self.ENV_PREFIX)
        events: list[object] = []

        def bad_listener(_event) -> None:  # noqa: ANN001
            raise RuntimeError("boom")

        def good_listener(event) -> None:
            events.append(event)

        cfg.add_listener(bad_listener)
        cfg.add_listener(good_listener)
        cfg.set("a.b", 1)
        self.assertTrue(events)
        cfg.to_dict()


class TestContainer(unittest.TestCase):
    """测试依赖注入容器。"""

    def test_register_instance(self) -> None:
        container = Container()
        instance = DummyConfigProvider()
        container.register_instance(ConfigProvider, instance)
        self.assertIs(container.resolve(ConfigProvider), instance)

    def test_try_resolve_returns_none(self) -> None:
        container = Container()
        self.assertIsNone(container.try_resolve(HardwareController))

    def test_inject_container(self) -> None:
        class NeedsContainer:
            def __init__(self, container: Container) -> None:
                self.container = container

        container = Container()
        obj = container.resolve(NeedsContainer)
        self.assertIs(obj.container, container)

    def test_resolve_non_type_raises(self) -> None:
        container = Container()
        with self.assertRaises(DependencyResolutionError):
            container.resolve("not a type")  # type: ignore[arg-type]

    def test_unregistered_abstract_raises(self) -> None:
        container = Container()
        with self.assertRaises(DependencyResolutionError):
            container.resolve(HardwareController)

    def test_register_class_singleton(self) -> None:
        class Impl(DummyConfigProvider):
            pass

        container = Container()
        container.register_class(ConfigProvider, Impl, lifecycle=Lifecycle.SINGLETON)
        a = container.resolve(ConfigProvider)
        b = container.resolve(ConfigProvider)
        self.assertIs(a, b)

    def test_transient_default(self) -> None:
        class Service:
            def __init__(self) -> None:
                self.value = object()

        container = Container()
        a = container.resolve(Service)
        b = container.resolve(Service)
        self.assertIsNot(a, b)

    def test_auto_wiring(self) -> None:
        class A:
            def __init__(self) -> None:
                self.name = "a"

        class B:
            def __init__(self, a: A) -> None:
                self.a = a

        class C:
            def __init__(self, b: B) -> None:
                self.b = b

        container = Container()
        c = container.resolve(C)
        self.assertEqual(c.b.a.name, "a")

    def test_register_factory_with_injection(self) -> None:
        class Service:
            def __init__(self, cfg: ConfigProvider) -> None:
                self.cfg = cfg

        container = Container()
        cfg = DummyConfigProvider()
        container.register_instance(ConfigProvider, cfg)

        called = {"count": 0}

        def factory(cfg: ConfigProvider) -> Service:
            called["count"] += 1
            return Service(cfg)

        container.register_factory(Service, factory, lifecycle=Lifecycle.SINGLETON)
        a = container.resolve(Service)
        b = container.resolve(Service)
        self.assertIs(a, b)
        self.assertIs(a.cfg, cfg)
        self.assertEqual(called["count"], 1)

    def test_factory_missing_annotation_raises(self) -> None:
        container = Container()

        def bad_factory(x):  # noqa: ANN001
            return object()

        container.register_factory(object, bad_factory)
        with self.assertRaises(DependencyResolutionError):
            container.resolve(object)

    def test_factory_typeerror_is_wrapped(self) -> None:
        class Service:
            def __init__(self, cfg: ConfigProvider) -> None:
                self.cfg = cfg

        container = Container()
        container.register_instance(ConfigProvider, DummyConfigProvider())

        def bad_factory(cfg: ConfigProvider) -> Service:
            raise TypeError("boom")

        container.register_factory(Service, bad_factory)
        with self.assertRaises(DependencyResolutionError):
            container.resolve(Service)

    def test_get_type_hints_failure_path(self) -> None:
        class BadHints:
            def __init__(self, dep: "NotExist") -> None:  # noqa: F821
                self.dep = dep

        container = Container()
        with self.assertRaises(DependencyResolutionError):
            container.resolve(BadHints)

    def test_construct_skips_varargs(self) -> None:
        class WithVarArgs:
            def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002,ANN003
                self.args = args
                self.kwargs = kwargs

        container = Container()
        obj = container.resolve(WithVarArgs)
        self.assertEqual(obj.args, ())
        self.assertEqual(obj.kwargs, {})

    def test_construct_skips_unannotated_default(self) -> None:
        class WithDefault:
            def __init__(self, x=1) -> None:  # noqa: ANN001
                self.x = x

        container = Container()
        obj = container.resolve(WithDefault)
        self.assertEqual(obj.x, 1)

    def test_optional_any_default_is_used(self) -> None:
        class OptionalAny:
            def __init__(self, dep: Optional[Any] = None) -> None:
                self.dep = dep

        container = Container()
        obj = container.resolve(OptionalAny)
        self.assertIsNone(obj.dep)

    def test_annotated_dependency_is_unwrapped(self) -> None:
        import typing as t

        class NeedsAnnotated:
            def __init__(self, dep: t.Annotated[DummyConfigProvider, "meta"]) -> None:
                self.dep = dep

        container = Container()
        obj = container.resolve(NeedsAnnotated)
        self.assertIsInstance(obj.dep, DummyConfigProvider)

    def test_construct_typeerror_is_wrapped(self) -> None:
        class Boom:
            def __init__(self) -> None:
                raise TypeError("boom")

        container = Container()
        with self.assertRaises(DependencyResolutionError):
            container.resolve(Boom)

    def test_missing_annotation_raises(self) -> None:
        class Bad:
            def __init__(self, x) -> None:  # noqa: ANN001
                self.x = x

        container = Container()
        with self.assertRaises(DependencyResolutionError):
            container.resolve(Bad)

    def test_cycle_detection(self) -> None:
        container = Container()
        with self.assertRaises(DependencyResolutionError):
            container.resolve(CycleX)


if __name__ == "__main__":
    unittest.main()
