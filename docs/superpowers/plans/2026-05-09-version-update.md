# Version Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a version update system where a stable independent updater installs Loadport releases, upgrades FOUP PS/PL files, and lets the GUI display only the Loadport version plus update state.

**Architecture:** The GUI project receives only lightweight read-only status/version plumbing. A separate updater under `tools/updater/` performs package validation, version comparison, release symlink switching, FOUP TCP version queries, SSH/SCP command execution, state writing, and dry-run testing. Deployment templates under `deploy/` convert the current `.desktop` autostart into a trigger for a `systemd --user` GUI service so the updater has one lifecycle control surface.

**Tech Stack:** Python 3.11+, PySide6/QML, pytest, stdlib `json`/`tarfile`/`socket`/`subprocess`/`pathlib`, `PyYAML` for updater config, systemd user services, desktop autostart.

---

## File Structure

Create or modify these files:

- Create `src/voc_app/version_info.py`
  - Reads Loadport version from release manifest first, then `pyproject.toml`, then a fallback.
- Create `src/voc_app/gui/update_status.py`
  - Provides `UpdateStatusController(QObject)` for QML.
- Modify `src/voc_app/gui/app.py`
  - Instantiates `UpdateStatusController`, injects it as `updateStatus`, and wires the status file path.
- Modify `src/voc_app/gui/qml/main.qml`
  - Passes `updateStatus` into `TitlePanel`.
- Modify `src/voc_app/gui/qml/TitlePanel.qml`
  - Displays `Loadport vX | Update: state`.
- Create `tools/updater/update.py`
  - CLI entry point.
- Create `tools/updater/voc_updater/config.py`
  - Loads YAML config into dataclasses.
- Create `tools/updater/voc_updater/state.py`
  - Writes compact GUI state and detailed log messages.
- Create `tools/updater/voc_updater/package.py`
  - Extracts and validates `.tar.gz` update packages.
- Create `tools/updater/voc_updater/foup_version.py`
  - Implements TCP length-prefixed `get_version`.
- Create `tools/updater/voc_updater/commands.py`
  - Defines command/upload abstractions for real and fake execution.
- Create `tools/updater/voc_updater/loadport.py`
  - Installs Loadport release and rolls back `current`.
- Create `tools/updater/voc_updater/foup.py`
  - Performs FOUP mount, upload, sync, reboot through command/upload abstraction.
- Create `tools/updater/voc_updater/orchestrator.py`
  - Coordinates package validation, version comparison, installers, and state.
- Create `tools/updater/voc_updater/__init__.py`
  - Package marker.
- Create `deploy/systemd/user/voc-gui.service`
  - User service template for GUI.
- Create `deploy/systemd/user/voc-updater.path`
  - Path watcher template.
- Create `deploy/systemd/user/voc-updater.service`
  - One-shot updater template.
- Create `deploy/autostart/voc-gui.desktop`
  - Desktop autostart template that starts `voc-gui.service`.
- Modify `pyproject.toml`
  - Add `PyYAML>=6.0` to project dependencies.
- Create tests:
  - `tests/test_version_info.py`
  - `tests/test_update_status.py`
  - `tests/test_updater_config.py`
  - `tests/test_updater_package.py`
  - `tests/test_foup_version.py`
  - `tests/test_loadport_installer.py`
  - `tests/test_foup_installer.py`
  - `tests/test_updater_orchestrator.py`
  - `tests/test_deploy_templates.py`

## Task 1: Loadport Version Reader

**Files:**
- Create: `src/voc_app/version_info.py`
- Test: `tests/test_version_info.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_version_info.py`:

```python
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.version_info import get_loadport_version


def test_get_loadport_version_from_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "loadport" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"version": "1.2.3"}), encoding="utf-8")

    assert get_loadport_version(tmp_path) == "1.2.3"


def test_get_loadport_version_from_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "voc-project"\nversion = "0.4.5"\n',
        encoding="utf-8",
    )

    assert get_loadport_version(tmp_path) == "0.4.5"


def test_get_loadport_version_returns_unknown_for_missing_files(tmp_path: Path) -> None:
    assert get_loadport_version(tmp_path) == "unknown"


def test_get_loadport_version_handles_invalid_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "loadport" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{broken", encoding="utf-8")

    assert get_loadport_version(tmp_path) == "unknown"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/test_version_info.py -q
```

Expected: fails because `voc_app.version_info` does not exist.

- [ ] **Step 3: Implement version reader**

Create `src/voc_app/version_info.py`:

```python
from __future__ import annotations

import json
import re
from pathlib import Path


UNKNOWN_VERSION = "unknown"


def _read_manifest_version(root: Path) -> str:
    manifest_path = root / "loadport" / "manifest.json"
    if not manifest_path.exists():
        return ""
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    version = data.get("version", "")
    return str(version).strip() if version else ""


def _read_pyproject_version(root: Path) -> str:
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.exists():
        return ""
    try:
        text = pyproject_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', text)
    if not match:
        return ""
    return match.group(1).strip()


def get_loadport_version(root: str | Path | None = None) -> str:
    project_root = Path(root).resolve() if root is not None else Path.cwd().resolve()
    return (
        _read_manifest_version(project_root)
        or _read_pyproject_version(project_root)
        or UNKNOWN_VERSION
    )
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
python -m pytest tests/test_version_info.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/voc_app/version_info.py tests/test_version_info.py
git commit -m "feat: add loadport version reader"
```

## Task 2: GUI Update Status Controller

**Files:**
- Create: `src/voc_app/gui/update_status.py`
- Test: `tests/test_update_status.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_update_status.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/test_update_status.py -q
```

Expected: fails because `voc_app.gui.update_status` does not exist.

- [ ] **Step 3: Implement controller**

Create `src/voc_app/gui/update_status.py`:

```python
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
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
python -m pytest tests/test_update_status.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/voc_app/gui/update_status.py tests/test_update_status.py
git commit -m "feat: add update status controller"
```

## Task 3: Wire Version Status Into QML Title Bar

**Files:**
- Modify: `src/voc_app/gui/app.py`
- Modify: `src/voc_app/gui/qml/main.qml`
- Modify: `src/voc_app/gui/qml/TitlePanel.qml`
- Test: `tests/test_qml_components.py`

