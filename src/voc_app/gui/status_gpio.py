from typing import Any


STATUS_OUTPUT_PINS: dict[str, int] = {
    "buzzer": 14,
    "red": 7,
    "yellow": 25,
    "green": 26,
}

# LEDs are active-low (LOW = on). Buzzer default (idle) level is HIGH after the
# hardware revision; it is no longer driven LOW at startup.
LED_PIN_NAMES: tuple[str, ...] = ("red", "yellow", "green")


def initialize_status_outputs(gpio: Any) -> None:
    """Configure status outputs with only the green LED enabled.

    - LEDs: active-low (HIGH = off, LOW = on)
    - Buzzer: default level HIGH (idle/silent); the old board idled LOW
    """
    gpio.setmode(gpio.BCM)

    buzzer_pin = STATUS_OUTPUT_PINS["buzzer"]
    gpio.setup(buzzer_pin, gpio.OUT, initial=gpio.HIGH)
    gpio.output(buzzer_pin, gpio.HIGH)

    for name in LED_PIN_NAMES:
        pin = STATUS_OUTPUT_PINS[name]
        gpio.setup(pin, gpio.OUT, initial=gpio.HIGH)
        gpio.output(pin, gpio.HIGH)

    gpio.output(STATUS_OUTPUT_PINS["green"], gpio.LOW)
