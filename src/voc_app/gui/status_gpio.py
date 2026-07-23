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
        gpio.output(pin, gpio.LOW)
    gpio.output(STATUS_OUTPUT_PINS["green"], gpio.HIGH)
