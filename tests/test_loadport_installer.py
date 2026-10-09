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
        settle_seconds=0,
    )

    installer.install(version="1.2.3", app_dir=new_app)

    assert current.resolve() == (releases / "loadport-1.2.3").resolve()
    assert (current / "src" / "voc_app" / "gui" / "app.py").read_text() == "new"
    assert runner.commands == [
        ["systemctl", "--user", "stop", "voc-gui.service"],
        ["systemctl", "--user", "is-active", "voc-gui.service"],
        ["systemctl", "--user", "start", "voc-gui.service"],
        ["systemctl", "--user", "is-active", "voc-gui.service"],
        ["systemctl", "--user", "show", "-p", "MainPID", "--value", "voc-gui.service"],
        ["systemctl", "--user", "is-active", "voc-gui.service"],
        ["systemctl", "--user", "show", "-p", "MainPID", "--value", "voc-gui.service"],
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
        settle_seconds=0,
    )

    try:
        installer.install(version="1.2.3", app_dir=new_app)
    except RuntimeError as exc:
        assert "GUI service did not become active" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    assert current.resolve() == old_release.resolve()


def test_install_copies_manifest_so_version_can_be_read(tmp_path: Path) -> None:
    """release 内必须带有版本 manifest，否则版本比较永远失效（每次升级都重启 GUI）"""
    import json

    from voc_app.version_info import get_loadport_version

    root = tmp_path / "package" / "loadport"
    new_app = root / "app"
    _make_app(new_app, "new")
    (root / "manifest.json").write_text(
        json.dumps({"component": "loadport", "version": "1.2.3"}),
        encoding="utf-8",
    )

    releases = tmp_path / "releases"
    current = tmp_path / "current"
    installer = LoadportInstaller(
        releases_dir=releases,
        current_link=current,
        gui_service="voc-gui.service",
        systemctl_scope="user",
        runner=FakeCommandRunner(),
        settle_seconds=0,
    )

    installer.install(version="1.2.3", app_dir=new_app)

    assert (current / "loadport" / "manifest.json").exists()
    assert get_loadport_version(current) == "1.2.3"


def test_install_repairs_manifest_in_existing_release(tmp_path: Path) -> None:
    """已存在的 release（例如上次部分拷贝留下）也必须补上版本 manifest"""
    import json

    from voc_app.version_info import get_loadport_version

    releases = tmp_path / "releases"
    current = tmp_path / "current"
    target = releases / "loadport-1.2.3"
    _make_app(target, "already-there")

    package_root = tmp_path / "package" / "loadport"
    new_app = package_root / "app"
    _make_app(new_app, "new")
    (package_root / "manifest.json").write_text(
        json.dumps({"component": "loadport", "version": "1.2.3"}),
        encoding="utf-8",
    )

    installer = LoadportInstaller(
        releases_dir=releases,
        current_link=current,
        gui_service="voc-gui.service",
        systemctl_scope="user",
        runner=FakeCommandRunner(),
        settle_seconds=0,
    )

    installer.install(version="1.2.3", app_dir=new_app)

    assert (target / "loadport" / "manifest.json").exists()
    assert get_loadport_version(target) == "1.2.3"