- [ ] **Step 1: Add QML/text tests**

Append these tests to `tests/test_qml_components.py`:

```python
class TestTitlePanelUpdateStatus(unittest.TestCase):
    def setUp(self):
        self.title_panel_path = (
            ROOT_DIR / "src" / "voc_app" / "gui" / "qml" / "TitlePanel.qml"
        )
        self.main_qml_path = (
            ROOT_DIR / "src" / "voc_app" / "gui" / "qml" / "main.qml"
        )
        self.title_content = self.title_panel_path.read_text(encoding="utf-8")
        self.main_content = self.main_qml_path.read_text(encoding="utf-8")

    def test_title_panel_accepts_update_status_ref(self):
        self.assertIn("property var updateStatusRef: null", self.title_content)
        self.assertIn("updateStatusRef.displayText", self.title_content)

    def test_main_passes_update_status_to_title_panel(self):
        self.assertIn("updateStatusRef:", self.main_content)
        self.assertIn('typeof updateStatus !== "undefined"', self.main_content)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/test_qml_components.py::TestTitlePanelUpdateStatus -q
```

Expected: fails because QML has not been wired.

- [ ] **Step 3: Modify Python app injection**

In `src/voc_app/gui/app.py`, add imports near existing GUI imports:

```python
from voc_app.version_info import get_loadport_version
from voc_app.gui.update_status import UpdateStatusController
```

After `alarm_store` is injected, add:

```python
    update_state_file = Path(
        os.environ.get(
            "VOC_UPDATE_STATE_FILE",
            str((PROJECT_ROOT.parent / "state" / "update_status.json").resolve()),
        )
    )
    update_status = UpdateStatusController(
        state_file=update_state_file,
        loadport_version=get_loadport_version(PROJECT_ROOT),
    )
    update_status.refresh()
    engine.rootContext().setContextProperty("updateStatus", update_status)
```

Keep `update_status` in local scope for the lifetime of the application, like the existing `alarm_store` and `foup_acquisition` objects.

- [ ] **Step 4: Modify `main.qml`**

In `TitlePanel { ... }`, add:

```qml
            updateStatusRef: (typeof updateStatus !== "undefined") ? updateStatus : null
```

- [ ] **Step 5: Modify `TitlePanel.qml`**

Near the other properties, add:

```qml
    property var updateStatusRef: null
```

After the current view frame and before the alarm button, add:

```qml
            Frame {
                visible: titlePanel.updateStatusRef !== null
                background: Rectangle {
                    color: Components.UiTheme.color("panel")
                    radius: Components.UiTheme.radius("md")
                    border.color: Components.UiTheme.color("outline")
                }
                padding: Components.UiTheme.spacing("md")
                Text {
                    text: titlePanel.updateStatusRef ? titlePanel.updateStatusRef.displayText : ""
                    color: Components.UiTheme.color("textPrimary")
                    font.pixelSize: Components.UiTheme.fontSize("subtitle")
                    elide: Text.ElideRight
                    Layout.maximumWidth: 320 * Components.UiTheme.controlScale
                }
            }
```

- [ ] **Step 6: Run targeted tests**

Run:

```bash
python -m pytest tests/test_update_status.py tests/test_version_info.py tests/test_qml_components.py::TestTitlePanelUpdateStatus -q
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/voc_app/gui/app.py src/voc_app/gui/qml/main.qml src/voc_app/gui/qml/TitlePanel.qml tests/test_qml_components.py
git commit -m "feat: show loadport update status in title bar"
```

## Task 4: Updater Config And State Writer

**Files:**
- Modify: `pyproject.toml`
- Create: `tools/updater/voc_updater/__init__.py`
- Create: `tools/updater/voc_updater/config.py`
- Create: `tools/updater/voc_updater/state.py`
- Test: `tests/test_updater_config.py`

- [ ] **Step 1: Add failing tests**

Create `tests/test_updater_config.py`:

```python
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.config import load_config
from voc_updater.state import UpdateStateWriter


def test_load_config_reads_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
paths:
  base_dir: /opt/voc
  updates_dir: /opt/voc/updates
  work_dir: /opt/voc/work
  releases_dir: /opt/voc/releases
  current_link: /opt/voc/current
  state_file: /opt/voc/state/update_status.json
  log_file: /opt/voc/state/update.log
services:
  gui_service: voc-gui.service
  systemctl_scope: user
python:
  executable: /opt/voc/.venv/bin/python
foup:
  host: 192.168.1.50
  port: 65432
  ssh_user: root
  ssh_key: /opt/voc/updater/id_rsa
  remote_mount_device: /dev/mmcblk1p1
  remote_mount_point: /tmp
  remote_run_path: /tmp/run
  remote_pl_path: /tmp/design_1_wrapper.bit.bin
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert str(config.paths.base_dir) == "/opt/voc"
    assert config.services.gui_service == "voc-gui.service"
    assert config.services.systemctl_scope == "user"
    assert config.foup.port == 65432
    assert str(config.foup.remote_run_path) == "/tmp/run"


def test_state_writer_writes_compact_status_and_log(tmp_path: Path) -> None:
    state_file = tmp_path / "state" / "update_status.json"
    log_file = tmp_path / "state" / "update.log"
    writer = UpdateStateWriter(state_file=state_file, log_file=log_file)

    writer.write_status("1.2.3", "running", "Installing")
    writer.log("message one")

    data = json.loads(state_file.read_text(encoding="utf-8"))
    assert data == {
        "loadport_version": "1.2.3",
        "update_state": "running",
        "update_message": "Installing",
    }
    assert "message one" in log_file.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/test_updater_config.py -q
```

Expected: fails because `voc_updater` does not exist.

- [ ] **Step 3: Add dependency**

In `pyproject.toml`, add `PyYAML>=6.0` to `[project].dependencies`:

```toml
dependencies = [
    "PySide6>=6.6.0",
    "numpy>=1.24.0",
    "pyserial>=3.5",
    "PyYAML>=6.0",
]
```

- [ ] **Step 4: Implement config and state modules**

Create `tools/updater/voc_updater/__init__.py`:

