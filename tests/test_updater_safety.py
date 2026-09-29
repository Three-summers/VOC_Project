"""升级器安全与可靠性测试（R10 / R11 / R12 / R15）。

R10：tar 内的符号链接/硬链接可以绕过解包目录边界
R11：manifest 里的版本字符串可以跳出 releases 目录
R12：manifest 声明了 sha256，但安装前不校验
R15：上次复制中断留下的残缺 release 被当成完整版本复用
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.commands import FakeCommandRunner
from voc_updater.loadport import LoadportInstaller
from voc_updater.package import UpdatePackageReader


def _valid_source(root: Path, sha256: dict | None = None) -> None:
    loadport = root / "loadport"
    foup = root / "foup"
    (loadport / "app" / "src" / "voc_app" / "gui").mkdir(parents=True)
    (foup / "ps").mkdir(parents=True)
    (foup / "pl").mkdir(parents=True)
    (loadport / "app" / "src" / "voc_app" / "gui" / "app.py").write_text(
        "print('app')\n", encoding="utf-8"
    )
    (foup / "ps" / "run").write_bytes(b"run")
    (foup / "pl" / "design_1_wrapper.bit.bin").write_bytes(b"bit")
    manifest = {"component": "loadport", "version": "1.2.3"}
    if sha256 is not None:
        manifest["sha256"] = sha256
    (loadport / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
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


def _write_package(source: Path, package_path: Path) -> None:
    with tarfile.open(package_path, "w:gz") as tar:
        tar.add(source, arcname=".")


def _make_app(path: Path, marker: str) -> None:
    app = path / "src" / "voc_app" / "gui"
    app.mkdir(parents=True)
    (app / "app.py").write_text(marker, encoding="utf-8")


# ---------------------------------------------------------------- R10


def test_reader_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    package_path = tmp_path / "evil.tar.gz"
    with tarfile.open(package_path, "w:gz") as tar:
        link = tarfile.TarInfo("escape")
        link.type = tarfile.SYMTYPE
        link.linkname = str(outside)
        tar.addfile(link)

        payload = b"pwned"
        entry = tarfile.TarInfo("escape/marker.txt")
        entry.size = len(payload)
        tar.addfile(entry, io.BytesIO(payload))

    with pytest.raises(ValueError):
        UpdatePackageReader(tmp_path / "work").read(package_path)

    assert not (outside / "marker.txt").exists(), "符号链接把文件写到了解包目录之外"


def test_reader_rejects_hardlink(tmp_path: Path) -> None:
    package_path = tmp_path / "hardlink.tar.gz"
    with tarfile.open(package_path, "w:gz") as tar:
        data = b"x"
        base = tarfile.TarInfo("loadport/base")
        base.size = len(data)
        tar.addfile(base, io.BytesIO(data))
        link = tarfile.TarInfo("loadport/link")
        link.type = tarfile.LNKTYPE
        link.linkname = "loadport/base"
        tar.addfile(link)

    with pytest.raises(ValueError):
        UpdatePackageReader(tmp_path / "work").read(package_path)


def test_reader_still_extracts_normal_package(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _valid_source(source)
    package_path = tmp_path / "ok.tar.gz"
    _write_package(source, package_path)

    result = UpdatePackageReader(tmp_path / "work").read(package_path)

    assert result.loadport_version == "1.2.3"
    assert result.loadport_app_dir.exists()


# ---------------------------------------------------------------- R12


def test_reader_rejects_wrong_sha256(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _valid_source(source, sha256={"app/src/voc_app/gui/app.py": "0" * 64})
    package_path = tmp_path / "badhash.tar.gz"
    _write_package(source, package_path)

    with pytest.raises(ValueError, match="sha256"):
        UpdatePackageReader(tmp_path / "work").read(package_path)


def test_reader_accepts_matching_sha256(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    digest = hashlib.sha256(b"print('app')\n").hexdigest()
    _valid_source(source, sha256={"app/src/voc_app/gui/app.py": digest})
    package_path = tmp_path / "goodhash.tar.gz"
    _write_package(source, package_path)

    result = UpdatePackageReader(tmp_path / "work").read(package_path)

    assert result.loadport_version == "1.2.3"


def test_reader_rejects_sha256_path_escape(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _valid_source(source, sha256={"../../etc/passwd": "0" * 64})
    package_path = tmp_path / "hashpath.tar.gz"
    _write_package(source, package_path)

    with pytest.raises(ValueError):
        UpdatePackageReader(tmp_path / "work").read(package_path)


# ---------------------------------------------------------------- R11


def _installer(tmp_path: Path, runner=None) -> LoadportInstaller:
    return LoadportInstaller(
        releases_dir=tmp_path / "releases",
        current_link=tmp_path / "current",
        gui_service="voc-gui.service",
        systemctl_scope="user",
        runner=runner or FakeCommandRunner(),
    )


@pytest.mark.parametrize(
    "version",
    ["x/../../outside", "../escape", "/absolute", "", ".", "..", "a/b"],
)
def test_installer_rejects_unsafe_versions(tmp_path: Path, version: str) -> None:
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")

    with pytest.raises(ValueError):
        _installer(tmp_path).install(version=version, app_dir=new_app)

    assert not (tmp_path / "current").exists()
    assert not (tmp_path / "outside").exists()


def test_installer_accepts_normal_version(tmp_path: Path) -> None:
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")

    target = _installer(tmp_path).install(version="1.2.3-rc1", app_dir=new_app)

    assert target == tmp_path / "releases" / "loadport-1.2.3-rc1"
    assert target.exists()


# ---------------------------------------------------------------- R15


def test_installer_rebuilds_incomplete_release(tmp_path: Path) -> None:
    releases = tmp_path / "releases"
    stale = releases / "loadport-1.2.3"
    stale.mkdir(parents=True)
    (stale / "stale.txt").write_text("partial copy", encoding="utf-8")

    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")

    installer = _installer(tmp_path)
    installer.install(version="1.2.3", app_dir=new_app)

    current = (tmp_path / "current").resolve()
    assert (current / "src" / "voc_app" / "gui" / "app.py").read_text() == "new"
    assert not (current / "stale.txt").exists(), "残缺目录的残留内容必须被清除"


def test_installer_does_not_leave_staging_directory(tmp_path: Path) -> None:
    new_app = tmp_path / "package" / "app"
    _make_app(new_app, "new")

    _installer(tmp_path).install(version="1.2.3", app_dir=new_app)

    leftovers = [p.name for p in (tmp_path / "releases").iterdir() if p.name.startswith(".")]
    assert leftovers == [], f"存在未清理的暂存目录: {leftovers}"
