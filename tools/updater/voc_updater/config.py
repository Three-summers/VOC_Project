from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PathsConfig:
    base_dir: Path
    updates_dir: Path
    work_dir: Path
    releases_dir: Path
    current_link: Path
    state_file: Path
    log_file: Path


@dataclass(frozen=True)
class ServicesConfig:
    gui_service: str
    systemctl_scope: str


@dataclass(frozen=True)
class PythonConfig:
    executable: Path


@dataclass(frozen=True)
class FoupConfig:
    host: str
    port: int
    ssh_user: str
    ssh_key: Path
    remote_mount_device: str
    remote_mount_point: Path
    remote_run_path: Path
    remote_pl_path: Path


@dataclass(frozen=True)
class UpdaterConfig:
    paths: PathsConfig
    services: ServicesConfig
    python: PythonConfig
    foup: FoupConfig


def _required(mapping: dict[str, Any], key: str) -> Any:
    if key not in mapping or mapping[key] in (None, ""):
        raise ValueError(f"missing required config key: {key}")
    return mapping[key]


def load_config(path: str | Path) -> UpdaterConfig:
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    paths = _required(data, "paths")
    services = _required(data, "services")
    python = _required(data, "python")
    foup = _required(data, "foup")
    return UpdaterConfig(
        paths=PathsConfig(
            base_dir=Path(_required(paths, "base_dir")),
            updates_dir=Path(_required(paths, "updates_dir")),
            work_dir=Path(_required(paths, "work_dir")),
            releases_dir=Path(_required(paths, "releases_dir")),
            current_link=Path(_required(paths, "current_link")),
            state_file=Path(_required(paths, "state_file")),
            log_file=Path(_required(paths, "log_file")),
        ),
        services=ServicesConfig(
            gui_service=str(_required(services, "gui_service")),
            systemctl_scope=str(services.get("systemctl_scope", "user")),
        ),
        python=PythonConfig(executable=Path(_required(python, "executable"))),
        foup=FoupConfig(
            host=str(_required(foup, "host")),
            port=int(_required(foup, "port")),
            ssh_user=str(_required(foup, "ssh_user")),
            ssh_key=Path(_required(foup, "ssh_key")),
            remote_mount_device=str(_required(foup, "remote_mount_device")),
            remote_mount_point=Path(_required(foup, "remote_mount_point")),
            remote_run_path=Path(_required(foup, "remote_run_path")),
            remote_pl_path=Path(_required(foup, "remote_pl_path")),
        ),
    )
