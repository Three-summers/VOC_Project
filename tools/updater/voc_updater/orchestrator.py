from __future__ import annotations

from pathlib import Path
from typing import Callable

from .state import UpdateStateWriter


class UpdateOrchestrator:
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
        package = self.reader.read(package_path)
        self.state.write_status(package.loadport_version, "running", "Validating update")
        self.state.log(f"package loaded: {package_path}")

        current_loadport = self.current_loadport_version()
        current_foup = self.foup_client.get_version()

        loadport_changed = current_loadport != package.loadport_version
        ps_changed = current_foup.ps_version != package.foup_ps_version
        pl_changed = current_foup.pl_version != package.foup_pl_version

        if not loadport_changed and not ps_changed and not pl_changed:
            self.state.write_status(
                package.loadport_version,
                "skipped",
                "Versions already match",
            )
            self.state.log("update skipped: all versions match")
            return

        try:
            if loadport_changed:
                self.state.log(
                    f"updating loadport: {current_loadport} -> {package.loadport_version}"
                )
                self.loadport_installer.install(
                    version=package.loadport_version,
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
        except Exception as exc:
            self.state.write_status(package.loadport_version, "failed", str(exc))
            self.state.log(f"update failed: {exc}")
            raise

        self.state.write_status(package.loadport_version, "succeeded", "Update completed")
        self.state.log("update succeeded")
