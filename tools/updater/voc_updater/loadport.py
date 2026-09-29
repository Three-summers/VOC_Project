from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .commands import CommandRunner, copy_tree
from .package import validate_version


class LoadportInstaller:
    def __init__(
        self,
        releases_dir: str | Path,
        current_link: str | Path,
        gui_service: str,
        systemctl_scope: str,
        runner: CommandRunner,
    ) -> None:
        self.releases_dir = Path(releases_dir)
        self.current_link = Path(current_link)
        self.gui_service = gui_service
        self.systemctl_scope = systemctl_scope
        self.runner = runner

    def install(self, version: str, app_dir: str | Path) -> Path:
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        old_target = self.current_link.resolve() if self.current_link.exists() else None
        source = Path(app_dir)
        target = self._release_dir_for(version)

        if self._is_release_complete(target):
            # 已有完整版本：只刷新版本 manifest
            self._write_release_manifest(source, target, version)
        else:
            self._publish_release(source, target, version)

        self._systemctl("stop")
        self._switch_current(target)
        self._systemctl("start")
        active = self._systemctl("is-active")
        if active.returncode != 0:
            if old_target is not None:
                self._switch_current(old_target)
                self._systemctl("start")
            raise RuntimeError("GUI service did not become active after upgrade")
        return target

    def _release_dir_for(self, version: str) -> Path:
        """版本字符串会被拼进目录名，必须校验格式并确认落在 releases 下。"""
        validate_version(version)
        target = self.releases_dir / f"loadport-{version}"
        releases_real = self.releases_dir.resolve()
        if target.resolve().parent != releases_real:
            raise ValueError(f"invalid release target for version: {version!r}")
        return target

    @staticmethod
    def _is_release_complete(target: Path) -> bool:
        """release 是否包含应用入口（与升级包的校验口径一致）。"""
        return (target / "src" / "voc_app" / "gui" / "app.py").is_file()

    def _publish_release(self, source: Path, target: Path, version: str) -> None:
        """在暂存目录完成复制与校验后原子发布。

        R15：只凭"目标目录存在"判断复制完成，会让上次中断留下的残缺目录
        被当成完整版本（甚至被补上正确的版本 manifest）持续复用。
        """
        staging = target.with_name(f".staging-{target.name}")
        if staging.exists():
            shutil.rmtree(staging)
        try:
            copy_tree(source, staging)
            self._write_release_manifest(source, staging, version)
            if not self._is_release_complete(staging):
                raise RuntimeError(f"incomplete release source: {source}")
            if target.exists():
                shutil.rmtree(target)
            os.replace(staging, target)
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

    def _write_release_manifest(self, app_dir: Path, target: Path, version: str) -> None:
        """把升级包内的 ``loadport/manifest.json`` 放进 release。

        版本读取（GUI ``version_info`` 与 updater 的 ``current_loadport_version``）
        都查 ``<release>/loadport/manifest.json``；升级包里该文件是 ``app/`` 的
        同级文件，不复制会导致 release 里永远读不到版本（回退到 pyproject 的
        0.1.0），从而每次运行都判定"loadport 需要升级"并重启 GUI。
        """
        destination = target / "loadport" / "manifest.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = Path(app_dir).parent / "manifest.json"
        if source.exists():
            shutil.copyfile(source, destination)
            return
        destination.write_text(
            json.dumps(
                {"component": "loadport", "version": version},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _systemctl(self, action: str):
        args = ["systemctl"]
        if self.systemctl_scope == "user":
            args.append("--user")
        args.extend([action, self.gui_service])
        return self.runner.run(args)

    def _switch_current(self, target: Path) -> None:
        tmp_link = self.current_link.with_name(self.current_link.name + ".next")
        if tmp_link.exists() or tmp_link.is_symlink():
            tmp_link.unlink()
        tmp_link.symlink_to(target, target_is_directory=True)
        os.replace(tmp_link, self.current_link)
