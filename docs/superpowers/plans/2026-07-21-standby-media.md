# 待机媒体播放 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在用户无操作达到可配置的秒数后，全屏且静音地按文件名顺序循环播放设置目录中的图片和视频；任意用户输入立即返回应用。

**Architecture:** `StandbyMediaController` 负责 JSON 配置、直接目录扫描、文件排序与 Qt 全局输入事件通知，并作为 QML 上下文属性公开。QML 使用主窗口计时器和独立的 `StandbyMediaOverlay` 显示层播放控制器提供的媒体项；设置子页只调用控制器，不直接读写文件系统。

**Tech Stack:** Python 3.11、PySide6 QtCore/QML/QtMultimedia、Qt Quick Controls、pytest、QML 离屏加载测试。

## Global Constraints

- 默认待机超时必须是 **60 秒**；设置值只接受正整数秒。
- 配置页必须允许选择媒体目录，且设置在重启后恢复。
- 只扫描已选择目录的直接普通文件；不递归子目录；按文件名不区分大小写升序循环。
- 图片格式只接受 `.bmp`、`.gif`、`.jpeg`、`.jpg`、`.png`、`.webp`；视频格式只接受 `.avi`、`.m4v`、`.mkv`、`.mov`、`.mp4`、`.webm`。
- 视频始终静音；图片固定展示 **10,000 ms**。
- 目录为空、缺失、不可访问或没有受支持文件时，显示设置页提示且绝不打开待机层。
- 任何鼠标移动、鼠标点击、鼠标滚轮或键盘按下均视为用户活动；待机时先关闭覆盖层、停止视频，再重启计时。
- 不添加第三方依赖，不播放音频，不支持随机循环、子目录、网络媒体或外部播放器。

---

## File Structure

| File | Responsibility |
| --- | --- |
| `src/voc_app/gui/standby_media.py` | 配置加载/保存、目录扫描与排序、媒体元数据、Qt 全局输入事件过滤。 |
| `src/voc_app/gui/app.py` | 创建控制器并注册为 `standbyMediaController`。 |
| `src/voc_app/gui/qml/components/StandbyMediaOverlay.qml` | 不透明全屏媒体循环、图片计时、视频静音和播放失败跳过。 |
| `src/voc_app/gui/qml/main.qml` | 无操作计时、控制器活动信号连接、待机层启停。 |
| `src/voc_app/gui/qml/views/config/ConfigStandbyPage.qml` | 目录选择、秒数编辑和媒体状态显示。 |
| `src/voc_app/gui/qml/views/ConfigView.qml` | 将 `standby` 子页键映射到设置页。 |
| `src/voc_app/gui/qml/InformationPanel.qml` | 在配置子导航中公开“待机动画”。 |
| `tests/test_standby_media.py` | 控制器的配置、过滤、排序和输入通知测试。 |
| `tests/test_qml_components.py` | 待机 QML 组件、主窗口连接与设置页路由的回归测试。 |

### Task 1: StandbyMediaController 的持久化与目录扫描

**Files:**
- Create: `src/voc_app/gui/standby_media.py`
- Create: `tests/test_standby_media.py`
- Modify: `src/voc_app/gui/app.py:36-48, 580-590`

**Interfaces:**
- Consumes: `QStandardPaths.AppConfigLocation`；QML 传入的本地路径或 `file:` URL。
- Produces: `StandbyMediaController`，具有 `mediaDirectory: str`、`idleTimeoutSeconds: int`、`mediaItems: QVariantList`、`mediaCount: int`、`statusMessage: str` 属性；`setMediaDirectory(str)`、`setIdleTimeoutSeconds(int)`、`refreshMedia()` 槽；`activityDetected()` 信号。

- [ ] **Step 1: Write the failing controller tests**

Create `tests/test_standby_media.py` with real temporary directories and files:

```python
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QUrl

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
        "a-first.png", "B-middle.JPG", "z-last.mp4"
    ]
    assert controller.statusMessage == "已找到 3 个待机媒体文件"


def test_settings_persist_and_invalid_timeout_keeps_last_valid_value(tmp_path: Path) -> None:
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


def test_directory_read_error_produces_no_media_and_a_safe_message(tmp_path: Path, monkeypatch) -> None:
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
```

