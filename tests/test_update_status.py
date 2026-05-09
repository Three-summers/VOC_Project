import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.update_status import UpdateStatusController


def test_update_status_initial_values(tmp_path: Path) -> None:
    controller = UpdateStatusController(
        state_file=tmp_path / "missing.json",
        loadport_version="0.1.0",
        poll_interval_ms=0,
    )

    assert controller.loadportVersion == "0.1.0"
    assert controller.updateState == "idle"
    assert controller.updateMessage == ""
    assert controller.displayText == "Loadport v0.1.0 | Update: idle"


def test_update_status_reads_state_file(tmp_path: Path) -> None:
    state_file = tmp_path / "update_status.json"
    state_file.write_text(
        json.dumps(
            {
                "loadport_version": "1.2.3",
                "update_state": "running",
                "update_message": "Installing",
            }
        ),
        encoding="utf-8",
    )

    controller = UpdateStatusController(
        state_file=state_file,
        loadport_version="0.1.0",
        poll_interval_ms=0,
    )
    controller.refresh()

    assert controller.loadportVersion == "1.2.3"
    assert controller.updateState == "running"
    assert controller.updateMessage == "Installing"
    assert controller.displayText == "Loadport v1.2.3 | Update: running"


def test_update_status_ignores_invalid_json(tmp_path: Path) -> None:
    state_file = tmp_path / "update_status.json"
    state_file.write_text("{broken", encoding="utf-8")

    controller = UpdateStatusController(
        state_file=state_file,
        loadport_version="0.1.0",
        poll_interval_ms=0,
    )
    controller.refresh()

    assert controller.loadportVersion == "0.1.0"
    assert controller.updateState == "idle"
