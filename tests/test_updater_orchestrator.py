import json
import sys
from pathlib import Path

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
