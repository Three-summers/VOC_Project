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
