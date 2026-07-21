from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QUrl

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.standby_media import StandbyMediaController


def test_defaults_to_60_seconds_and_no_directory(tmp_path: Path) -> None:
    controller = StandbyMediaController(config_path=tmp_path / "standby.json")

    assert controller.idleTimeoutSeconds == 60
    assert controller.mediaDirectory == ""
    assert controller.mediaCount == 0
    assert controller.statusMessage == "未选择待机媒体目录"


def test_refresh_filters_and_sorts_direct_media_files(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    for name in ("z-last.mp4", "B-middle.JPG", "a-first.png", "notes.txt"):
        (media_dir / name).touch()
    (media_dir / "child").mkdir()
    (media_dir / "child" / "ignored.png").touch()
    controller = StandbyMediaController(config_path=tmp_path / "standby.json")

    controller.setMediaDirectory(str(media_dir))

    assert [item["kind"] for item in controller.mediaItems] == ["image", "image", "video"]
    assert [QUrl(item["url"]).fileName() for item in controller.mediaItems] == [
        "a-first.png",
        "B-middle.JPG",
        "z-last.mp4",
    ]
    assert controller.statusMessage == "已找到 3 个待机媒体文件"


def test_settings_persist_and_invalid_timeout_keeps_last_valid_value(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "standby.json"
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    controller = StandbyMediaController(config_path=config_path)

    controller.setMediaDirectory(str(media_dir))
    controller.setIdleTimeoutSeconds(75)
    controller.setIdleTimeoutSeconds(0)
    reloaded = StandbyMediaController(config_path=config_path)

    assert controller.idleTimeoutSeconds == 75
    assert reloaded.mediaDirectory == str(media_dir.resolve())
    assert reloaded.idleTimeoutSeconds == 75
    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "mediaDirectory": str(media_dir.resolve()),
        "idleTimeoutSeconds": 75,
    }


def test_invalid_saved_config_uses_safe_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "standby.json"
    config_path.write_text("{not json", encoding="utf-8")

    controller = StandbyMediaController(config_path=config_path)

    assert controller.idleTimeoutSeconds == 60
    assert controller.mediaDirectory == ""
    assert controller.statusMessage == "配置文件无效，已使用默认待机设置；未选择待机媒体目录"


def test_directory_read_error_produces_no_media_and_a_safe_message(
    tmp_path: Path, monkeypatch
) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    controller = StandbyMediaController(config_path=tmp_path / "standby.json")

    def fail_to_iterate(_: Path):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "iterdir", fail_to_iterate)
    controller.setMediaDirectory(str(media_dir))

    assert controller.mediaCount == 0
    assert controller.statusMessage == "待机媒体目录不存在或不可访问"


def test_application_input_event_emits_activity_signal(tmp_path: Path) -> None:
    controller = StandbyMediaController(config_path=tmp_path / "standby.json")
    received: list[bool] = []
    controller.activityDetected.connect(lambda: received.append(True))

    controller.eventFilter(QObject(), QEvent(QEvent.Type.KeyPress))

    assert received == [True]