- [ ] **Step 2: Run the test to verify it fails for the missing module**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_standby_media.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'voc_app.gui.standby_media'`.

- [ ] **Step 3: Implement the smallest controller that satisfies the tests**

Create `src/voc_app/gui/standby_media.py` with these concrete definitions:

```python
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
    DEFAULT_IDLE_TIMEOUT_SECONDS = 60
    IMAGE_EXTENSIONS = frozenset({".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"})
    VIDEO_EXTENSIONS = frozenset({".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"})
    INPUT_EVENT_TYPES = frozenset({
        QEvent.Type.KeyPress,
        QEvent.Type.MouseButtonPress,
        QEvent.Type.MouseMove,
        QEvent.Type.Wheel,
    })

    settingsChanged = Signal()
    mediaChanged = Signal()
    statusMessageChanged = Signal()
    activityDetected = Signal()

    def __init__(self, config_path: Path | None = None, parent: QObject | None = None):
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
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
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
        raw_path = url.toLocalFile() if url.isValid() and url.scheme() == "file" else directory
        self._media_directory = str(Path(raw_path).expanduser().resolve()) if raw_path else ""
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
                entries = sorted(directory.iterdir(), key=lambda item: item.name.casefold())
            except OSError:
                message = "待机媒体目录不存在或不可访问"
            else:
                for path in entries:
                    if not path.is_file():
                        continue
                    suffix = path.suffix.casefold()
                    kind = "image" if suffix in self.IMAGE_EXTENSIONS else "video" if suffix in self.VIDEO_EXTENSIONS else ""
                    if kind:
                        items.append({"url": QUrl.fromLocalFile(str(path.resolve())).toString(), "kind": kind})
                message = f"已找到 {len(items)} 个待机媒体文件" if items else "目录中没有受支持的待机媒体文件"
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
            seconds = data.get("idleTimeoutSeconds", self.DEFAULT_IDLE_TIMEOUT_SECONDS)
            if not isinstance(directory, str) or not isinstance(seconds, int) or isinstance(seconds, bool) or seconds <= 0:
                raise ValueError("配置字段无效")
            self._media_directory = str(Path(directory).expanduser().resolve()) if directory else ""
            self._idle_timeout_seconds = seconds
        except (OSError, ValueError, json.JSONDecodeError):
            self._media_directory = ""
            self._idle_timeout_seconds = self.DEFAULT_IDLE_TIMEOUT_SECONDS
            self._configuration_error = "配置文件无效，已使用默认待机设置"

    def _save_settings(self) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._config_path.write_text(json.dumps({
                "mediaDirectory": self._media_directory,
                "idleTimeoutSeconds": self._idle_timeout_seconds,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            self._configuration_error = ""
        except OSError:
            self._set_status_message("待机设置保存失败")

    def _set_status_message(self, message: str) -> None:
        if self._status_message != message:
            self._status_message = message
            self.statusMessageChanged.emit()
```

In `src/voc_app/gui/app.py`, add the import with the other GUI controller imports and register the controller before `engine.load`:

```python
from voc_app.gui.standby_media import StandbyMediaController

# after engine = QQmlApplicationEngine()
standby_media_controller = StandbyMediaController()
engine.rootContext().setContextProperty("standbyMediaController", standby_media_controller)
```

- [ ] **Step 4: Run the focused controller tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_standby_media.py -q`

Expected: `6 passed`.

- [ ] **Step 5: Commit the controller work**

```bash
git add src/voc_app/gui/standby_media.py src/voc_app/gui/app.py tests/test_standby_media.py
git commit -m "feat: add standby media controller"
```

### Task 2: 全屏媒体覆盖层和无操作计时

**Files:**
- Create: `src/voc_app/gui/qml/components/StandbyMediaOverlay.qml`
- Modify: `src/voc_app/gui/qml/main.qml:1-145`
- Modify: `tests/test_qml_components.py:390-end`

**Interfaces:**
- Consumes: `standbyMediaController.mediaItems`, `mediaCount`, `idleTimeoutSeconds`, `refreshMedia()` 和 `activityDetected()`。
- Produces: `StandbyMediaOverlay.start()`、`stop()` 和 `visible`；主窗口的 `restartIdleTimer()`。

- [ ] **Step 1: Write failing QML component tests**

Append these tests to `tests/test_qml_components.py`:

```python
class TestStandbyMediaQml(unittest.TestCase):
    def setUp(self):
        self.overlay_path = ROOT_DIR / "src" / "voc_app" / "gui" / "qml" / "components" / "StandbyMediaOverlay.qml"
        self.main_path = ROOT_DIR / "src" / "voc_app" / "gui" / "qml" / "main.qml"

    def test_overlay_component_exists_and_uses_silent_media_player(self):
        content = self.overlay_path.read_text(encoding="utf-8")

        self.assertIn("import QtMultimedia", content)
        self.assertIn("function start()", content)
        self.assertIn("function stop()", content)
        self.assertIn("MediaPlayer", content)
        self.assertIn("muted: true", content)
        self.assertIn("imageDurationMs: 10000", content)

    def test_overlay_component_loads(self):
        app = get_app()
        engine = QQmlApplicationEngine()
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(self.overlay_path)))

        self.assertNotEqual(component.status(), QQmlComponent.Error, [error.toString() for error in component.errors()])
        overlay = component.create()
        self.assertIsNotNone(overlay)
        overlay.deleteLater()
        app.processEvents()

    def test_main_window_wires_idle_timer_to_controller_activity(self):
        content = self.main_path.read_text(encoding="utf-8")

        self.assertIn("id: idleTimer", content)
        self.assertIn("standbyMediaController.idleTimeoutSeconds * 1000", content)
        self.assertIn("standbyMediaController.refreshMedia()", content)
        self.assertIn("function onActivityDetected()", content)
        self.assertIn("standbyMediaOverlay.stop()", content)
```

- [ ] **Step 2: Run the tests to verify they fail because the component is missing**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_qml_components.py::TestStandbyMediaQml -q`

Expected: failure at `read_text()` with `FileNotFoundError` for `StandbyMediaOverlay.qml`.

- [ ] **Step 3: Implement the overlay and main-window integration**

Create `src/voc_app/gui/qml/components/StandbyMediaOverlay.qml`:

```qml
import QtQuick
import QtMultimedia

Item {
    id: overlay
    anchors.fill: parent
    z: 10000
    visible: false
    focus: visible

    property var mediaItems: []
    property int imageDurationMs: 10000
    property int mediaIndex: -1
    property int consecutiveFailures: 0

    function start() {
        if (!mediaItems || mediaItems.length === 0)
            return
        visible = true
        mediaIndex = -1
        consecutiveFailures = 0
        advance()
        forceActiveFocus()
    }

    function stop() {
        imageTimer.stop()
        player.stop()
        player.source = ""
        image.source = ""
        visible = false
    }

    function advance() {
        if (!visible || !mediaItems || mediaItems.length === 0) {
            stop()
            return
        }
        imageTimer.stop()
        player.stop()
        mediaIndex = (mediaIndex + 1) % mediaItems.length
        const entry = mediaItems[mediaIndex]
        image.visible = entry.kind === "image"
        videoOutput.visible = entry.kind === "video"
        if (entry.kind === "image") {
            image.source = entry.url
            imageTimer.restart()
        } else {
            player.source = entry.url
            player.play()
        }
    }

    function skipFailedItem() {
        if (!visible)
            return
        consecutiveFailures += 1
        if (consecutiveFailures >= mediaItems.length) {
            stop()
            return
        }
        advance()
    }

    Rectangle {
        anchors.fill: parent
        color: "black"
    }

    Image {
        id: image
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        visible: false
        onStatusChanged: {
            if (status === Image.Ready)
                overlay.consecutiveFailures = 0
            else if (status === Image.Error)
                overlay.skipFailedItem()
        }
    }

    VideoOutput {
        id: videoOutput
        anchors.fill: parent
        fillMode: VideoOutput.PreserveAspectFit
        visible: false
    }

    Timer {
        id: imageTimer
        interval: overlay.imageDurationMs
        repeat: false
        onTriggered: overlay.advance()
    }

    MediaPlayer {
        id: player
        videoOutput: videoOutput
        audioOutput: AudioOutput { muted: true }
        onMediaStatusChanged: {
            if (mediaStatus === MediaPlayer.EndOfMedia) {
                overlay.consecutiveFailures = 0
                overlay.advance()
            }
        }
        onErrorOccurred: overlay.skipFailedItem()
    }
}
```

In `src/voc_app/gui/qml/main.qml`, directly after the existing startup `Timer`, add the single-shot idle timer and controller connection. Add the overlay as the last child of `ApplicationWindow`, so it is above the main layout:

```qml
    function restartIdleTimer() {
        if (standbyMediaOverlay.visible)
            standbyMediaOverlay.stop()
        idleTimer.restart()
    }

    Timer {
        id: idleTimer
        interval: Math.max(1, standbyMediaController.idleTimeoutSeconds) * 1000
        repeat: false
        running: true
        onTriggered: {
            standbyMediaController.refreshMedia()
            if (standbyMediaController.mediaCount > 0) {
                standbyMediaOverlay.mediaItems = standbyMediaController.mediaItems
                standbyMediaOverlay.start()
            } else {
                restart()
            }
        }
    }

    Connections {
        target: standbyMediaController
        function onActivityDetected() {
            root.restartIdleTimer()
        }
        function onSettingsChanged() {
            root.restartIdleTimer()
        }
    }

    Components.StandbyMediaOverlay {
        id: standbyMediaOverlay
        mediaItems: standbyMediaController.mediaItems
    }
```

Keep the overlay after the main `ColumnLayout`, not inside it, so normal UI layout cannot constrain its size. Do not add a QML `MouseArea` that could intercept normal controls: the controller's Qt application event filter emits `activityDetected` while returning `false`, so every input reaches its original destination.

- [ ] **Step 4: Run the focused QML tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_qml_components.py::TestStandbyMediaQml -q`

Expected: `3 passed` with no QML component errors.

- [ ] **Step 5: Commit the display and timer work**

```bash
git add src/voc_app/gui/qml/components/StandbyMediaOverlay.qml src/voc_app/gui/qml/main.qml tests/test_qml_components.py
git commit -m "feat: add standby media overlay"
```

### Task 3: 待机动画设置页与配置导航

**Files:**
- Create: `src/voc_app/gui/qml/views/config/ConfigStandbyPage.qml`
- Modify: `src/voc_app/gui/qml/views/ConfigView.qml:12-17`
- Modify: `src/voc_app/gui/qml/InformationPanel.qml:23-28`
- Modify: `tests/test_qml_components.py:end`

**Interfaces:**
- Consumes: Task 1 的 `standbyMediaController` 属性和槽。
- Produces: 配置子页键 `standby`；用户可更新目录和正整数秒数。

- [ ] **Step 1: Write failing configuration-page tests**

Append these tests to `tests/test_qml_components.py`:

```python
class TestStandbyMediaSettingsQml(unittest.TestCase):
    def test_config_navigation_exposes_standby_page(self):
        info_content = (ROOT_DIR / "src" / "voc_app" / "gui" / "qml" / "InformationPanel.qml").read_text(encoding="utf-8")
        config_content = (ROOT_DIR / "src" / "voc_app" / "gui" / "qml" / "views" / "ConfigView.qml").read_text(encoding="utf-8")

        self.assertIn('{ key: "standby", title: "待机动画" }', info_content)
        self.assertIn('case "standby": return "config/ConfigStandbyPage.qml"', config_content)

    def test_standby_config_page_selects_folder_and_saves_timeout(self):
        page_path = ROOT_DIR / "src" / "voc_app" / "gui" / "qml" / "views" / "config" / "ConfigStandbyPage.qml"
        content = page_path.read_text(encoding="utf-8")

        self.assertIn("FolderDialog", content)
        self.assertIn("standbyMediaController.setMediaDirectory", content)
        self.assertIn("IntValidator", content)
        self.assertIn("standbyMediaController.setIdleTimeoutSeconds", content)
        self.assertIn("standbyMediaController.statusMessage", content)
```

- [ ] **Step 2: Run the tests to verify they fail before the page and route exist**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_qml_components.py::TestStandbyMediaSettingsQml -q`

Expected: one assertion failure for the absent `standby` navigation key and one `FileNotFoundError` for `ConfigStandbyPage.qml`.

- [ ] **Step 3: Implement the route and settings page**

In `src/voc_app/gui/qml/InformationPanel.qml`, replace the commented theme entry in the `"Config"` array with:

```qml
            { key: "standby", title: "待机动画" }
```

In `src/voc_app/gui/qml/views/ConfigView.qml`, add this branch before `default`:

```qml
            case "standby": return "config/ConfigStandbyPage.qml"
```

Create `src/voc_app/gui/qml/views/config/ConfigStandbyPage.qml`:

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../../components" as Components

Item {
    id: root

    FolderDialog {
        id: folderDialog
        title: "选择待机媒体目录"
        onAccepted: standbyMediaController.setMediaDirectory(selectedFolder.toString())
    }

    Rectangle {
        anchors.fill: parent
        radius: Components.UiTheme.radius(18)
        color: Components.UiTheme.color("panel")
        border.color: Components.UiTheme.color("outline")

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Components.UiTheme.spacing("xl")
            spacing: Components.UiTheme.spacing("lg")

            Text {
                text: "待机动画"
                font.pixelSize: Components.UiTheme.fontSize("title")
                font.bold: true
                color: Components.UiTheme.color("textPrimary")
            }

            Text {
                text: "无操作达到设定秒数后，按文件名顺序静音循环播放此目录中的图片和视频。"
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Components.UiTheme.color("textSecondary")
            }

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "媒体目录"
                    color: Components.UiTheme.color("textPrimary")
                }
                Text {
                    Layout.fillWidth: true
                    text: standbyMediaController.mediaDirectory || "尚未选择"
                    elide: Text.ElideMiddle
                    color: Components.UiTheme.color("textSecondary")
                }
                Components.CustomButton {
                    text: "选择目录"
                    onClicked: folderDialog.open()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "待机秒数"
                    color: Components.UiTheme.color("textPrimary")
                }
                TextField {
                    id: timeoutField
                    Layout.preferredWidth: 180
                    text: String(standbyMediaController.idleTimeoutSeconds)
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: IntValidator { bottom: 1; top: 2147483647 }
                    onEditingFinished: {
                        if (acceptableInput)
                            standbyMediaController.setIdleTimeoutSeconds(Number(text))
                        else
                            text = String(standbyMediaController.idleTimeoutSeconds)
                    }
                }
                Text {
                    text: "秒"
                    color: Components.UiTheme.color("textSecondary")
                }
            }

            Text {
                Layout.fillWidth: true
                text: standbyMediaController.statusMessage
                wrapMode: Text.WordWrap
                color: standbyMediaController.mediaCount > 0
                    ? Components.UiTheme.color("accentSuccess")
                    : Components.UiTheme.color("accentWarning")
            }

            Item { Layout.fillHeight: true }
        }
    }
}
```

Ensure `TextField.text` updates after another component changes the setting by adding this handler at page root:

```qml
    Connections {
        target: standbyMediaController
        function onSettingsChanged() {
            timeoutField.text = String(standbyMediaController.idleTimeoutSeconds)
        }
    }
```

- [ ] **Step 4: Run the settings-page tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_qml_components.py::TestStandbyMediaSettingsQml -q`

Expected: `2 passed`.

- [ ] **Step 5: Run the complete relevant regression suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_standby_media.py tests/test_qml_components.py -q`

Expected: all selected tests pass with no QML load errors or warnings about missing `standbyMediaController`.

- [ ] **Step 6: Commit the settings UI and integration**

```bash
git add src/voc_app/gui/qml/views/config/ConfigStandbyPage.qml src/voc_app/gui/qml/views/ConfigView.qml src/voc_app/gui/qml/InformationPanel.qml tests/test_qml_components.py
git commit -m "feat: add standby media settings"
```

## Plan Self-Review

### Spec coverage

- Configurable 60-second default and persisted directory/seconds: Task 1 and Task 3.
- Direct-file filtering and filename-ordered image/video loop: Task 1 and Task 2.
- Silent video, 10-second image duration, black fullscreen layer and failed-media skipping: Task 2.
- All required user input exits/restarts waiting: Task 1 event filter and Task 2 signal connection.
- Missing/empty/unreadable directory behavior: Task 1 and Task 3 status display.
- Automated coverage: Task 1 controller tests and Tasks 2–3 QML tests.

### Placeholder scan

The plan contains no unassigned implementation work: every task names its files, interfaces, test command, expected result, implementation content, and commit command.

### Interface consistency

`StandbyMediaController` is registered as `standbyMediaController`, exposes `mediaItems`, `mediaCount`, `idleTimeoutSeconds`, `statusMessage`, `setMediaDirectory`, `setIdleTimeoutSeconds`, `refreshMedia`, and `activityDetected`, and every QML consumer uses these exact names. `StandbyMediaOverlay` exposes `start` and `stop`, and `main.qml` uses those exact names.
