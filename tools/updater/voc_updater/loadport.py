from __future__ import annotations

import json
import logging
import os
import shutil
import time
from pathlib import Path

from .commands import CommandRunner, copy_tree
from .package import validate_version

logger = logging.getLogger(__name__)


class LoadportInstaller:
    def __init__(
        self,
        releases_dir: str | Path,
        current_link: str | Path,
        gui_service: str,
        systemctl_scope: str,
        runner: CommandRunner,
        stop_timeout: int = 60,
        start_timeout: int = 60,
        settle_seconds: float = 2.0,
    ) -> None:
        self.releases_dir = Path(releases_dir)
        self.current_link = Path(current_link)
        self.gui_service = gui_service
        self.systemctl_scope = systemctl_scope
        self.runner = runner
        self.stop_timeout = int(stop_timeout)
        self.start_timeout = int(start_timeout)
        # 启动确认的稳定窗口：真实部署测试发现，新版可能在 start 之后几十毫秒
        # 就退出，若立即判定会把已经死掉的进程记成升级成功。
        self.settle_seconds = float(settle_seconds)

    def install(self, version: str, app_dir: str | Path) -> Path:
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        old_target = self._current_target()
        source = Path(app_dir)
        target = self._release_dir_for(version)

        if self._is_release_complete(target):
            # 已有完整版本：只刷新版本 manifest
            self._write_release_manifest(source, target, version)
        else:
            self._publish_release(source, target, version)

        # 事务化：停止 -> 切换 current -> 启动 -> 确认运行版本。
        # 切换之后的任何异常（启动返回非零、超时、状态不属于目标 release）
        # 都必须回滚到旧版本，不能让现场停在半升级状态（R14/R27）。
        self._stop_service()
        self._switch_current(target)
        try:
            self._start_service()
            self._confirm_running(target)
        except Exception as exc:  # noqa: BLE001
            self._rollback(old_target, exc)
            raise RuntimeError(
                f"upgrade failed, rolled back to previous release: {exc}"
            ) from exc
        return target

    # ------------------------------------------------------------------
    # 服务生命周期
    # ------------------------------------------------------------------

    def _current_target(self) -> Path | None:
        if not self.current_link.exists():
            return None
        try:
            return self.current_link.resolve()
        except OSError:
            return None

    def _stop_service(self) -> None:
        """停止服务，并确认它真的停了（R27）。

        ``stop`` 返回非零但服务仍是 active 说明旧进程还在运行；此时继续切换
        current 会让"start 无效果、is-active 仍然成功"，把旧进程记成升级成功。
        """
        result = self._systemctl("stop", timeout=self.stop_timeout)
        # 不论 stop 的返回码如何，都必须确认服务真的停了：只要它还是 active，
        # 继续切换 current 就会把仍在运行的旧进程记成升级成功（R27）。
        if self._service_is_active():
            raise RuntimeError(
                f"failed to stop service {self.gui_service} "
                f"(rc={result.returncode})"
            )

    def _start_service(self) -> None:
        result = self._systemctl("start", timeout=self.start_timeout)
        if result.returncode != 0:
            raise RuntimeError(
                f"failed to start service {self.gui_service} (rc={result.returncode})"
            )

    def _confirm_running(self, target: Path) -> None:
        if not self._service_is_active():
            raise RuntimeError("GUI service did not become active after upgrade")
        pid_before = self._main_pid()

        # 稳定窗口：等服务真的活下来再复查。真实部署测试中，一个启动即退出的
        # release 在 start 后几十毫秒才死；立即确认会误判成功（服务随后 inactive，
        # current 却停在新版本上）。
        if self.settle_seconds > 0:
            time.sleep(self.settle_seconds)
        if not self._service_is_active():
            raise RuntimeError(
                "GUI service exited during the post-start settle window"
            )
        pid_after = self._main_pid()
        if pid_before and pid_after and pid_before != pid_after:
            raise RuntimeError(
                "GUI service restarted during the post-start settle window "
                f"({pid_before} -> {pid_after})"
            )

        current_target = self._current_target()
        if current_target is None or current_target != target.resolve():
            raise RuntimeError(
                f"current link points to {current_target}, expected {target}"
            )
        # 进程 cwd 必须位于目标 release，确认服务真的加载了新代码（R13）
        self._verify_process_release(pid_after or pid_before, target)

    def _service_is_active(self) -> bool:
        return self._systemctl("is-active").returncode == 0

    def _main_pid(self) -> str:
        args = ["systemctl"]
        if self.systemctl_scope == "user":
            args.append("--user")
        args.extend(["show", "-p", "MainPID", "--value", self.gui_service])
        result = self.runner.run(args)
        pid = (result.stdout or "").strip()
        return pid if pid.isdigit() and pid != "0" else ""

    def _verify_process_release(self, pid: str, target: Path) -> None:
        """校验 MainPID 的 cwd 属于目标 release。

        拿不到 PID 或 ``/proc`` 不可读（权限/平台限制）时不做结论，避免在
        不支持的环境里误判升级失败。
        """
        if not pid:
            return
        cwd = Path(f"/proc/{pid}/cwd")
        # /proc 不可读或 PID 已退出时不做结论，避免在不支持的环境里误判
        if not cwd.exists():
            return
        try:
            actual = cwd.resolve(strict=True)
        except OSError:
            return
        if actual != target.resolve():
            raise RuntimeError(
                f"running process {pid} cwd {actual} does not belong to "
                f"target release {target}"
            )

    def _rollback(self, old_target: Path | None, original: Exception) -> None:
        if old_target is None:
            self._systemctl("stop")
            raise RuntimeError(
                "upgrade failed and there is no previous release to roll back to: "
                f"{original}"
            ) from original
        self._switch_current(old_target)
        result = self._systemctl("start")
        if result.returncode != 0 or not self._service_is_active():
            raise RuntimeError(
                f"upgrade failed ({original}); rollback to {old_target} also failed"
            ) from original
        logger.info("已回滚到旧版本: %s", old_target)

    # ------------------------------------------------------------------
    # release 发布
    # ------------------------------------------------------------------

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

    def _systemctl(self, action: str, timeout: int = 60):
        args = ["systemctl"]
        if self.systemctl_scope == "user":
            args.append("--user")
        args.extend([action, self.gui_service])
        return self.runner.run(args, timeout=timeout)

    def _switch_current(self, target: Path) -> None:
        tmp_link = self.current_link.with_name(self.current_link.name + ".next")
        if tmp_link.exists() or tmp_link.is_symlink():
            tmp_link.unlink()
        tmp_link.symlink_to(target, target_is_directory=True)
        os.replace(tmp_link, self.current_link)
