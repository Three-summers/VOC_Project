"""待机媒体的配置、目录扫描和用户活动通知。"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import (
    QCoreApplication,
    QEvent,
    QFileSystemWatcher,
    QObject,
    Property,
    QUrl,
    Signal,
    Slot,
)


class StandbyMediaController(QObject):
    """向 QML 提供持久化的待机媒体设置和已排序的媒体文件。"""

    DEFAULT_IDLE_TIMEOUT_SECONDS = 60
    IMAGE_EXTENSIONS = frozenset({".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"})
    VIDEO_EXTENSIONS = frozenset({".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"})
    INPUT_EVENT_TYPES = frozenset(
        {
            QEvent.Type.KeyPress,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.Wheel,
        }
    )

    settingsChanged = Signal()
    mediaChanged = Signal()
    statusMessageChanged = Signal()
    activityDetected = Signal()

    def __init__(self, config_path: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config_path = Path(config_path)
        self._media_directory = ""
        self._idle_timeout_seconds = self.DEFAULT_IDLE_TIMEOUT_SECONDS
        self._media_items: list[dict[str, str]] = []
        self._configuration_error = ""
        self._status_message = ""
        self._watcher: QFileSystemWatcher | None = None
        self.reloadConfig()

        app = QCoreApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            self._watcher = QFileSystemWatcher(self)
            self._watcher.fileChanged.connect(self._on_config_path_changed)
            self._watcher.directoryChanged.connect(self._on_config_path_changed)
            self._ensure_config_watched()

    @Property(str, notify=settingsChanged)
    def mediaDirectory(self) -> str:
        return self._media_directory

    @Property(int, notify=settingsChanged)
    def idleTimeoutSeconds(self) -> int:
        return self._idle_timeout_seconds

    @Property("QVariantList", notify=mediaChanged)
    def mediaItems(self) -> list[dict[str, str]]:
        return list(self._media_items)

    @Property(int, notify=mediaChanged)
    def mediaCount(self) -> int:
        return len(self._media_items)

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Slot(result=bool)
    def reloadConfig(self) -> bool:
        """从系统配置读取待机设置，失败时保留最近一次有效设置。"""

        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("系统配置不是对象")
            standby = data.get("standby")
            if not isinstance(standby, dict):
                raise ValueError("缺少 standby 分区")
            directory = standby.get("media_directory")
            seconds = standby.get("idle_timeout_seconds")
            if (
                not isinstance(directory, str)
                or not isinstance(seconds, int)
                or isinstance(seconds, bool)
                or seconds <= 0
            ):
                raise ValueError("standby 分区无效")
        except (OSError, ValueError, json.JSONDecodeError):
            self._configuration_error = "系统配置无效，保留当前待机设置"
            self.refreshMedia()
            self._ensure_config_watched()
            return False

        next_directory = (
            str(Path(directory).expanduser().resolve()) if directory else ""
        )
        changed = (
            next_directory != self._media_directory
            or seconds != self._idle_timeout_seconds
        )
        self._media_directory = next_directory
        self._idle_timeout_seconds = seconds
        self._configuration_error = ""
        self.refreshMedia()
        if changed:
            self.settingsChanged.emit()
        self._ensure_config_watched()
        return True

    @Slot(str)
    def _on_config_path_changed(self, _path: str) -> None:
        self.reloadConfig()

    def _ensure_config_watched(self) -> None:
        if self._watcher is None:
            return

        watched = set(self._watcher.files()) | set(self._watcher.directories())
        config_name = str(self._config_path)
        parent_name = str(self._config_path.parent)
        if self._config_path.exists() and config_name not in watched:
            self._watcher.addPath(config_name)
        if self._config_path.parent.exists() and parent_name not in watched:
            self._watcher.addPath(parent_name)

    @Slot()
    def refreshMedia(self) -> None:
        directory = Path(self._media_directory)
        items: list[dict[str, str]] = []
        if not self._media_directory:
            message = "未选择待机媒体目录"
        elif not directory.is_dir():
            message = "待机媒体目录不存在或不可访问"
        else:
            try:
                entries = sorted(
                    directory.iterdir(), key=lambda item: item.name.casefold()
                )
            except OSError:
                message = "待机媒体目录不存在或不可访问"
            else:
                for path in entries:
                    if not path.is_file():
                        continue
                    suffix = path.suffix.casefold()
                    if suffix in self.IMAGE_EXTENSIONS:
                        kind = "image"
                    elif suffix in self.VIDEO_EXTENSIONS:
                        kind = "video"
                    else:
                        continue
                    items.append(
                        {
                            "url": QUrl.fromLocalFile(str(path.resolve())).toString(),
                            "kind": kind,
                        }
                    )
                message = (
                    f"已找到 {len(items)} 个待机媒体文件"
                    if items
                    else "目录中没有受支持的待机媒体文件"
                )

        if self._configuration_error:
            message = f"{self._configuration_error}；{message}"
        self._media_items = items
        self._set_status_message(message)
        self.mediaChanged.emit()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in self.INPUT_EVENT_TYPES:
            self.activityDetected.emit()
        return False

    def _set_status_message(self, message: str) -> None:
        if self._status_message != message:
            self._status_message = message
            self.statusMessageChanged.emit()