```python
"""Independent VOC updater package."""
```

Create `tools/updater/voc_updater/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PathsConfig:
    base_dir: Path
    updates_dir: Path
    work_dir: Path
    releases_dir: Path
    current_link: Path
    state_file: Path
    log_file: Path


@dataclass(frozen=True)
class ServicesConfig:
    gui_service: str
    systemctl_scope: str


@dataclass(frozen=True)
class PythonConfig:
    executable: Path


@dataclass(frozen=True)
class FoupConfig:
    host: str
    port: int
    ssh_user: str
    ssh_key: Path
    remote_mount_device: str
    remote_mount_point: Path
    remote_run_path: Path
    remote_pl_path: Path


@dataclass(frozen=True)
class UpdaterConfig:
    paths: PathsConfig
    services: ServicesConfig
    python: PythonConfig
    foup: FoupConfig


def _required(mapping: dict[str, Any], key: str) -> Any:
    if key not in mapping or mapping[key] in (None, ""):
        raise ValueError(f"missing required config key: {key}")
    return mapping[key]


def load_config(path: str | Path) -> UpdaterConfig:
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    paths = _required(data, "paths")
    services = _required(data, "services")
    python = _required(data, "python")
    foup = _required(data, "foup")
    return UpdaterConfig(
        paths=PathsConfig(
            base_dir=Path(_required(paths, "base_dir")),
            updates_dir=Path(_required(paths, "updates_dir")),
            work_dir=Path(_required(paths, "work_dir")),
            releases_dir=Path(_required(paths, "releases_dir")),
            current_link=Path(_required(paths, "current_link")),
            state_file=Path(_required(paths, "state_file")),
            log_file=Path(_required(paths, "log_file")),
        ),
        services=ServicesConfig(
            gui_service=str(_required(services, "gui_service")),
            systemctl_scope=str(services.get("systemctl_scope", "user")),
        ),
        python=PythonConfig(executable=Path(_required(python, "executable"))),
        foup=FoupConfig(
            host=str(_required(foup, "host")),
            port=int(_required(foup, "port")),
            ssh_user=str(_required(foup, "ssh_user")),
            ssh_key=Path(_required(foup, "ssh_key")),
            remote_mount_device=str(_required(foup, "remote_mount_device")),
            remote_mount_point=Path(_required(foup, "remote_mount_point")),
            remote_run_path=Path(_required(foup, "remote_run_path")),
            remote_pl_path=Path(_required(foup, "remote_pl_path")),
        ),
    )
```

Create `tools/updater/voc_updater/state.py`:

```python
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
```

- [ ] **Step 5: Run tests and verify pass**

Run:

```bash
python -m pytest tests/test_updater_config.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tools/updater/voc_updater tests/test_updater_config.py
git commit -m "feat: add updater config and state writer"
```

## Task 5: Update Package Reader

**Files:**
- Create: `tools/updater/voc_updater/package.py`
- Test: `tests/test_updater_package.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_updater_package.py`:

```python
import json
import sys
import tarfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.package import UpdatePackageReader


def _write_package(source: Path, package_path: Path) -> None:
    with tarfile.open(package_path, "w:gz") as tar:
        tar.add(source, arcname=".")


def _valid_source(root: Path) -> None:
    loadport = root / "loadport"
    foup = root / "foup"
    (loadport / "app" / "src" / "voc_app" / "gui").mkdir(parents=True)
    (foup / "ps").mkdir(parents=True)
    (foup / "pl").mkdir(parents=True)
    (loadport / "app" / "src" / "voc_app" / "gui" / "app.py").write_text(
        "print('app')\n",
        encoding="utf-8",
    )
    (foup / "ps" / "run").write_bytes(b"run")
    (foup / "pl" / "design_1_wrapper.bit.bin").write_bytes(b"bit")
    (loadport / "manifest.json").write_text(
        json.dumps({"component": "loadport", "version": "1.2.3"}),
        encoding="utf-8",
    )
    (foup / "manifest.json").write_text(
        json.dumps(
            {
                "component": "foup",
                "ps_version": "2.0.1",
                "pl_version": "2026.05.09",
                "ps_file": "ps/run",
                "pl_file": "pl/design_1_wrapper.bit.bin",
            }
        ),
        encoding="utf-8",
    )


def test_package_reader_extracts_and_validates(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _valid_source(source)
    package_path = tmp_path / "voc-update.tar.gz"
    _write_package(source, package_path)

    result = UpdatePackageReader(tmp_path / "work").read(package_path)

    assert result.loadport_version == "1.2.3"
    assert result.foup_ps_version == "2.0.1"
    assert result.foup_pl_version == "2026.05.09"
    assert result.loadport_app_dir.exists()
    assert result.foup_ps_file.exists()
    assert result.foup_pl_file.exists()


def test_package_reader_rejects_missing_run(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _valid_source(source)
    (source / "foup" / "ps" / "run").unlink()
    package_path = tmp_path / "voc-update.tar.gz"
    _write_package(source, package_path)

    try:
        UpdatePackageReader(tmp_path / "work").read(package_path)
    except ValueError as exc:
        assert "missing FOUP PS file" in str(exc)
    else:
        raise AssertionError("expected ValueError")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/test_updater_package.py -q
```

Expected: fails because `voc_updater.package` does not exist.

- [ ] **Step 3: Implement package reader**

Create `tools/updater/voc_updater/package.py`:

