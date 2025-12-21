"""测试硬件抽象层（hardware-abstraction）。"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.core.container import Container
from voc_app.core.interfaces import HardwareController
from voc_app.core.registry import ComponentRegistry
from voc_app.hardware.controller import AbstractHardwareController
from voc_app.hardware.factory import HardwareControllerFactory
from voc_app.hardware.loadport.e84_controller import E84Controller, E84State, Signal
from voc_app.hardware.loadport.e84_thread import E84ControllerThread
from voc_app.hardware.loadport.gpio_controller import GPIOController
from voc_app.hardware.loadport import e84_controller as e84_module


class DummyController(AbstractHardwareController):
    """用于覆盖 AbstractHardwareController 的最小实现。"""

    def __init__(self) -> None:
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> dict:
        return {"running": self._running}

    def reset(self) -> None:
        self._running = False


class TestAbstractHardwareController(unittest.TestCase):
    def test_dummy_controller_implements_all_methods(self) -> None:
        ctrl = DummyController()
        self.assertFalse(ctrl.is_running())
        ctrl.start()
        self.assertTrue(ctrl.is_running())
        self.assertEqual(ctrl.get_status()["running"], True)
        ctrl.reset()
        self.assertFalse(ctrl.is_running())

    def test_base_abstract_methods_can_be_called_for_coverage(self) -> None:
        """显式调用抽象基类方法体，覆盖 controller.py 的可执行行。"""
        ctrl = DummyController()
        AbstractHardwareController.get_status(ctrl)
        AbstractHardwareController.reset(ctrl)


class TestHardwareControllerFactory(unittest.TestCase):
    def test_register_and_create_class(self) -> None:
        registry = ComponentRegistry()
        factory = HardwareControllerFactory(registry)
        factory.register("dummy", DummyController, validate=True)

        controller = factory.create("dummy")
        self.assertIsInstance(controller, DummyController)

    def test_register_instance_and_create(self) -> None:
        factory = HardwareControllerFactory()
        instance = DummyController()
        factory.register("dummy_instance", instance, validate=True)
        self.assertIs(factory.create("dummy_instance"), instance)

    def test_create_via_container_auto_wiring(self) -> None:
        """当注册的是“类”且未提供 kwargs 时，允许通过 Container 自动装配。"""
        factory = HardwareControllerFactory()
        factory.register("dummy", DummyController, validate=True)

        container = Container()
        controller = factory.create("dummy", container=container)
        self.assertIsInstance(controller, DummyController)

    def test_create_unsupported_component_raises(self) -> None:
        factory = HardwareControllerFactory()
        factory.registry.register(HardwareController, "bad", object(), validate=False)
        with self.assertRaises(TypeError):
            factory.create("bad")


class TestGPIOController(unittest.TestCase):
    def test_gpio_controller_imports_without_rpi_gpio(self) -> None:
        """验证模块可导入；在缺少 RPi.GPIO 时，初始化会抛出清晰异常。"""
        with self.assertRaises(RuntimeError):
            GPIOController({}, {}, 1, True)

    def test_gpio_controller_can_work_with_injected_gpio_module(self) -> None:
        class FakeGPIOModule:
            BCM = "BCM"
            IN = "IN"
            OUT = "OUT"
            PUD_UP = "PUD_UP"
            PUD_DOWN = "PUD_DOWN"
            HIGH = 1
            LOW = 0

            def __init__(self) -> None:
                self.modes = []
                self.setups = []
                self.inputs: dict[int, int] = {}
                self.outputs: dict[int, int] = {}
                self.cleaned = False

            def setmode(self, mode):
                self.modes.append(mode)

            def setup(self, pin_num, mode, pull_up_down=None):
                self.setups.append((pin_num, mode, pull_up_down))

            def input(self, pin_num):
                return self.inputs.get(pin_num, self.LOW)

            def output(self, pin_num, state):
                self.outputs[pin_num] = state

            def cleanup(self):
                self.cleaned = True

        fake = FakeGPIOModule()
        fake.inputs[1] = fake.HIGH

        ctrl = GPIOController(
            input_pins_config={"IN1": 1},
            output_pins_config={"OUT1": 2},
            pull_status=1,
            default_state=True,
            gpio_module=fake,
        )

        self.assertEqual(ctrl.read_input("IN1"), fake.HIGH)
        self.assertEqual(ctrl.read_all_inputs(), {"IN1": False})

        ctrl.set_output("OUT1", fake.LOW)
        self.assertEqual(fake.outputs[2], fake.LOW)

        ctrl.set_all_outputs(fake.HIGH)
        self.assertEqual(fake.outputs[2], fake.HIGH)

        with self.assertRaises(ValueError):
            ctrl.read_input("MISSING")
        with self.assertRaises(ValueError):
            ctrl.set_output("MISSING", True)

        ctrl.cleanup()
        self.assertTrue(fake.cleaned)


class TestE84Controller(unittest.TestCase):
    def _make_fake_gpio(self):
        shared_state: dict[str, bool] = {}
        outputs: dict[str, bool] = {}

        class FakeGPIOController:
            def __init__(self, input_pins_config, output_pins_config, pull_status, default_state):
                self._input_names = list(input_pins_config.keys())
                self._output_names = list(output_pins_config.keys())
                for name in self._output_names:
                    outputs[name] = default_state

            def read_all_inputs(self):
                return {name: bool(shared_state.get(name, False)) for name in self._input_names}

            def set_output(self, pin_name: str, state: bool) -> None:
                outputs[pin_name] = state

            def set_all_outputs(self, state: bool) -> None:
                for name in self._output_names:
                    outputs[name] = state

        return shared_state, outputs, FakeGPIOController

    def test_e84_controller_has_required_interface_methods(self) -> None:
        state, _, fake_gpio = self._make_fake_gpio()
        controller = E84Controller(
            refresh_interval=0.01,
            gpio_controller_cls=fake_gpio,
            sleep_func=lambda _: None,
            debounce_interval=0.0,
        )
        self.assertFalse(controller.is_running())
        controller.start()
        self.assertTrue(controller.is_running())
        controller.stop()
        self.assertFalse(controller.is_running())

        status = controller.get_status()
        self.assertIn("state", status)
        self.assertIn("inputs", status)
        self.assertIn("keys", status)

        controller.reset()

    def test_e84_refresh_input_warns_when_go_is_low(self) -> None:
        state, outputs, fake_gpio = self._make_fake_gpio()
        controller = E84Controller(
            refresh_interval=0.01,
            gpio_controller_cls=fake_gpio,
            sleep_func=lambda _: None,
            debounce_interval=0.0,
        )

        warnings: list[str] = []
        controller.warning.connect(lambda msg: warnings.append(msg))

        state.update({"GO": False})
        controller.Refresh_Input()

        self.assertGreaterEqual(len(warnings), 1)
        self.assertTrue(outputs.get("SENSOR_LED", False))

    def test_e84_refresh_input_debounce_branch_can_be_triggered(self) -> None:
        state, _, fake_gpio = self._make_fake_gpio()
        controller = E84Controller(
            refresh_interval=0.01,
            gpio_controller_cls=fake_gpio,
            sleep_func=lambda _: None,
            debounce_interval=0.0,
        )

        # 人为制造“旧值 != 新值”，覆盖防抖分支
        controller.E84_Key_Old_Value = {"KEY_0": True, "KEY_1": False, "KEY_2": False}
        state.update({"KEY_0": False, "KEY_1": False, "KEY_2": False})
        controller.Refresh_Input()

    def test_e84_timeout_and_interrupt_paths(self) -> None:
        state, _, fake_gpio = self._make_fake_gpio()
        controller = E84Controller(
            refresh_interval=0.01,
            gpio_controller_cls=fake_gpio,
            sleep_func=lambda _: None,
            debounce_interval=0.0,
        )

        # 覆盖 wait_* 的 timeout 分支
        controller._timeout_deadline = time.monotonic() - 1  # type: ignore[attr-defined]
        self.assertEqual(controller.E84_wait_TR_REQ(), 1)

        # 覆盖 wait_* 的 0 返回（无 timeout 且条件不满足）
        controller._timeout_deadline = None  # type: ignore[attr-defined]
        state.update({"TR_REQ": False})
        controller.Refresh_Input()
        self.assertEqual(controller.E84_wait_TR_REQ(), 0)

        # 覆盖 L_REQ 中断分支（信号缺失）
        state.update({"CS_0": False, "VALID": True, "TR_REQ": True, "BUSY": True})
        controller.Refresh_Input()
        self.assertEqual(controller.E84_wait_L_REQ(), 1)

    def test_e84_test_out_pin_calls_set_all_outputs(self) -> None:
        _, outputs, fake_gpio = self._make_fake_gpio()
        controller = E84Controller(
            refresh_interval=0.01,
            gpio_controller_cls=fake_gpio,
            sleep_func=lambda _: None,
            debounce_interval=0.0,
        )

        controller.E84_TestOutPin()
        self.assertIn("READY", outputs)

    def test_as_str_int_dict_handles_invalid_values(self) -> None:
        default = {"A": 1}
        self.assertEqual(e84_module._as_str_int_dict("bad", default=default), default)  # type: ignore[arg-type]
        self.assertEqual(e84_module._as_str_int_dict({"A": "x"}, default=default), default)  # type: ignore[arg-type]
        self.assertEqual(e84_module._as_str_int_dict({"A": 2, 3: 4}, default=default), {"A": 2})  # type: ignore[arg-type]

    def test_more_wait_paths_for_coverage(self) -> None:
        state, _, fake_gpio = self._make_fake_gpio()
        controller = E84Controller(
            refresh_interval=0.01,
            gpio_controller_cls=fake_gpio,
            sleep_func=lambda _: None,
            debounce_interval=0.0,
        )

        # 未满足握手条件时应返回 0
        state.update({"GO": False, "CS_0": False, "VALID": False})
        controller.Refresh_Input()
        self.assertEqual(controller.E84Handoff(), 0)

        # COMPT 未到且无 timeout 时返回 0
        controller._timeout_deadline = None  # type: ignore[attr-defined]
        state.update({"COMPT": False})
        controller.Refresh_Input()
        self.assertEqual(controller.E84_wait_COMPT(), 0)

    def test_misc_branches_for_coverage(self) -> None:
        """覆盖若干边缘分支，提升 hardware/loadport/e84_controller.py 覆盖率。"""

        class BadIntervalConfig:
            def get(self, key: str, default=None):
                if key == "hardware.loadport.e84.refresh_interval":
                    return "bad"
                return default

            def set(self, key: str, value) -> None:
                return None

            def load(self) -> None:
                return None

            def save(self) -> None:
                return None

        state, outputs, fake_gpio = self._make_fake_gpio()
        controller = E84Controller(
            refresh_interval=0.01,
            config=BadIntervalConfig(),  # type: ignore[arg-type]
            gpio_controller_cls=fake_gpio,
            sleep_func=lambda _: None,
            debounce_interval=0.0,
        )

        # any_key=True 但 all_keys_on=False 的分支
        state.update({"KEY_0": True, "KEY_1": False, "KEY_2": False, "GO": True})
        controller.Refresh_Input()
        self.assertTrue(outputs.get("HO_AVBL", False))
        self.assertTrue(outputs.get("ES", False))
        self.assertFalse(outputs.get("ALARM_LED", True))

        # led_cnt > 10 的分支
        controller.led_cnt = 11
        controller.Refresh_Input()
        self.assertEqual(controller.led_cnt, 1)

        # led_cnt == 10 触发 CODE_LED OFF 分支
        controller.led_cnt = 9
        controller.Refresh_Input()
        self.assertTrue(outputs.get("CODE_LED", False))

        # start 已运行时再次 start 应直接返回
        controller.start()
        controller.start()
        controller.stop()

        # 兼容旧入口
        controller.E84_main()
        self.assertTrue(controller.is_running())
        controller.stop()

    def test_run_cycle_exception_emits_fatal_error(self) -> None:
        _, _, fake_gpio = self._make_fake_gpio()
        controller = E84Controller(
            refresh_interval=0.01,
            gpio_controller_cls=fake_gpio,
            sleep_func=lambda _: None,
            debounce_interval=0.0,
        )

        fatals: list[str] = []
        controller.fatal_error.connect(lambda msg: fatals.append(msg))

        def boom():
            raise RuntimeError("boom")

        controller.Refresh_Input = boom  # type: ignore[method-assign]
        controller._run_cycle()
        self.assertGreaterEqual(len(fatals), 1)

    def test_e84_state_machine_load_flow(self) -> None:
        """覆盖典型 Load 流程：IDLE -> WAIT_TR_REQ -> WAIT_BUSY -> WAIT_L_REQ -> WAIT_COMPT -> WAIT_DONE -> IDLE。"""
        state, outputs, fake_gpio = self._make_fake_gpio()
        controller = E84Controller(
            refresh_interval=0.01,
            gpio_controller_cls=fake_gpio,
            sleep_func=lambda _: None,
            debounce_interval=0.0,
        )

        observed_states: list[str] = []
        controller.state_changed.connect(lambda s: observed_states.append(s))

        # 初始：无 KEY，FOUP_status=False，对应 Load 流程
        state.update({"GO": True, "CS_0": True, "VALID": True})
        controller._run_cycle()
        self.assertEqual(controller.state, E84State.WAIT_TR_REQ)
        self.assertTrue(outputs.get("L_REQ", True) is False)

        state.update({"TR_REQ": True})
        controller._run_cycle()
        self.assertEqual(controller.state, E84State.WAIT_BUSY)
        self.assertTrue(outputs.get("READY", True) is False)

        state.update({"BUSY": True})
        controller._run_cycle()
        self.assertEqual(controller.state, E84State.WAIT_L_REQ)

        # FOUP 放回（KEY 全部为 True）
        state.update({"KEY_0": True, "KEY_1": True, "KEY_2": True})
        controller._run_cycle()
        self.assertEqual(controller.state, E84State.WAIT_COMPT)

        state.update({"COMPT": True})
        controller._run_cycle()
        self.assertEqual(controller.state, E84State.WAIT_DONE)

        # TRANS OVER
        state.update({"CS_0": False, "VALID": False, "COMPT": False})
        controller._run_cycle()
        self.assertEqual(controller.state, E84State.IDLE)

        self.assertIn(E84State.IDLE.value, observed_states)

    def test_e84_state_machine_unload_flow_emits_start_and_stop(self) -> None:
        """覆盖典型 Unload 流程，并验证采集 START/STOP 信号会被触发。"""
        state, _, fake_gpio = self._make_fake_gpio()
        controller = E84Controller(
            refresh_interval=0.01,
            gpio_controller_cls=fake_gpio,
            sleep_func=lambda _: None,
            debounce_interval=0.0,
        )

        started = []
        stopped = []
        controller.data_collection_start.connect(lambda: started.append(True))
        controller.data_collection_stop.connect(lambda: stopped.append(True))

        # 初始：KEY 全部为 True，FOUP_status=True，对应 Unload 流程
        state.update({"KEY_0": True, "KEY_1": True, "KEY_2": True})
        state.update({"GO": True, "CS_0": True, "VALID": True})
        controller._run_cycle()
        self.assertEqual(controller.state, E84State.WAIT_TR_REQ)
        self.assertEqual(len(started), 1)

        state.update({"TR_REQ": True})
        controller._run_cycle()
        self.assertEqual(controller.state, E84State.WAIT_BUSY)

        state.update({"BUSY": True})
        controller._run_cycle()
        self.assertEqual(controller.state, E84State.WAIT_U_REQ)

        # FOUP 移走（KEY 全部为 False）让 WAIT_U_REQ 完成
        state.update({"KEY_0": False, "KEY_1": False, "KEY_2": False})
        controller._run_cycle()
        self.assertEqual(controller.state, E84State.WAIT_COMPT)

        state.update({"COMPT": True})
        controller._run_cycle()
        self.assertEqual(controller.state, E84State.WAIT_DONE)
        self.assertEqual(len(stopped), 1)

        state.update({"CS_0": False, "VALID": False, "COMPT": False})
        controller._run_cycle()
        self.assertEqual(controller.state, E84State.IDLE)


class TestSignal(unittest.TestCase):
    def test_signal_connect_emit_disconnect(self) -> None:
        sig = Signal()
        called = []

        def handler(value):
            called.append(value)

        sig.connect(handler)
        sig.emit(1)
        sig.disconnect(handler)
        sig.emit(2)
        self.assertEqual(called, [1])


class TestE84ControllerThread(unittest.TestCase):
    def _make_fake_gpio(self):
        shared_state: dict[str, bool] = {}

        class FakeGPIOController:
            def __init__(self, input_pins_config, output_pins_config, pull_status, default_state):
                self._input_names = list(input_pins_config.keys())

            def read_all_inputs(self):
                return {name: bool(shared_state.get(name, False)) for name in self._input_names}

            def set_output(self, pin_name: str, state: bool) -> None:
                return None

            def set_all_outputs(self, state: bool) -> None:
                return None

        return shared_state, FakeGPIOController

    def test_thread_wrapper_relays_controller_signals(self) -> None:
        state, fake_gpio = self._make_fake_gpio()
        worker = E84ControllerThread(
            gpio_controller_cls=fake_gpio,
            sleep_func=lambda _: None,
            debounce_interval=0.0,
        )

        ready: list[E84Controller] = []
        states: list[str] = []
        warnings: list[str] = []
        fatals: list[str] = []
        events: list[tuple[str, str]] = []
        worker.controller_ready.connect(lambda c: ready.append(c))
        worker.e84_state_changed.connect(lambda s: states.append(s))
        worker.e84_warning.connect(lambda s: warnings.append(s))
        worker.e84_fatal_error.connect(lambda s: fatals.append(s))
        worker.system_event.connect(lambda k, v: events.append((k, v)))

        worker.start()
        self.assertTrue(worker.is_running())
        self.assertEqual(len(ready), 1)

        # 手动触发底层控制器状态信号，验证转发
        ready[0].state_changed.emit("idle")
        self.assertIn("idle", states)

        ready[0].warning.emit("w")
        ready[0].fatal_error.emit("f")
        ready[0].all_keys_set.emit()
        self.assertIn("w", warnings)
        self.assertIn("f", fatals)
        self.assertIn(("e84_all_keys_set", "true"), events)

        worker.stop()
        self.assertFalse(worker.is_running())

    def test_thread_wrapper_emits_error_when_controller_fails(self) -> None:
        class BadGPIOController:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("no gpio")

        worker = E84ControllerThread(gpio_controller_cls=BadGPIOController)
        errors: list[str] = []
        worker.error.connect(lambda msg: errors.append(msg))
        worker.start()
        self.assertGreaterEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
