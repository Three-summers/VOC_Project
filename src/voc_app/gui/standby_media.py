"""待机媒体的配置、目录扫描和用户活动通知。"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import (
    QCoreApplication,
    QEvent,
    QObject,
    Property,
    QStandardPaths,
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

    def __init__(
        self, config_path: Path | None = None, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._config_path = config_path or self._default_config_path()
        self._media_directory = ""
        self._idle_timeout_seconds = self.DEFAULT_IDLE_TIMEOUT_SECONDS
        self._media_items: list[dict[str, str]] = []
        self._configuration_error = ""
        self._status_message = ""
        self._load_settings()
        self.refreshMedia()

        app = QCoreApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    @staticmethod
    def _default_config_path() -> Path:
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation
        )
        return Path(base) / "standby_media.json"

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

    @Slot(str)
    def setMediaDirectory(self, directory: str) -> None:
        url = QUrl(directory)
        raw_path = (
            url.toLocalFile()
            if url.isValid() and url.scheme() == "file"
            else directory
        )
        self._media_directory = (
            str(Path(raw_path).expanduser().resolve()) if raw_path else ""
        )
        self._save_settings()
        self.settingsChanged.emit()
        self.refreshMedia()

    @Slot(int)
    def setIdleTimeoutSeconds(self, seconds: int) -> None:
        if seconds <= 0:
            return
        self._idle_timeout_seconds = seconds
        self._save_settings()
        self.settingsChanged.emit()

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

    def _load_settings(self) -> None:
        if not self._config_path.exists():
            return
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            directory = data.get("mediaDirectory", "")
            seconds = data.get(
                "idleTimeoutSeconds", self.DEFAULT_IDLE_TIMEOUT_SECONDS
            )
            if (
                not isinstance(directory, str)
                or not isinstance(seconds, int)
                or isinstance(seconds, bool)
                or seconds <= 0
            ):
                raise ValueError("配置字段无效")
            self._media_directory = (
                str(Path(directory).expanduser().resolve()) if directory else ""
            )
            self._idle_timeout_seconds = seconds
        except (OSError, ValueError, json.JSONDecodeError):
            self._media_directory = ""
            self._idle_timeout_seconds = self.DEFAULT_IDLE_TIMEOUT_SECONDS
            self._configuration_error = "配置文件无效，已使用默认待机设置"

    def _save_settings(self) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._config_path.write_text(
                json.dumps(
                    {
                        "mediaDirectory": self._media_directory,
                        "idleTimeoutSeconds": self._idle_timeout_seconds,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self._configuration_error = ""
        except OSError:
            self._set_status_message("待机设置保存失败")

    def _set_status_message(self, message: str) -> None:
        if self._status_message != message:
            self._status_message = message
            self.statusMessageChanged.emit()
