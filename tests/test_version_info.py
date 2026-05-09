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