```python
from __future__ import annotations

import json
import tarfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UpdatePackage:
    package_path: Path
    extract_dir: Path
    loadport_manifest: dict
    foup_manifest: dict
    loadport_app_dir: Path
    foup_ps_file: Path
    foup_pl_file: Path

    @property
    def loadport_version(self) -> str:
        return str(self.loadport_manifest["version"])

    @property
    def foup_ps_version(self) -> str:
        return str(self.foup_manifest["ps_version"])

    @property
    def foup_pl_version(self) -> str:
        return str(self.foup_manifest["pl_version"])


class UpdatePackageReader:
    def __init__(self, work_dir: str | Path) -> None:
        self.work_dir = Path(work_dir)

    def read(self, package_path: str | Path) -> UpdatePackage:
        source_package = Path(package_path)
        if not source_package.exists():
            raise ValueError(f"package does not exist: {source_package}")
        extract_dir = self.work_dir / source_package.stem.replace(".tar", "")
        if extract_dir.exists():
            raise ValueError(f"work directory already exists: {extract_dir}")
        extract_dir.mkdir(parents=True, exist_ok=False)
        with tarfile.open(source_package, "r:gz") as tar:
            tar.extractall(extract_dir)

        root = extract_dir
        loadport_manifest = self._read_json(root / "loadport" / "manifest.json")
        foup_manifest = self._read_json(root / "foup" / "manifest.json")

        if loadport_manifest.get("component") != "loadport":
            raise ValueError("invalid loadport manifest component")
        if foup_manifest.get("component") != "foup":
            raise ValueError("invalid foup manifest component")
        if not loadport_manifest.get("version"):
            raise ValueError("missing loadport version")
        if not foup_manifest.get("ps_version"):
            raise ValueError("missing FOUP PS version")
        if not foup_manifest.get("pl_version"):
            raise ValueError("missing FOUP PL version")

        loadport_app_dir = root / "loadport" / "app"
        if not (loadport_app_dir / "src" / "voc_app" / "gui" / "app.py").exists():
            raise ValueError("missing Loadport app entry file")

        foup_root = root / "foup"
        ps_file = foup_root / str(foup_manifest.get("ps_file", "ps/run"))
        pl_file = foup_root / str(
            foup_manifest.get("pl_file", "pl/design_1_wrapper.bit.bin")
        )
        if not ps_file.exists():
            raise ValueError("missing FOUP PS file")
        if not pl_file.exists():
            raise ValueError("missing FOUP PL file")

        return UpdatePackage(
            package_path=source_package,
            extract_dir=extract_dir,
            loadport_manifest=loadport_manifest,
            foup_manifest=foup_manifest,
            loadport_app_dir=loadport_app_dir,
            foup_ps_file=ps_file,
            foup_pl_file=pl_file,
        )

    @staticmethod
    def _read_json(path: Path) -> dict:
        if not path.exists():
            raise ValueError(f"missing manifest: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON manifest: {path}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"manifest must be a JSON object: {path}")
        return data
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
python -m pytest tests/test_updater_package.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add tools/updater/voc_updater/package.py tests/test_updater_package.py
git commit -m "feat: validate update packages"
```

## Task 6: FOUP TCP Version Client

**Files:**
- Create: `tools/updater/voc_updater/foup_version.py`
- Test: `tests/test_foup_version.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_foup_version.py`:

```python
import json
import socket
import struct
import sys
import threading
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.foup_version import FoupVersionClient


def _recv_msg(conn: socket.socket) -> str:
    header = conn.recv(4)
    size = struct.unpack(">I", header)[0]
    return conn.recv(size).decode("utf-8")


def _send_msg(conn: socket.socket, text: str) -> None:
    body = text.encode("utf-8")
    conn.sendall(struct.pack(">I", len(body)) + body)


def test_foup_version_client_sends_get_version_and_parses_json() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    received = []

    def run_server() -> None:
        conn, _ = server.accept()
        with conn:
            received.append(_recv_msg(conn))
            _send_msg(
                conn,
                json.dumps({"ps_version": "2.0.1", "pl_version": "2026.05.09"}),
            )
        server.close()

    thread = threading.Thread(target=run_server)
    thread.start()

    version = FoupVersionClient("127.0.0.1", port, timeout=2.0).get_version()

    thread.join(timeout=2)
    assert received == ["get_version"]
    assert version.ps_version == "2.0.1"
    assert version.pl_version == "2026.05.09"


def test_foup_version_client_rejects_missing_fields() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def run_server() -> None:
        conn, _ = server.accept()
        with conn:
            _recv_msg(conn)
            _send_msg(conn, json.dumps({"ps_version": "2.0.1"}))
        server.close()

    thread = threading.Thread(target=run_server)
    thread.start()

    try:
        FoupVersionClient("127.0.0.1", port, timeout=2.0).get_version()
    except ValueError as exc:
        assert "pl_version" in str(exc)
    else:
        raise AssertionError("expected ValueError")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/test_foup_version.py -q
```

Expected: fails because `voc_updater.foup_version` does not exist.

- [ ] **Step 3: Implement FOUP version client**

Create `tools/updater/voc_updater/foup_version.py`:

```python
from __future__ import annotations

import json
import socket
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class FoupVersion:
    ps_version: str
    pl_version: str


class FoupVersionClient:
    def __init__(self, host: str, port: int, timeout: float = 5.0) -> None:
        self.host = host
        self.port = int(port)
        self.timeout = float(timeout)

    def get_version(self) -> FoupVersion:
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.settimeout(self.timeout)
            self._send_msg(sock, "get_version")
            response = self._recv_msg(sock)
        try:
            payload = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError("FOUP get_version response is not JSON") from exc
        ps_version = str(payload.get("ps_version") or "")
        pl_version = str(payload.get("pl_version") or "")
        if not ps_version:
            raise ValueError("FOUP get_version response missing ps_version")
        if not pl_version:
            raise ValueError("FOUP get_version response missing pl_version")
        return FoupVersion(ps_version=ps_version, pl_version=pl_version)

    @staticmethod
    def _send_msg(sock: socket.socket, text: str) -> None:
        body = text.encode("utf-8")
        sock.sendall(struct.pack(">I", len(body)) + body)

    @staticmethod
    def _recv_msg(sock: socket.socket) -> str:
        header = FoupVersionClient._recv_exact(sock, 4)
        size = struct.unpack(">I", header)[0]
        body = FoupVersionClient._recv_exact(sock, size)
        return body.decode("utf-8")

    @staticmethod
    def _recv_exact(sock: socket.socket, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            chunk = sock.recv(size - len(chunks))
            if not chunk:
                raise ConnectionError("socket closed while reading FOUP response")
            chunks.extend(chunk)
        return bytes(chunks)
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
python -m pytest tests/test_foup_version.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add tools/updater/voc_updater/foup_version.py tests/test_foup_version.py
git commit -m "feat: add foup version client"
```

