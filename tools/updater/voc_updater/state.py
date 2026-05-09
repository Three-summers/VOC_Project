from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class UpdateStateWriter:
    def __init__(self, state_file: str | Path, log_file: str | Path) -> None:
        self.state_file = Path(state_file)
        self.log_file = Path(log_file)

    def write_status(
        self,
        loadport_version: str,
        update_state: str,
        update_message: str,
    ) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "loadport_version": loadport_version,
            "update_state": update_state,
            "update_message": update_message,
        }
        self.state_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def log(self, message: str) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat(timespec="seconds")
        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} {message}\n")
