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
