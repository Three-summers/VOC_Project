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


class FailingFoupClient:
    def get_version(self):
        raise ConnectionError("foup unreachable")


def test_orchestrator_keeps_loadport_update_when_foup_unreachable(
    tmp_path: Path,
) -> None:
    """FOUP 查询失败不能阻塞 Loadport 升级，也不能把状态永久留在 running"""
    state_file = tmp_path / "state.json"
    log_file = tmp_path / "update.log"
    loadport_installer = FakeLoadportInstaller()
    foup_installer = FakeFoupInstaller()
    orchestrator = UpdateOrchestrator(
        reader=FakeReader(),
        current_loadport_version=FakeLoadportVersion("1.0.0"),
        foup_client=FailingFoupClient(),
        loadport_installer=loadport_installer,
        foup_installer=foup_installer,
        state_file=state_file,
        log_file=log_file,
    )

    try:
        orchestrator.run(tmp_path / "package.tar.gz")
    except Exception as exc:
        assert "FOUP" in str(exc) or "foup" in str(exc)
    else:
        raise AssertionError("expected the FOUP failure to surface")

    # Loadport 升级必须照常执行
    assert loadport_installer.calls == [("1.2.3", Path("/package/loadport/app"))]
    assert foup_installer.calls == []

    state = json.loads(state_file.read_text())
    assert state["update_state"] == "failed"
    assert "FOUP" in state["update_message"] or "foup" in state["update_message"]


# ---------------------------------------------------------------- R29 / R30


class BrokenReader:
    def read(self, package_path):
        raise ValueError("invalid package")


class FailingInstallLoadportInstaller:
    def __init__(self):
        self.calls = []

    def install(self, version, app_dir):
        self.calls.append((version, app_dir))
        raise RuntimeError("GUI service did not become active after upgrade")


def _make_orchestrator(state_file, log_file, *, reader, current_version, installer):
    return UpdateOrchestrator(
        reader=reader,
        current_loadport_version=current_version,
        foup_client=FakeFoupClient("2.0.1", "2026.05.09"),
        loadport_installer=installer,
        foup_installer=FakeFoupInstaller(),
        state_file=state_file,
        log_file=log_file,
    )


def test_orchestrator_records_failed_when_package_read_fails(tmp_path: Path) -> None:
    """R30：读取包失败也要写 failed，不能让上一次 succeeded 冒充本次结果"""
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "loadport_version": "0.9.0",
                "update_state": "succeeded",
                "update_message": "old success",
            }
        ),
        encoding="utf-8",
    )
    orchestrator = _make_orchestrator(
        state_file,
        tmp_path / "update.log",
        reader=BrokenReader(),
        current_version=FakeLoadportVersion("1.0.0"),
        installer=FakeLoadportInstaller(),
    )

    try:
        orchestrator.run(tmp_path / "bad.tar.gz")
    except ValueError:
        pass
    else:
        raise AssertionError("expected package read failure to surface")

    state = json.loads(state_file.read_text())
    assert state["update_state"] == "failed"
    assert "invalid package" in state["update_message"]


def test_orchestrator_records_actual_version_after_failed_install(
    tmp_path: Path,
) -> None:
    """R29：回滚成功后状态里的版本必须是实际运行版本，而不是目标版本"""
    state_file = tmp_path / "state.json"
    installer = FailingInstallLoadportInstaller()
    orchestrator = _make_orchestrator(
        state_file,
        tmp_path / "update.log",
        reader=FakeReader(),
        current_version=FakeLoadportVersion("1.0.0"),
        installer=installer,
    )

    try:
        orchestrator.run(tmp_path / "package.tar.gz")
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected install failure to surface")

    state = json.loads(state_file.read_text())
    assert state["update_state"] == "failed"
    assert state["loadport_version"] == "1.0.0", "回滚后界面必须显示实际运行版本"
    assert state["loadport_target_version"] == "1.2.3"


def test_orchestrator_handles_unreadable_current_version(tmp_path: Path) -> None:
    """R30：读取当前版本失败也必须落到 failed，而不是永久 running"""

    def broken_version():
        raise OSError("current link broken")

    orchestrator = _make_orchestrator(
        tmp_path / "state.json",
        tmp_path / "update.log",
        reader=FakeReader(),
        current_version=broken_version,
        installer=FakeLoadportInstaller(),
    )

    try:
        orchestrator.run(tmp_path / "package.tar.gz")
    except OSError:
        pass
    else:
        raise AssertionError("expected current version failure to surface")

    state = json.loads((tmp_path / "state.json").read_text())
    assert state["update_state"] == "failed"
    assert state["loadport_target_version"] == "1.2.3"
