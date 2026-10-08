from __future__ import annotations

from pathlib import Path
from typing import Callable

from .state import UpdateStateWriter


class UpdateOrchestrator:
    """单次升级尝试的编排与状态记录。

    关键约束（R29/R30）：整个升级尝试都处于状态生命周期内。
    读取包、读取当前版本、安装任一环节失败，都必须写入 failed，并区分
    "实际运行版本"与"目标版本"；不能让上一次的 succeeded 冒充本次结果，
    也不能让状态永久停在 running。
    """

    def __init__(
        self,
        reader,
        current_loadport_version: Callable[[], str],
        foup_client,
        loadport_installer,
        foup_installer,
        state_file: str | Path,
        log_file: str | Path,
    ) -> None:
        self.reader = reader
        self.current_loadport_version = current_loadport_version
        self.foup_client = foup_client
        self.loadport_installer = loadport_installer
        self.foup_installer = foup_installer
        self.state = UpdateStateWriter(state_file=state_file, log_file=log_file)

    def run(self, package_path: str | Path) -> None:
        try:
            package = self.reader.read(package_path)
        except Exception as exc:  # noqa: BLE001
            message = f"package read failed: {exc}"
            self.state.write_status("unknown", "failed", message)
            self.state.log(message)
            raise

        target_version = package.loadport_version
        self.state.write_status(
            target_version,
            "running",
            "Validating update",
            target_version=target_version,
        )
        self.state.log(f"package loaded: {package_path}")

        current_loadport = "unknown"
        foup_error: Exception | None = None
        ps_changed = False
        pl_changed = False

        try:
            current_loadport = str(self.current_loadport_version())
            loadport_changed = current_loadport != target_version

            # FOUP 版本查询失败不应阻塞 Loadport 升级（设计文档要求），
            # 但必须显式记录失败，不能让状态永久停留在 running。
            try:
                current_foup = self.foup_client.get_version()
            except Exception as exc:  # noqa: BLE001
                foup_error = exc
                self.state.log(f"foup version query failed: {exc}")
            else:
                ps_changed = current_foup.ps_version != package.foup_ps_version
                pl_changed = current_foup.pl_version != package.foup_pl_version
                if not loadport_changed and not ps_changed and not pl_changed:
                    self.state.write_status(
                        current_loadport,
                        "skipped",
                        "Versions already match",
                        target_version=target_version,
                    )
                    self.state.log("update skipped: all versions match")
                    return

            if loadport_changed:
                self.state.log(
                    f"updating loadport: {current_loadport} -> {target_version}"
                )
                self.loadport_installer.install(
                    version=target_version,
                    app_dir=package.loadport_app_dir,
                )
            if ps_changed or pl_changed:
                self.state.log(
                    "updating foup: "
                    f"ps {current_foup.ps_version} -> {package.foup_ps_version}, "
                    f"pl {current_foup.pl_version} -> {package.foup_pl_version}"
                )
                self.foup_installer.upgrade(
                    ps_changed=ps_changed,
                    pl_changed=pl_changed,
                    local_run_file=package.foup_ps_file,
                    local_pl_file=package.foup_pl_file,
                )
        except Exception as exc:  # noqa: BLE001
            actual_version = self._safe_current_version(target_version)
            self.state.write_status(
                actual_version,
                "failed",
                str(exc),
                target_version=target_version,
            )
            self.state.log(f"update failed: {exc}")
            raise

        if foup_error is not None:
            message = f"FOUP update skipped: {foup_error}"
            self.state.write_status(
                target_version,
                "failed",
                message,
                target_version=target_version,
            )
            self.state.log(message)
            raise RuntimeError(message)

        self.state.write_status(
            target_version,
            "succeeded",
            "Update completed",
            target_version=target_version,
        )
        self.state.log("update succeeded")

    def _safe_current_version(self, fallback: str) -> str:
        """回滚后重新读取实际运行版本；读不到时退回目标版本，避免再次抛出。"""
        try:
            return str(self.current_loadport_version())
        except Exception as exc:  # noqa: BLE001
            self.state.log(f"reading current version failed: {exc}")
            return fallback
