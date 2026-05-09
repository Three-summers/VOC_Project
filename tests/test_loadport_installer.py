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
    runner = FakeCommandRunner(
        fail_on=[["systemctl", "--user", "is-active", "voc-gui.service"]]
    )

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