## Task 7: Command Runner And Loadport Installer

**Files:**
- Create: `tools/updater/voc_updater/commands.py`
- Create: `tools/updater/voc_updater/loadport.py`
- Test: `tests/test_loadport_installer.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_loadport_installer.py`:

```python
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.commands import FakeCommandRunner
from voc_updater.loadport import LoadportInstaller


def _make_app(path: Path, marker: str) -> None:
    app = path / "src" / "voc_app" / "gui"
    app.mkdir(parents=True)
    (app / "app.py").write_text(marker, encoding="utf-8")


def test_loadport_installer_switches_current_symlink(tmp_path: Path) -> None:
    releases = tmp_path / "releases"
    current = tmp_path / "current"
    old_release = releases / "loadport-1.0.0"
    _make_app(old_release, "old")
    current.symlink_to(old_release, target_is_directory=True)
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")
    runner = FakeCommandRunner()

    installer = LoadportInstaller(
        releases_dir=releases,
        current_link=current,
        gui_service="voc-gui.service",
        systemctl_scope="user",
        runner=runner,
    )

    installer.install(version="1.2.3", app_dir=new_app)

    assert current.resolve() == (releases / "loadport-1.2.3").resolve()
    assert (current / "src" / "voc_app" / "gui" / "app.py").read_text() == "new"
    assert runner.commands == [
        ["systemctl", "--user", "stop", "voc-gui.service"],
        ["systemctl", "--user", "start", "voc-gui.service"],
        ["systemctl", "--user", "is-active", "voc-gui.service"],
    ]


def test_loadport_installer_rolls_back_when_start_check_fails(tmp_path: Path) -> None:
    releases = tmp_path / "releases"
    current = tmp_path / "current"
    old_release = releases / "loadport-1.0.0"
    _make_app(old_release, "old")
    current.symlink_to(old_release, target_is_directory=True)
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")
    runner = FakeCommandRunner(fail_on=[["systemctl", "--user", "is-active", "voc-gui.service"]])

    installer = LoadportInstaller(
        releases_dir=releases,
        current_link=current,
        gui_service="voc-gui.service",
        systemctl_scope="user",
        runner=runner,
    )

    try:
        installer.install(version="1.2.3", app_dir=new_app)
    except RuntimeError as exc:
        assert "GUI service did not become active" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    assert current.resolve() == old_release.resolve()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/test_loadport_installer.py -q
```

Expected: fails because command/loadport modules do not exist.

- [ ] **Step 3: Implement command runner**

Create `tools/updater/voc_updater/commands.py`:

```python
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    def run(self, args: list[str], timeout: int = 60) -> CommandResult:
        completed = subprocess.run(
            args,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return CommandResult(
            args=args,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def upload(self, local_path: Path, remote_path: str) -> CommandResult:
        args = ["scp", str(local_path), remote_path]
        return self.run(args, timeout=300)


class FakeCommandRunner(CommandRunner):
    def __init__(self, fail_on: list[list[str]] | None = None) -> None:
        self.commands: list[list[str]] = []
        self.uploads: list[tuple[Path, str]] = []
        self.fail_on = fail_on or []

    def run(self, args: list[str], timeout: int = 60) -> CommandResult:
        self.commands.append(list(args))
        returncode = 1 if args in self.fail_on else 0
        return CommandResult(args=list(args), returncode=returncode, stdout="", stderr="")

    def upload(self, local_path: Path, remote_path: str) -> CommandResult:
        self.uploads.append((Path(local_path), remote_path))
        args = ["upload", str(local_path), remote_path]
        returncode = 1 if args in self.fail_on else 0
        return CommandResult(args=args, returncode=returncode, stdout="", stderr="")


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copytree(source, destination)
```

- [ ] **Step 4: Implement Loadport installer**

Create `tools/updater/voc_updater/loadport.py`:

```python
from __future__ import annotations

import os
from pathlib import Path

from .commands import CommandRunner, copy_tree


class LoadportInstaller:
    def __init__(
        self,
        releases_dir: str | Path,
        current_link: str | Path,
        gui_service: str,
        systemctl_scope: str,
        runner: CommandRunner,
    ) -> None:
        self.releases_dir = Path(releases_dir)
        self.current_link = Path(current_link)
        self.gui_service = gui_service
        self.systemctl_scope = systemctl_scope
        self.runner = runner

    def install(self, version: str, app_dir: str | Path) -> Path:
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        old_target = self.current_link.resolve() if self.current_link.exists() else None
        target = self.releases_dir / f"loadport-{version}"
        if not target.exists():
            copy_tree(Path(app_dir), target)

        self._systemctl("stop")
        self._switch_current(target)
        self._systemctl("start")
        active = self._systemctl("is-active")
        if active.returncode != 0:
            if old_target is not None:
                self._switch_current(old_target)
                self._systemctl("start")
            raise RuntimeError("GUI service did not become active after upgrade")
        return target

    def _systemctl(self, action: str):
        args = ["systemctl"]
        if self.systemctl_scope == "user":
            args.append("--user")
        args.extend([action, self.gui_service])
        return self.runner.run(args)

    def _switch_current(self, target: Path) -> None:
        tmp_link = self.current_link.with_name(self.current_link.name + ".next")
        if tmp_link.exists() or tmp_link.is_symlink():
            tmp_link.unlink()
        tmp_link.symlink_to(target, target_is_directory=True)
        os.replace(tmp_link, self.current_link)
```

- [ ] **Step 5: Run tests and verify pass**

Run:

```bash
python -m pytest tests/test_loadport_installer.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add tools/updater/voc_updater/commands.py tools/updater/voc_updater/loadport.py tests/test_loadport_installer.py
git commit -m "feat: add loadport release installer"
```

## Task 8: FOUP Installer

**Files:**
- Create: `tools/updater/voc_updater/foup.py`
- Test: `tests/test_foup_installer.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_foup_installer.py`:

