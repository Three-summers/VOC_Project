from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_voc_gui_service_uses_current_symlink_and_module_entrypoint() -> None:
    content = (ROOT_DIR / "deploy" / "systemd" / "user" / "voc-gui.service").read_text(
        encoding="utf-8"
    )
    assert "WorkingDirectory=/home/kasp/Project/voc_project/current" in content
    assert "-m voc_app.gui.app" in content
    assert "Restart=on-failure" in content


def test_autostart_desktop_starts_systemd_service_not_python() -> None:
    content = (ROOT_DIR / "deploy" / "autostart" / "voc-gui.desktop").read_text(
        encoding="utf-8"
    )
    assert "Exec=systemctl --user start voc-gui.service" in content
    assert "python" not in content


def test_updater_path_watches_updates_directory() -> None:
    content = (ROOT_DIR / "deploy" / "systemd" / "user" / "voc-updater.path").read_text(
        encoding="utf-8"
    )
    assert "PathExistsGlob=/home/kasp/Project/voc_project/updates/*.tar.gz" in content


def test_updater_service_runs_independent_script() -> None:
    content = (ROOT_DIR / "deploy" / "systemd" / "user" / "voc-updater.service").read_text(
        encoding="utf-8"
    )
    assert "/home/kasp/Project/voc_project/updater/update.py" in content
    assert "--config /home/kasp/Project/voc_project/updater/config.yaml" in content
