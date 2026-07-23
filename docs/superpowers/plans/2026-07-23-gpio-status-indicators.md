# GPIO Status Indicators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Initialize the buzzer and three-color status indicator outputs at GUI startup, leaving only the green LED on.

**Architecture:** Keep `app.py` responsible for optional `RPi.GPIO` detection and startup error handling. Add a small GPIO-independent helper module that receives a GPIO-compatible object, configures the four BCM outputs low, and then turns BCM26 high; this makes the hardware sequence unit-testable on WSL2.

**Tech Stack:** Python 3.11+, PySide6 GUI bootstrap, optional `RPi.GPIO`, pytest.

## Global Constraints

- GPIO numbering uses BCM mode.
- GPIO14 (buzzer), GPIO7 (red), and GPIO25 (yellow) must start LOW.
- GPIO26 (green) must start HIGH after every other status output is set LOW.
- A missing `RPi.GPIO` module or a GPIO initialization exception must not prevent GUI startup.
- Do not add runtime UI controls, timers, or business rules for the buzzer or status LEDs.
- Do not modify `src/voc_app/loadport/gpio_controller.py` or add GPIO cleanup behavior.

---

## File Structure

- Create `src/voc_app/gui/status_gpio.py`: contains the four-pin mapping and the deterministic output initialization sequence. It has no direct dependency on `RPi.GPIO` so a fake object can drive its tests.
- Create `tests/test_status_gpio.py`: tests the pin setup sequence and all four required startup states using a recording fake GPIO object.
- Modify `src/voc_app/gui/app.py:34-43,570-580`: retains optional `RPi.GPIO` loading, calls the helper before `QApplication` is created, and logs failures without aborting startup.
- Create `tests/test_gui_app_gpio.py`: tests the GUI startup wrapper for its available, unavailable, and exception cases without touching physical GPIO.

### Task 1: Testable Status GPIO Initializer

**Files:**

- Create: `tests/test_status_gpio.py`
- Create: `src/voc_app/gui/status_gpio.py`

**Interfaces:**

- Consumes: a GPIO-compatible object exposing `BCM`, `OUT`, `LOW`, `HIGH`, `setmode(mode)`, `setup(pin, direction, *, initial)`, and `output(pin, state)`.
- Produces: `STATUS_OUTPUT_PINS: dict[str, int]` and `initialize_status_outputs(gpio: Any) -> None`.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.status_gpio import (
    STATUS_OUTPUT_PINS,
    initialize_status_outputs,
)


class RecordingGPIO:
    BCM = "BCM"
    OUT = "OUT"
    LOW = "LOW"
    HIGH = "HIGH"

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def setmode(self, mode: object) -> None:
        self.calls.append(("setmode", mode))

    def setup(self, pin: int, direction: object, *, initial: object) -> None:
        self.calls.append(("setup", pin, direction, initial))

    def output(self, pin: int, state: object) -> None:
        self.calls.append(("output", pin, state))


