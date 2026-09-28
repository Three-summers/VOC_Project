from typing import Any


STATUS_OUTPUT_PINS: dict[str, int] = {
    "buzzer": 14,
    "red": 7,
    "yellow": 26,
    "green": 25,
}

# LEDs are active-low (LOW = on). Buzzer is active-high (HIGH = on).
LED_PIN_NAMES: tuple[str, ...] = ("red", "yellow", "green")


def initialize_status_outputs(gpio: Any) -> None:
    """Configure status outputs with only the green LED enabled.

    - LEDs: active-low (HIGH = off, LOW = on)
    - Buzzer: active-high (LOW = off, HIGH = on); starts LOW
    """
    gpio.setmode(gpio.BCM)

    buzzer_pin = STATUS_OUTPUT_PINS["buzzer"]
    gpio.setup(buzzer_pin, gpio.OUT, initial=gpio.LOW)
    gpio.output(buzzer_pin, gpio.LOW)

    for name in LED_PIN_NAMES:
        pin = STATUS_OUTPUT_PINS[name]
        gpio.setup(pin, gpio.OUT, initial=gpio.HIGH)
        gpio.output(pin, gpio.HIGH)

    gpio.output(STATUS_OUTPUT_PINS["green"], gpio.LOW)