```python
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.commands import FakeCommandRunner
from voc_updater.foup import FoupInstaller


def test_foup_installer_updates_only_changed_ps_file(tmp_path: Path) -> None:
    run_file = tmp_path / "run"
    pl_file = tmp_path / "design_1_wrapper.bit.bin"
    run_file.write_bytes(b"run")
    pl_file.write_bytes(b"pl")
    runner = FakeCommandRunner()

    installer = FoupInstaller(
        host="192.168.1.50",
        ssh_user="root",
        ssh_key=tmp_path / "id_rsa",
        mount_device="/dev/mmcblk1p1",
        mount_point="/tmp",
        remote_run_path="/tmp/run",
        remote_pl_path="/tmp/design_1_wrapper.bit.bin",
        runner=runner,
    )

    installer.upgrade(
        ps_changed=True,
        pl_changed=False,
        local_run_file=run_file,
        local_pl_file=pl_file,
    )

    assert runner.commands == [
        ["ssh", "-i", str(tmp_path / "id_rsa"), "root@192.168.1.50", "mount /dev/mmcblk1p1 /tmp"],
        ["ssh", "-i", str(tmp_path / "id_rsa"), "root@192.168.1.50", "sync"],
        ["ssh", "-i", str(tmp_path / "id_rsa"), "root@192.168.1.50", "reboot"],
    ]
    assert runner.uploads == [(run_file, "root@192.168.1.50:/tmp/run")]


def test_foup_installer_skips_when_no_files_changed(tmp_path: Path) -> None:
    runner = FakeCommandRunner()
    installer = FoupInstaller(
        host="192.168.1.50",
        ssh_user="root",
        ssh_key=tmp_path / "id_rsa",
        mount_device="/dev/mmcblk1p1",
        mount_point="/tmp",
        remote_run_path="/tmp/run",
        remote_pl_path="/tmp/design_1_wrapper.bit.bin",
        runner=runner,
    )

    installer.upgrade(
        ps_changed=False,
        pl_changed=False,
        local_run_file=tmp_path / "run",
        local_pl_file=tmp_path / "design_1_wrapper.bit.bin",
    )

    assert runner.commands == []
    assert runner.uploads == []
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/test_foup_installer.py -q
```

Expected: fails because `voc_updater.foup` does not exist.

- [ ] **Step 3: Implement FOUP installer**

Create `tools/updater/voc_updater/foup.py`:

```python
from __future__ import annotations

from pathlib import Path

from .commands import CommandRunner


class FoupInstaller:
    def __init__(
        self,
        host: str,
        ssh_user: str,
        ssh_key: str | Path,
        mount_device: str,
        mount_point: str | Path,
        remote_run_path: str | Path,
        remote_pl_path: str | Path,
        runner: CommandRunner,
    ) -> None:
        self.host = host
        self.ssh_user = ssh_user
        self.ssh_key = Path(ssh_key)
        self.mount_device = mount_device
        self.mount_point = Path(mount_point)
        self.remote_run_path = Path(remote_run_path)
        self.remote_pl_path = Path(remote_pl_path)
        self.runner = runner

    def upgrade(
        self,
        ps_changed: bool,
        pl_changed: bool,
        local_run_file: str | Path,
        local_pl_file: str | Path,
    ) -> None:
        if not ps_changed and not pl_changed:
            return
        self._run_remote(f"mount {self.mount_device} {self.mount_point}")
        if ps_changed:
            self._upload(Path(local_run_file), self.remote_run_path)
        if pl_changed:
            self._upload(Path(local_pl_file), self.remote_pl_path)
        self._run_remote("sync")
        self._run_remote("reboot")

    def _remote(self) -> str:
        return f"{self.ssh_user}@{self.host}"

    def _run_remote(self, command: str) -> None:
        args = ["ssh", "-i", str(self.ssh_key), self._remote(), command]
        result = self.runner.run(args, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"remote command failed: {command}")

    def _upload(self, local_path: Path, remote_path: Path) -> None:
        result = self.runner.upload(local_path, f"{self._remote()}:{remote_path}")
        if result.returncode != 0:
            raise RuntimeError(f"upload failed: {local_path} -> {remote_path}")
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
python -m pytest tests/test_foup_installer.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add tools/updater/voc_updater/foup.py tests/test_foup_installer.py
git commit -m "feat: add foup installer"
```

## Task 9: Orchestrator And CLI

**Files:**
- Create: `tools/updater/voc_updater/orchestrator.py`
- Create: `tools/updater/update.py`
- Test: `tests/test_updater_orchestrator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_updater_orchestrator.py`:

```python
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.foup_version import FoupVersion
from voc_updater.orchestrator import UpdateOrchestrator


class FakePackage:
    loadport_version = "1.2.3"
    foup_ps_version = "2.0.1"
    foup_pl_version = "2026.05.09"
    loadport_app_dir = Path("/package/loadport/app")
    foup_ps_file = Path("/package/foup/ps/run")
    foup_pl_file = Path("/package/foup/pl/design_1_wrapper.bit.bin")


class FakeReader:
    def read(self, package_path):
        self.package_path = package_path
        return FakePackage()


class FakeLoadportVersion:
    def __init__(self, version):
        self.version = version

    def __call__(self):
        return self.version


class FakeFoupClient:
    def __init__(self, ps_version, pl_version):
        self.version = FoupVersion(ps_version=ps_version, pl_version=pl_version)

    def get_version(self):
        return self.version


class FakeLoadportInstaller:
    def __init__(self):
        self.calls = []

    def install(self, version, app_dir):
        self.calls.append((version, app_dir))


class FakeFoupInstaller:
    def __init__(self):
        self.calls = []

    def upgrade(self, ps_changed, pl_changed, local_run_file, local_pl_file):
        self.calls.append((ps_changed, pl_changed, local_run_file, local_pl_file))


def test_orchestrator_skips_when_versions_match(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    log_file = tmp_path / "update.log"
    loadport_installer = FakeLoadportInstaller()
    foup_installer = FakeFoupInstaller()
    orchestrator = UpdateOrchestrator(
        reader=FakeReader(),
        current_loadport_version=FakeLoadportVersion("1.2.3"),
        foup_client=FakeFoupClient("2.0.1", "2026.05.09"),
        loadport_installer=loadport_installer,
        foup_installer=foup_installer,
        state_file=state_file,
        log_file=log_file,
    )

    orchestrator.run(tmp_path / "package.tar.gz")

    assert loadport_installer.calls == []
    assert foup_installer.calls == []
    assert json.loads(state_file.read_text())["update_state"] == "skipped"


def test_orchestrator_installs_changed_components(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    log_file = tmp_path / "update.log"
    loadport_installer = FakeLoadportInstaller()
    foup_installer = FakeFoupInstaller()
    orchestrator = UpdateOrchestrator(
        reader=FakeReader(),
        current_loadport_version=FakeLoadportVersion("1.0.0"),
        foup_client=FakeFoupClient("2.0.0", "2026.05.01"),
        loadport_installer=loadport_installer,
        foup_installer=foup_installer,
        state_file=state_file,
        log_file=log_file,
    )

    orchestrator.run(tmp_path / "package.tar.gz")

    assert loadport_installer.calls == [("1.2.3", Path("/package/loadport/app"))]
    assert foup_installer.calls == [
        (
            True,
            True,
            Path("/package/foup/ps/run"),
            Path("/package/foup/pl/design_1_wrapper.bit.bin"),
        )
    ]
    assert json.loads(state_file.read_text())["update_state"] == "succeeded"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/test_updater_orchestrator.py -q
```

