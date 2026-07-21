from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QUrl
from PySide6.QtTest import QTest

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.standby_media import StandbyMediaController


def get_app() -> QCoreApplication:
    app = QCoreApplication.instance()
    return app if app is not None else QCoreApplication([])


def write_system_config(path: Path, media_directory: Path, seconds: int) -> None:
    path.write_text(
        json.dumps(
            {
                "logging": {"levels": {}, "format": "%(message)s"},
                "standby": {
                    "media_directory": str(media_directory),
                    "idle_timeout_seconds": seconds,
                },
            }
        ),
        encoding="utf-8",
    )


def test_reads_standby_settings_from_system_config(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "welcome.png").touch()
    config_path = tmp_path / "system_config.json"
    write_system_config(config_path, media_dir, 75)

    controller = StandbyMediaController(config_path=config_path)

    assert controller.idleTimeoutSeconds == 75
    assert controller.mediaDirectory == str(media_dir.resolve())
    assert controller.mediaCount == 1


def test_refresh_filters_and_sorts_direct_media_files(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    for name in ("z-last.mp4", "B-middle.JPG", "a-first.png", "notes.txt"):
        (media_dir / name).touch()
    (media_dir / "child").mkdir()
    (media_dir / "child" / "ignored.png").touch()
    config_path = tmp_path / "system_config.json"
    write_system_config(config_path, media_dir, 60)
    controller = StandbyMediaController(config_path=config_path)

    assert [item["kind"] for item in controller.mediaItems] == ["image", "image", "video"]
    assert [QUrl(item["url"]).fileName() for item in controller.mediaItems] == [
        "a-first.png",
        "B-middle.JPG",
        "z-last.mp4",
    ]
    assert controller.statusMessage == "已找到 3 个待机媒体文件"


def test_reload_config_applies_new_settings_and_emits_change(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    (second_dir / "movie.mp4").touch()
    config_path = tmp_path / "system_config.json"
    write_system_config(config_path, first_dir, 60)
    controller = StandbyMediaController(config_path=config_path)
    changed: list[bool] = []
    controller.settingsChanged.connect(lambda: changed.append(True))

    write_system_config(config_path, second_dir, 90)
    assert controller.reloadConfig() is True

    assert changed == [True]
    assert controller.mediaDirectory == str(second_dir.resolve())
    assert controller.idleTimeoutSeconds == 90
    assert [item["kind"] for item in controller.mediaItems] == ["video"]


def test_invalid_reload_keeps_previous_effective_settings(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    config_path = tmp_path / "system_config.json"
    write_system_config(config_path, media_dir, 60)

    controller = StandbyMediaController(config_path=config_path)
    config_path.write_text('{"standby": {"idle_timeout_seconds": 0}}', encoding="utf-8")

    assert controller.reloadConfig() is False
    assert controller.idleTimeoutSeconds == 60
    assert controller.mediaDirectory == str(media_dir.resolve())
    assert "系统配置无效" in controller.statusMessage


def test_file_watcher_applies_changed_system_config(tmp_path: Path) -> None:
    app = get_app()
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    config_path = tmp_path / "system_config.json"
    write_system_config(config_path, first_dir, 60)
    controller = StandbyMediaController(config_path=config_path)
    changed: list[bool] = []
    controller.settingsChanged.connect(lambda: changed.append(True))

    write_system_config(config_path, second_dir, 90)
    for _ in range(20):
        if changed:
            break
        QTest.qWait(25)
        app.processEvents()

    assert changed
    assert controller.mediaDirectory == str(second_dir.resolve())
    assert controller.idleTimeoutSeconds == 90


def test_directory_read_error_produces_no_media_and_a_safe_message(
    tmp_path: Path, monkeypatch
) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    config_path = tmp_path / "system_config.json"
    write_system_config(config_path, media_dir, 60)
    controller = StandbyMediaController(config_path=config_path)

    def fail_to_iterate(_: Path):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "iterdir", fail_to_iterate)
    controller.refreshMedia()

    assert controller.mediaCount == 0
    assert controller.statusMessage == "待机媒体目录不存在或不可访问"


def test_application_input_event_emits_activity_signal(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    config_path = tmp_path / "system_config.json"
    write_system_config(config_path, media_dir, 60)
    controller = StandbyMediaController(config_path=config_path)
    received: list[bool] = []
    controller.activityDetected.connect(lambda: received.append(True))

    controller.eventFilter(QObject(), QEvent(QEvent.Type.KeyPress))

    assert received == [True]
