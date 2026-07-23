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