Expected: fails because orchestrator module does not exist.

- [ ] **Step 3: Implement orchestrator**

Create `tools/updater/voc_updater/orchestrator.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Callable

from .state import UpdateStateWriter


class UpdateOrchestrator:
    def __init__(
        self,
        reader,
        current_loadport_version: Callable[[], str],
        foup_client,
        loadport_installer,
        foup_installer,
        state_file: str | Path,
        log_file: str | Path,
    ) -> None:
        self.reader = reader
        self.current_loadport_version = current_loadport_version
        self.foup_client = foup_client
        self.loadport_installer = loadport_installer
        self.foup_installer = foup_installer
        self.state = UpdateStateWriter(state_file=state_file, log_file=log_file)

    def run(self, package_path: str | Path) -> None:
        package = self.reader.read(package_path)
        self.state.write_status(package.loadport_version, "running", "Validating update")
        self.state.log(f"package loaded: {package_path}")

        current_loadport = self.current_loadport_version()
        current_foup = self.foup_client.get_version()

        loadport_changed = current_loadport != package.loadport_version
        ps_changed = current_foup.ps_version != package.foup_ps_version
        pl_changed = current_foup.pl_version != package.foup_pl_version

        if not loadport_changed and not ps_changed and not pl_changed:
            self.state.write_status(package.loadport_version, "skipped", "Versions already match")
            self.state.log("update skipped: all versions match")
            return

        try:
            if loadport_changed:
                self.state.log(
                    f"updating loadport: {current_loadport} -> {package.loadport_version}"
                )
                self.loadport_installer.install(
                    version=package.loadport_version,
                    app_dir=package.loadport_app_dir,
                )
            if ps_changed or pl_changed:
                self.state.log(
                    "updating foup: "
                    f"ps {current_foup.ps_version} -> {package.foup_ps_version}, "
                    f"pl {current_foup.pl_version} -> {package.foup_pl_version}"
                )
                self.foup_installer.upgrade(
                    ps_changed=ps_changed,
                    pl_changed=pl_changed,
                    local_run_file=package.foup_ps_file,
                    local_pl_file=package.foup_pl_file,
                )
        except Exception as exc:
            self.state.write_status(package.loadport_version, "failed", str(exc))
            self.state.log(f"update failed: {exc}")
            raise

        self.state.write_status(package.loadport_version, "succeeded", "Update completed")
        self.state.log("update succeeded")
```

- [ ] **Step 4: Implement CLI**

Create `tools/updater/update.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from voc_updater.commands import CommandRunner
from voc_updater.config import load_config
from voc_updater.foup import FoupInstaller
from voc_updater.foup_version import FoupVersionClient
from voc_updater.loadport import LoadportInstaller
from voc_updater.orchestrator import UpdateOrchestrator
from voc_updater.package import UpdatePackageReader


def _find_package(updates_dir: Path) -> Path:
    packages = sorted(updates_dir.glob("*.tar.gz"), key=lambda path: path.stat().st_mtime)
    if not packages:
        raise FileNotFoundError(f"no update package found in {updates_dir}")
    return packages[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VOC updater")
    parser.add_argument("--config", required=True)
    parser.add_argument("--package")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    package_path = Path(args.package) if args.package else _find_package(config.paths.updates_dir)
    runner = CommandRunner()
    reader = UpdatePackageReader(config.paths.work_dir)
    foup_client = FoupVersionClient(config.foup.host, config.foup.port)
    loadport_installer = LoadportInstaller(
        releases_dir=config.paths.releases_dir,
        current_link=config.paths.current_link,
        gui_service=config.services.gui_service,
        systemctl_scope=config.services.systemctl_scope,
        runner=runner,
    )
    foup_installer = FoupInstaller(
        host=config.foup.host,
        ssh_user=config.foup.ssh_user,
        ssh_key=config.foup.ssh_key,
        mount_device=config.foup.remote_mount_device,
        mount_point=config.foup.remote_mount_point,
        remote_run_path=config.foup.remote_run_path,
        remote_pl_path=config.foup.remote_pl_path,
        runner=runner,
    )

    def current_loadport_version() -> str:
        manifest = config.paths.current_link / "loadport" / "manifest.json"
        if manifest.exists():
            import json

            return str(json.loads(manifest.read_text(encoding="utf-8")).get("version", "unknown"))
        return "unknown"

    orchestrator = UpdateOrchestrator(
        reader=reader,
        current_loadport_version=current_loadport_version,
        foup_client=foup_client,
        loadport_installer=loadport_installer,
        foup_installer=foup_installer,
        state_file=config.paths.state_file,
        log_file=config.paths.log_file,
    )
    orchestrator.run(package_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run orchestrator tests**

Run:

```bash
python -m pytest tests/test_updater_orchestrator.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add tools/updater/update.py tools/updater/voc_updater/orchestrator.py tests/test_updater_orchestrator.py
git commit -m "feat: add updater orchestrator"
```

## Task 10: Systemd And Autostart Templates

**Files:**
- Create: `deploy/systemd/user/voc-gui.service`
- Create: `deploy/systemd/user/voc-updater.path`
- Create: `deploy/systemd/user/voc-updater.service`
- Create: `deploy/autostart/voc-gui.desktop`
- Test: `tests/test_deploy_templates.py`

- [ ] **Step 1: Write failing template tests**

Create `tests/test_deploy_templates.py`:

```python
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_voc_gui_service_uses_current_symlink_and_module_entrypoint() -> None:
    content = (ROOT_DIR / "deploy" / "systemd" / "user" / "voc-gui.service").read_text(
        encoding="utf-8"
    )
    assert "WorkingDirectory=/home/kasp/Project/voc_project/current" in content
    assert "-m voc_app.gui.app" in content
    assert "Restart=on-failure" in content


