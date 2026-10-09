"""部署模板与 install.sh 的路径收敛测试。

现场路径只在 `deploy/install.sh` 的 `VOC_BASE` 填一次，systemd 单元与 updater
配置都是模板；这里保证：模板里不写死现场路径、占位符能全部被渲染、渲染后的
config.yaml 能被真实的 `load_config` 解析。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DEPLOY_DIR = ROOT_DIR / "deploy"
SYSTEMD_DIR = DEPLOY_DIR / "systemd" / "user"
UPDATER_DIR = ROOT_DIR / "tools" / "updater"

PLACEHOLDER_RE = re.compile(r"@[A-Z_]+@")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_voc_gui_service_template_uses_placeholders() -> None:
    content = _read(SYSTEMD_DIR / "voc-gui.service.in")
    assert "WorkingDirectory=@VOC_BASE@/current" in content
    assert "Environment=PYTHONPATH=@VOC_BASE@/current/src" in content
    assert "ExecStart=@VOC_PYTHON@ -m voc_app.gui.app" in content
    assert "Restart=on-failure" in content
    assert "/home/kasp" not in content, "单元模板不应写死现场路径"


def test_updater_service_template_uses_placeholders() -> None:
    content = _read(SYSTEMD_DIR / "voc-updater.service.in")
    assert "WorkingDirectory=@VOC_BASE@/updater" in content
    assert (
        "ExecStart=@VOC_PYTHON@ @VOC_BASE@/updater/update.py "
        "--config @VOC_BASE@/updater/config.yaml" in content
    )


def test_updater_path_template_uses_placeholder() -> None:
    content = _read(SYSTEMD_DIR / "voc-updater.path.in")
    assert "PathExistsGlob=@VOC_BASE@/updates/*.tar.gz" in content


def test_autostart_desktop_starts_systemd_service_not_python() -> None:
    content = _read(DEPLOY_DIR / "autostart" / "voc-gui.desktop")
    assert "Exec=systemctl --user start voc-gui.service" in content
    assert "python" not in content


def test_config_example_has_all_required_sections() -> None:
    content = _read(DEPLOY_DIR / "updater" / "config.yaml.example")
    for section in ("paths:", "services:", "python:", "foup:"):
        assert section in content
    for key in (
        "base_dir",
        "updates_dir",
        "work_dir",
        "releases_dir",
        "current_link",
        "state_file",
        "log_file",
        "gui_service",
        "systemctl_scope",
        "executable",
        "ssh_key",
    ):
        assert key in content


def test_config_example_renders_to_loadable_config(tmp_path: Path) -> None:
    template = _read(DEPLOY_DIR / "updater" / "config.yaml.example")
    values = {
        "VOC_BASE": str(tmp_path / "base"),
        "VOC_PYTHON": str(tmp_path / "base" / ".venv" / "bin" / "python"),
        "FOUP_HOST": "10.1.2.3",
        "FOUP_PORT": "65432",
        "FOUP_SSH_USER": "root",
        "FOUP_SSH_KEY": str(tmp_path / "base" / "updater" / "id_rsa"),
        "FOUP_MOUNT_DEVICE": "/dev/mmcblk1p1",
        "FOUP_MOUNT_POINT": "/tmp",
        "FOUP_RUN_PATH": "/tmp/run",
        "FOUP_PL_PATH": "/tmp/design_1_wrapper.bit.bin",
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"@{key}@", value)
    assert not PLACEHOLDER_RE.search(rendered), "示例里仍有未替换的占位符"

    config_path = tmp_path / "config.yaml"
    config_path.write_text(rendered, encoding="utf-8")

    if str(UPDATER_DIR) not in sys.path:
        sys.path.insert(0, str(UPDATER_DIR))
    from voc_updater.config import load_config

    config = load_config(config_path)
    assert str(config.paths.base_dir) == str(tmp_path / "base")
    assert str(config.paths.current_link) == str(tmp_path / "base" / "current")
    assert config.python.executable == tmp_path / "base" / ".venv" / "bin" / "python"
    assert config.foup.host == "10.1.2.3"
    assert config.foup.port == 65432
    assert config.services.systemctl_scope == "user"


def _install_env(tmp_path: Path, base: Path) -> dict:
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(tmp_path / "home"),
            "VOC_BASE": str(base),
            "VOC_SYSTEMD_USER_DIR": str(tmp_path / "systemd"),
            "VOC_AUTOSTART_DIR": str(tmp_path / "autostart"),
        }
    )
    return env


def test_install_sh_renders_everything_from_one_base(tmp_path: Path) -> None:
    base = tmp_path / "custom" / "voc"
    env = _install_env(tmp_path, base)
    env["QT_QPA_PLATFORM"] = "xcb"

    result = subprocess.run(
        ["bash", str(DEPLOY_DIR / "install.sh")],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "@VOC_BASE@" not in result.stdout

    systemd_dir = tmp_path / "systemd"
    gui = _read(systemd_dir / "voc-gui.service")
    assert f"WorkingDirectory={base}/current" in gui
    assert f"Environment=PYTHONPATH={base}/current/src" in gui
    assert f"ExecStart={base}/.venv/bin/python -m voc_app.gui.app" in gui
    assert "Environment=QT_QPA_PLATFORM=xcb" in gui
    assert not PLACEHOLDER_RE.search(gui)

    updater_service = _read(systemd_dir / "voc-updater.service")
    assert f"WorkingDirectory={base}/updater" in updater_service
    assert f"--config {base}/updater/config.yaml" in updater_service
    assert not PLACEHOLDER_RE.search(updater_service)

    path_unit = _read(systemd_dir / "voc-updater.path")
    assert f"PathExistsGlob={base}/updates/*.tar.gz" in path_unit
    assert not PLACEHOLDER_RE.search(path_unit)

    config_text = _read(base / "updater" / "config.yaml")
    assert not PLACEHOLDER_RE.search(config_text)
    assert f"base_dir: {base}" in config_text

    assert (base / "updater" / "update.py").is_file()
    assert (base / "updater" / "voc_updater").is_dir()
    assert (tmp_path / "autostart" / "voc-gui.desktop").is_file()
    for name in ("updates", "releases", "state", "work"):
        assert (base / name).is_dir()


def test_install_sh_preserves_existing_config(tmp_path: Path) -> None:
    base = tmp_path / "base"
    (base / "updater").mkdir(parents=True)
    config_path = base / "updater" / "config.yaml"
    original = "# 现场已改\npaths:\n  base_dir: /keep\n"
    config_path.write_text(original, encoding="utf-8")

    subprocess.run(
        ["bash", str(DEPLOY_DIR / "install.sh")],
        env=_install_env(tmp_path, base),
        capture_output=True,
        text=True,
        check=True,
    )

    assert config_path.read_text(encoding="utf-8") == original


def test_install_sh_force_config_overwrites(tmp_path: Path) -> None:
    base = tmp_path / "base"
    (base / "updater").mkdir(parents=True)
    config_path = base / "updater" / "config.yaml"
    config_path.write_text("# 旧配置\n", encoding="utf-8")

    subprocess.run(
        ["bash", str(DEPLOY_DIR / "install.sh"), "--force-config"],
        env=_install_env(tmp_path, base),
        capture_output=True,
        text=True,
        check=True,
    )

    content = config_path.read_text(encoding="utf-8")
    assert "# 旧配置" not in content
    assert f"base_dir: {base}" in content
