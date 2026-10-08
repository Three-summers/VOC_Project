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
        target_version: str | None = None,
    ) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "loadport_version": loadport_version,
            "update_state": update_state,
            "update_message": update_message,
        }
        # 目标版本与实际运行版本可能不同（例如回滚后）。分开记录，界面才能
        # 显示"实际运行版本"，而不是把包版本当成当前版本（R29）。
        if target_version is not None:
            payload["loadport_target_version"] = target_version
        self.state_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def log(self, message: str) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat(timespec="seconds")
        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} {message}\n")