def test_autostart_desktop_starts_systemd_service_not_python() -> None:
    content = (ROOT_DIR / "deploy" / "autostart" / "voc-gui.desktop").read_text(
        encoding="utf-8"
    )
    assert "Exec=systemctl --user start voc-gui.service" in content
    assert "python" not in content


def test_updater_path_watches_updates_directory() -> None:
    content = (ROOT_DIR / "deploy" / "systemd" / "user" / "voc-updater.path").read_text(
        encoding="utf-8"
    )
    assert "PathExistsGlob=/home/kasp/Project/voc_project/updates/*.tar.gz" in content


def test_updater_service_runs_independent_script() -> None:
    content = (ROOT_DIR / "deploy" / "systemd" / "user" / "voc-updater.service").read_text(
        encoding="utf-8"
    )
    assert "/home/kasp/Project/voc_project/updater/update.py" in content
    assert "--config /home/kasp/Project/voc_project/updater/config.yaml" in content
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python -m pytest tests/test_deploy_templates.py -q
```

Expected: fails because deploy templates do not exist.

- [ ] **Step 3: Add deploy templates**

Create `deploy/systemd/user/voc-gui.service`:

```ini
[Unit]
Description=VOC Loadport GUI
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=/home/kasp/Project/voc_project/current
ExecStart=/home/kasp/Project/voc_project/.venv/bin/python -m voc_app.gui.app
Restart=on-failure
RestartSec=3
Environment=QT_QPA_PLATFORM=wayland

[Install]
WantedBy=default.target
```

Create `deploy/systemd/user/voc-updater.path`:

```ini
[Unit]
Description=Watch VOC update packages

[Path]
PathExistsGlob=/home/kasp/Project/voc_project/updates/*.tar.gz

[Install]
WantedBy=default.target
```

Create `deploy/systemd/user/voc-updater.service`:

```ini
[Unit]
Description=Run VOC updater

[Service]
Type=oneshot
WorkingDirectory=/home/kasp/Project/voc_project/updater
ExecStart=/home/kasp/Project/voc_project/.venv/bin/python /home/kasp/Project/voc_project/updater/update.py --config /home/kasp/Project/voc_project/updater/config.yaml
```

Create `deploy/autostart/voc-gui.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=VOC Loadport GUI
Exec=systemctl --user start voc-gui.service
X-GNOME-Autostart-enabled=true
Terminal=false
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
python -m pytest tests/test_deploy_templates.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add deploy/systemd/user deploy/autostart tests/test_deploy_templates.py
git commit -m "feat: add updater deployment templates"
```

## Task 11: Full Verification

**Files:**
- Modify if failures require fixes:
  - `src/voc_app/version_info.py`
  - `src/voc_app/gui/update_status.py`
  - `src/voc_app/gui/app.py`
  - `src/voc_app/gui/qml/main.qml`
  - `src/voc_app/gui/qml/TitlePanel.qml`
  - `tools/updater/**`
  - `deploy/**`
  - `tests/**`

- [ ] **Step 1: Run all focused update tests**

Run:

```bash
python -m pytest \
  tests/test_version_info.py \
  tests/test_update_status.py \
  tests/test_updater_config.py \
  tests/test_updater_package.py \
  tests/test_foup_version.py \
  tests/test_loadport_installer.py \
  tests/test_foup_installer.py \
  tests/test_updater_orchestrator.py \
  tests/test_deploy_templates.py \
  tests/test_qml_components.py::TestTitlePanelUpdateStatus \
  -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run existing related tests**

Run:

```bash
python -m pytest tests/test_foup_acquisition.py tests/test_socket_client.py tests/test_qml_components.py -q
```

Expected: existing FOUP/socket/QML tests pass.

- [ ] **Step 3: Run full test suite**

Run:

```bash
python -m pytest tests -q
```

Expected: all tests pass. If unrelated existing failures appear, record the failing tests and verify that focused update tests still pass.

- [ ] **Step 4: Review git diff**

Run:

```bash
git status --short
git diff --stat
```

Expected: only files listed in this plan are changed.

- [ ] **Step 5: Commit final fixes**

```bash
git add src tools deploy tests pyproject.toml docs
git commit -m "test: verify version update workflow"
```

## Self-Review

Spec coverage:

- Independent updater: covered by Tasks 4-9.
- Loadport release/current symlink and rollback: covered by Task 7.
- FOUP TCP `get_version`: covered by Task 6.
- FOUP SSH/SCP mount/upload/sync/reboot: covered by Task 8.
- Simplified GUI status display: covered by Tasks 1-3.
- systemd user services and `.desktop` autostart handoff: covered by Task 10.
- WSL2 mock/dry-run posture: covered through fake command runner tests and no real systemctl/mount/reboot in tests.

Placeholder scan:

- The plan contains no unresolved markers or unspecified implementation steps.
- Every task includes exact files, test commands, and expected outcomes.

Type consistency:

- `UpdateStateWriter.write_status(loadport_version, update_state, update_message)` is used consistently by GUI-facing state tests and orchestrator.
- `FoupVersion(ps_version, pl_version)` fields match manifest comparison fields.
- `LoadportInstaller.install(version, app_dir)` is used consistently by tests and orchestrator.
- `FoupInstaller.upgrade(ps_changed, pl_changed, local_run_file, local_pl_file)` is used consistently by tests and orchestrator.