def test_initialize_status_outputs_turns_on_only_green() -> None:
    gpio = RecordingGPIO()

    initialize_status_outputs(gpio)

    assert STATUS_OUTPUT_PINS == {
        "buzzer": 14,
        "red": 7,
        "yellow": 25,
        "green": 26,
    }
    assert gpio.calls == [
        ("setmode", gpio.BCM),
        ("setup", 14, gpio.OUT, gpio.LOW),
        ("setup", 7, gpio.OUT, gpio.LOW),
        ("setup", 25, gpio.OUT, gpio.LOW),
        ("setup", 26, gpio.OUT, gpio.LOW),
        ("output", 26, gpio.HIGH),
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_status_gpio.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'voc_app.gui.status_gpio'`.

- [ ] **Step 3: Write minimal implementation**

```python
from typing import Any


STATUS_OUTPUT_PINS: dict[str, int] = {
    "buzzer": 14,
    "red": 7,
    "yellow": 25,
    "green": 26,
}


def initialize_status_outputs(gpio: Any) -> None:
    """Configure status outputs with only the green LED enabled."""
    gpio.setmode(gpio.BCM)
    for pin in STATUS_OUTPUT_PINS.values():
        gpio.setup(pin, gpio.OUT, initial=gpio.LOW)
    gpio.output(STATUS_OUTPUT_PINS["green"], gpio.HIGH)
```

`initial=gpio.LOW` ensures each output becomes low as it changes to output mode, avoiding an intermediate active state for the buzzer, red LED, or yellow LED.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_status_gpio.py -v`
Expected: PASS with `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/voc_app/gui/status_gpio.py tests/test_status_gpio.py
git commit -m "feat: add status GPIO initializer"
```

### Task 2: Wire the Initializer into GUI Startup

**Files:**

- Create: `tests/test_gui_app_gpio.py`
- Modify: `src/voc_app/gui/app.py:34-43,570-580`

**Interfaces:**

- Consumes: `initialize_status_outputs(gpio: Any) -> None` from `voc_app.gui.status_gpio`.
- Produces: `initialize_status_gpio() -> None`, a startup wrapper that is safe when `RPi.GPIO` is unavailable or the helper raises an exception.

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path
import sys
from unittest.mock import Mock

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui import app


def test_initialize_status_gpio_uses_available_rpi_gpio(monkeypatch) -> None:
    gpio = object()
    initialize = Mock()
    monkeypatch.setattr(app, "_HAS_RPI_GPIO", True)
    monkeypatch.setattr(app, "GPIO", gpio)
    monkeypatch.setattr(app, "initialize_status_outputs", initialize)

    app.initialize_status_gpio()

    initialize.assert_called_once_with(gpio)


def test_initialize_status_gpio_skips_when_rpi_gpio_is_unavailable(monkeypatch) -> None:
    initialize = Mock()
    monkeypatch.setattr(app, "_HAS_RPI_GPIO", False)
    monkeypatch.setattr(app, "GPIO", None)
    monkeypatch.setattr(app, "initialize_status_outputs", initialize)

    app.initialize_status_gpio()

    initialize.assert_not_called()


def test_initialize_status_gpio_logs_and_continues_after_gpio_failure(
    monkeypatch, caplog
) -> None:
    def raise_gpio_error(_gpio: object) -> None:
        raise RuntimeError("simulated GPIO failure")

    monkeypatch.setattr(app, "_HAS_RPI_GPIO", True)
    monkeypatch.setattr(app, "GPIO", object())
    monkeypatch.setattr(app, "initialize_status_outputs", raise_gpio_error)

    app.initialize_status_gpio()

    assert "状态指示器" in caplog.text
    assert "simulated GPIO failure" in caplog.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_gui_app_gpio.py -v`
Expected: FAIL during collection with `ImportError: cannot import name 'initialize_status_gpio'` or fail with `AttributeError` because the wrapper is not yet defined.

- [ ] **Step 3: Wire the helper into app startup**

Add the import with the other GUI imports:

```python
from voc_app.gui.status_gpio import initialize_status_outputs
```

Add this function immediately before the `if __name__ == "__main__":` block:

```python
def initialize_status_gpio() -> None:
    if _HAS_RPI_GPIO and GPIO is not None:
        try:
            initialize_status_outputs(GPIO)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"RPi.GPIO 状态指示器初始化失败，跳过 GPIO 置位: {exc}")
    elif _RPI_GPIO_IMPORT_ERROR is not None:
        logger.info(
            f"未检测到 RPi.GPIO，跳过状态指示器初始化: {_RPI_GPIO_IMPORT_ERROR}"
        )
```

Replace the existing inline startup block that calls `GPIO.setup(25, GPIO.OUT)` and `GPIO.output(25, GPIO.HIGH)` with:

```python
if __name__ == "__main__":
    initialize_status_gpio()

    app = QApplication(sys.argv)
```

This removes the old BCM25-as-green-light behavior and makes BCM26 the only output driven high at launch.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `pytest tests/test_status_gpio.py tests/test_gui_app_gpio.py -v`
Expected: PASS with `4 passed`.

- [ ] **Step 5: Run the regression suite**

Run: `pytest -q`
Expected: PASS; existing QML tests may report intentional skips when a display-capable Qt environment is unavailable.

- [ ] **Step 6: Commit**

```bash
git add src/voc_app/gui/app.py tests/test_gui_app_gpio.py
git commit -m "feat: initialize green status light at startup"
```

## Self-Review

- Spec coverage: Task 1 implements the BCM14/7/25/26 mapping and the required LOW-to-green-HIGH order. Task 2 preserves the WSL2 skip behavior, catches GPIO errors, invokes initialization before QApplication creation, and removes the old BCM25 output-high startup code.
- Placeholder scan: no incomplete steps or unspecified tests remain.
- Type consistency: Task 1 defines `initialize_status_outputs(gpio: Any) -> None`; Task 2 imports and calls that exact function. Task 2 defines `initialize_status_gpio() -> None`, which the main block and its tests use.
