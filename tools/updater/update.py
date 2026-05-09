from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from voc_updater.commands import CommandRunner
from voc_updater.config import load_config
from voc_updater.foup import FoupInstaller
from voc_updater.foup_version import FoupVersionClient
from voc_updater.loadport import LoadportInstaller
from voc_updater.orchestrator import UpdateOrchestrator
from voc_updater.package import UpdatePackageReader


def _find_package(updates_dir: Path) -> Path:
    packages = sorted(updates_dir.glob("*.tar.gz"), key=lambda path: path.stat().st_mtime)
    if not packages:
        raise FileNotFoundError(f"no update package found in {updates_dir}")
    return packages[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VOC updater")
    parser.add_argument("--config", required=True)
    parser.add_argument("--package")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    package_path = Path(args.package) if args.package else _find_package(
        config.paths.updates_dir
    )
    runner = CommandRunner()
    reader = UpdatePackageReader(config.paths.work_dir)
    foup_client = FoupVersionClient(config.foup.host, config.foup.port)
    loadport_installer = LoadportInstaller(
        releases_dir=config.paths.releases_dir,
        current_link=config.paths.current_link,
        gui_service=config.services.gui_service,
        systemctl_scope=config.services.systemctl_scope,
        runner=runner,
    )
    foup_installer = FoupInstaller(
        host=config.foup.host,
        ssh_user=config.foup.ssh_user,
        ssh_key=config.foup.ssh_key,
        mount_device=config.foup.remote_mount_device,
        mount_point=config.foup.remote_mount_point,
        remote_run_path=config.foup.remote_run_path,
        remote_pl_path=config.foup.remote_pl_path,
        runner=runner,
    )

    def current_loadport_version() -> str:
        manifest = config.paths.current_link / "loadport" / "manifest.json"
        if manifest.exists():
            return str(
                json.loads(manifest.read_text(encoding="utf-8")).get(
                    "version",
                    "unknown",
                )
            )
        pyproject = config.paths.current_link / "pyproject.toml"
        if pyproject.exists():
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("version"):
                    return line.split("=", 1)[1].strip().strip('"')
        return "unknown"

    orchestrator = UpdateOrchestrator(
        reader=reader,
        current_loadport_version=current_loadport_version,
        foup_client=foup_client,
        loadport_installer=loadport_installer,
        foup_installer=foup_installer,
        state_file=config.paths.state_file,
        log_file=config.paths.log_file,
    )
    orchestrator.run(package_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
