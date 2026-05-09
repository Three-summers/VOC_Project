from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


class UpdateStatusController(QObject):
    statusChanged = Signal()

    def __init__(
        self,
        state_file: str | Path,
        loadport_version: str,
        poll_interval_ms: int = 2000,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._state_file = Path(state_file)
        self._loadport_version = loadport_version or "unknown"
        self._update_state = "idle"
        self._update_message = ""
        self._timer: QTimer | None = None
        if poll_interval_ms > 0:
            self._timer = QTimer(self)
            self._timer.setInterval(int(poll_interval_ms))
            self._timer.timeout.connect(self.refresh)
            self._timer.start()

    @Property(str, notify=statusChanged)
    def loadportVersion(self) -> str:
        return self._loadport_version

    @Property(str, notify=statusChanged)
    def updateState(self) -> str:
        return self._update_state

    @Property(str, notify=statusChanged)
    def updateMessage(self) -> str:
        return self._update_message

    @Property(str, notify=statusChanged)
    def displayText(self) -> str:
        return f"Loadport v{self._loadport_version} | Update: {self._update_state}"

    @Slot()
    def refresh(self) -> None:
        if not self._state_file.exists():
            return
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        loadport_version = str(data.get("loadport_version") or self._loadport_version)
        update_state = str(data.get("update_state") or "idle")
        update_message = str(data.get("update_message") or "")

        if (
            loadport_version == self._loadport_version
            and update_state == self._update_state
            and update_message == self._update_message
        ):
            return

        self._loadport_version = loadport_version
        self._update_state = update_state
        self._update_message = update_message
        self.statusChanged.emit()
