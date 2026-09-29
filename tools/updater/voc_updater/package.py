from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path

# 版本字符串会被拼进 release 目录名，必须拒绝路径分隔符与上级跳转
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


def validate_version(version: str) -> str:
    """校验版本字符串可用于目录名，返回原值。"""
    text = str(version or "").strip()
    if not _VERSION_PATTERN.match(text) or ".." in text:
        raise ValueError(f"invalid version string: {version!r}")
    return text


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


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

        extract_dir = (self.work_dir / source_package.stem.replace(".tar", "")).resolve()
        work_root = self.work_dir.resolve()
        if work_root != extract_dir and work_root not in extract_dir.parents:
            raise ValueError(f"invalid work directory for package: {source_package.name}")
        if extract_dir.exists():
            # 上次运行留下的解包残留：清掉重来，否则第二次升级会永久失败
            shutil.rmtree(extract_dir)
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
        validate_version(loadport_manifest["version"])
        if not foup_manifest.get("ps_version"):
            raise ValueError("missing FOUP PS version")
        if not foup_manifest.get("pl_version"):
            raise ValueError("missing FOUP PL version")

        # manifest 提供哈希时必须逐项校验（设计文档第 159 行）
        self._verify_sha256(
            root / "loadport", loadport_manifest.get("sha256"), "loadport"
        )
        self._verify_sha256(root / "foup", foup_manifest.get("sha256"), "foup")

        loadport_app_dir = root / "loadport" / "app"
        if not (loadport_app_dir / "src" / "voc_app" / "gui" / "app.py").exists():
            raise ValueError("missing Loadport app entry file")

        foup_root = root / "foup"
        ps_file = self._component_file(
            foup_root, foup_manifest.get("ps_file", "ps/run"), "FOUP PS"
        )
        pl_file = self._component_file(
            foup_root,
            foup_manifest.get("pl_file", "pl/design_1_wrapper.bit.bin"),
            "FOUP PL",
        )

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
    def _component_file(component_root: Path, relative: object, label: str) -> Path:
        """把 manifest 里的相对路径安全地解析为组件内的普通文件。"""
        text = str(relative or "").strip()
        if not text or os.path.isabs(text) or ".." in Path(text).parts:
            raise ValueError(f"invalid {label} path in manifest: {relative!r}")
        root = component_root.resolve()
        target = (component_root / text).resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"{label} path escapes package: {relative!r}")
        if not target.is_file():
            raise ValueError(f"missing {label} file")
        return target

    @staticmethod
    def _verify_sha256(component_root: Path, declared: object, component: str) -> None:
        """校验 manifest 中声明的 sha256（形如 {组件内相对路径: 十六进制摘要}）。"""
        if declared in (None, {}, ""):
            return
        if not isinstance(declared, dict):
            raise ValueError(f"invalid sha256 section in {component} manifest")
        root = component_root.resolve()
        for relative, expected in declared.items():
            text = str(relative).strip()
            if not text or os.path.isabs(text) or ".." in Path(text).parts:
                raise ValueError(f"invalid sha256 path in {component} manifest: {relative!r}")
            target = (component_root / text).resolve()
            if root != target and root not in target.parents:
                raise ValueError(f"sha256 path escapes package: {relative!r}")
            if not target.is_file():
                raise ValueError(f"sha256 file missing: {component}/{text}")
            actual = _sha256_of(target)
            if actual.lower() != str(expected).strip().lower():
                raise ValueError(f"sha256 mismatch for {component}/{text}")

    @staticmethod
    def _extract_safely(tar: tarfile.TarFile, extract_dir: Path) -> None:
        """逐项解包：拒绝符号链接/硬链接/特殊文件，并持续约束目标路径。

        R10：只校验 member.name 是不够的——先落盘一个指向外部的符号链接，
        ``extractall`` 随后会跟随它把文件写到解包目录之外。
        """
        root = extract_dir.resolve()
        for member in tar.getmembers():
            target = (extract_dir / member.name).resolve()
            if root != target and root not in target.parents:
                raise ValueError(f"unsafe path in update package: {member.name}")
            if member.issym() or member.islnk():
                raise ValueError(
                    f"symbolic/hard link not allowed in update package: {member.name}"
                )
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isreg():
                raise ValueError(
                    f"unsupported entry in update package: {member.name}"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tar.extractfile(member)
            if source is None:
                raise ValueError(f"cannot read entry in update package: {member.name}")
            with source, open(target, "wb") as destination:
                shutil.copyfileobj(source, destination)
            if member.mode:
                os.chmod(target, member.mode & 0o777)

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
