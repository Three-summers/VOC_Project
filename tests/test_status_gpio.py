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
