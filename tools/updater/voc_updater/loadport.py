from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .commands import CommandRunner, copy_tree


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
        target = self.releases_dir / f"loadport-{version}"
        if not target.exists():
            copy_tree(Path(app_dir), target)
            self._write_release_manifest(Path(app_dir), target, version)

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
