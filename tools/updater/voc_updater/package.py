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
            self._extract_safely(tar, extract_dir)

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
    def _extract_safely(tar: tarfile.TarFile, extract_dir: Path) -> None:
        root = extract_dir.resolve()
        for member in tar.getmembers():
            target = (extract_dir / member.name).resolve()
            if root != target and root not in target.parents:
                raise ValueError(f"unsafe path in update package: {member.name}")
        tar.extractall(extract_dir)

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
