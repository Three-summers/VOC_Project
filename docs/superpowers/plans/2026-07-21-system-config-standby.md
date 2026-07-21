# 系统配置化待机媒体 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将待机目录和超时迁移到自动重载的 `system_config.json`，同时将现有日志配置迁移到同一文件，并移除待机设置页面。

**Architecture:** `system_config.json` 放在 `src/voc_app/`，以 `logging` 和 `standby` 顶级分区承载系统设置。`StandbyMediaController` 只读取并监视 `standby` 分区，不再写用户配置；`logging_config.py` 从 `logging` 分区加载启动时日志设置。

**Tech Stack:** Python 3.11、PySide6 QtCore/QFileSystemWatcher、Qt Quick/QML、pytest、JSON。

## Global Constraints

- 配置文件必须为 `src/voc_app/system_config.json`；旧 `logging_config.json` 必须删除。
- 默认 `standby.media_directory` 必须是 `/home/say/code/python/VOC_Project/standby_res`。
- 默认 `standby.idle_timeout_seconds` 必须是 `60`，且只接受正整数。
- 运行中修改配置文件时，待机目录和超时必须自动重载；无效更新保留上一份有效设置。
- `logging` 分区继续支持模块级别和日志格式，但本次不热重载日志设置。
- 删除待机配置页面、子导航、路由和命令面板；不改变媒体播放、静音、循环或输入退出行为。
- 不修改用户当前未提交的 `.gitignore` 变更。

---

## File Structure

| File | Responsibility |
| --- | --- |
| `src/voc_app/system_config.json` | 唯一的系统配置，包含 `logging` 与 `standby` 分区。 |
| `src/voc_app/logging_config.py` | 读取 `logging` 分区并应用启动时日志配置。 |
| `src/voc_app/gui/app.py` | 在创建应用日志器前加载系统配置，并将同一文件路径传给待机控制器。 |
| `src/voc_app/gui/standby_media.py` | 从 `standby` 分区读取设置，并用 `QFileSystemWatcher` 热重载。 |
| `src/voc_app/gui/qml/InformationPanel.qml` | 移除待机动画配置子导航。 |
| `src/voc_app/gui/qml/views/ConfigView.qml` | 移除 `standby` 路由。 |
| `tests/test_logging_config.py` | 验证嵌套的 `logging` 分区。 |
| `tests/test_standby_media.py` | 验证系统配置启动读取、热重载与无效更新保留。 |
| `tests/test_qml_components.py` | 移除设置页断言，并验证待机页/路由/命令组件不存在。 |

### Task 1: 创建系统配置并迁移日志加载

**Files:**
- Create: `src/voc_app/system_config.json`
- Delete: `src/voc_app/logging_config.json`
- Modify: `src/voc_app/logging_config.py:1-30,252-289`
- Modify: `src/voc_app/gui/app.py:15-55,567-590`
- Modify: `tests/test_logging_config.py:179-200`

**Interfaces:**
- Consumes: 一个包含 `logging` 与 `standby` 对象的 JSON 文件。
- Produces: `configure_from_file(path)` 从 `data["logging"]` 应用格式和级别；`SYSTEM_CONFIG_PATH` 是 `src/voc_app/system_config.json` 的绝对路径。

- [ ] **Step 1: 写入失败的日志配置测试**

Replace the body of `TestModuleLevelConfig.test_configure_from_file` with this test, which requires the new nested section:

```python
    def test_configure_from_file_reads_logging_section(self) -> None:
        logging_config_module.setup_logging(level=logging.INFO, console=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "system_config.json"
            config_file.write_text(json.dumps({
                "logging": {
                    "levels": {"voc_app": "WARNING", "voc_app.gui": "ERROR"},
                    "format": "%(levelname)s:%(message)s",
                },
                "standby": {"media_directory": "/media", "idle_timeout_seconds": 60},
            }), encoding="utf-8")

            assert logging_config_module.configure_from_file(config_file) is True

        assert logging.getLogger("voc_app.gui").level == logging.ERROR
```

Add a source-level regression test in the same class:

```python
    def test_application_uses_system_config_before_creating_its_logger(self) -> None:
        app_source = (Path(__file__).resolve().parents[1] / "src" / "voc_app" / "gui" / "app.py").read_text(encoding="utf-8")

        assert 'SYSTEM_CONFIG_PATH = APP_DIR.parent / "system_config.json"' in app_source
        assert "configure_from_file(SYSTEM_CONFIG_PATH)" in app_source
```

- [ ] **Step 2: 运行测试确认其因旧扁平格式失败**

Run: `python3 -m pytest tests/test_logging_config.py::TestModuleLevelConfig -q`

Expected: `test_configure_from_file_reads_logging_section` fails because `configure_from_file` looks for `levels` at the document root, and the source-level test fails because `SYSTEM_CONFIG_PATH` is absent.

- [ ] **Step 3: 迁移 JSON 与日志加载实现**

Delete `src/voc_app/logging_config.json` and create `src/voc_app/system_config.json` with exactly:

```json
{
  "logging": {
    "levels": {
      "voc_app": "INFO",
      "voc_app.gui": "WARNING",
      "voc_app.gui.foup_acquisition": "DEBUG",
      "voc_app.loadport": "INFO"
    },
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  },
  "standby": {
    "media_directory": "/home/say/code/python/VOC_Project/standby_res",
    "idle_timeout_seconds": 60
  }
}
```

In `src/voc_app/logging_config.py`, update the module docstring example to `configure_from_file("system_config.json")`. Replace the configuration extraction in `configure_from_file` with:

```python
        config = json.loads(config_path.read_text(encoding="utf-8"))
        logging_config = config.get("logging")
        if not isinstance(logging_config, dict):
            return False

        levels = logging_config.get("levels")
        if isinstance(levels, dict):
            configure_levels(levels)

        format_string = logging_config.get("format")
        if isinstance(format_string, str):
            formatter = logging.Formatter(format_string)
            for handler in logging.getLogger("voc_app").handlers:
                handler.setFormatter(formatter)
        return True
```

In `src/voc_app/gui/app.py`, after `APP_DIR`, `PROJECT_ROOT`, and `SRC_DIR` are defined and before `logger = get_logger(__name__)`, use:

```python
from voc_app.logging_config import configure_from_file, get_logger

SYSTEM_CONFIG_PATH = APP_DIR.parent / "system_config.json"
configure_from_file(SYSTEM_CONFIG_PATH)
logger = get_logger(__name__)
```

Remove the earlier standalone `from voc_app.logging_config import get_logger` import so only this import remains.

- [ ] **Step 4: 运行日志迁移测试确认通过**

Run: `python3 -m pytest tests/test_logging_config.py::TestModuleLevelConfig -q`

Expected: all tests in `TestModuleLevelConfig` pass.

- [ ] **Step 5: 提交系统配置和日志迁移**

```bash
git add src/voc_app/system_config.json src/voc_app/logging_config.py src/voc_app/gui/app.py tests/test_logging_config.py
git add -u src/voc_app/logging_config.json
git commit -m "feat: add shared system config"
```

### Task 2: 从系统配置热重载待机媒体

**Files:**
- Modify: `src/voc_app/gui/standby_media.py:1-205`
- Modify: `src/voc_app/gui/app.py:580-590`
- Modify: `tests/test_standby_media.py:1-105`

**Interfaces:**
- Consumes: `system_config.json["standby"]` with `media_directory: str` and `idle_timeout_seconds: int`.
- Produces: `StandbyMediaController(config_path: Path, ...)`, read-only QML properties, `reloadConfig()` slot, and watcher-driven `settingsChanged`/`mediaChanged` signals.

- [ ] **Step 1: 写入失败的系统配置和热重载测试**

Replace the GUI-setter test with these tests. Keep the existing sorting, unreadable-directory and activity tests, but construct the controller from a system-config file.

```python
def write_system_config(path: Path, media_directory: Path, seconds: int) -> None:
    path.write_text(json.dumps({
        "logging": {"levels": {}, "format": "%(message)s"},
        "standby": {
            "media_directory": str(media_directory),
            "idle_timeout_seconds": seconds,
        },
    }), encoding="utf-8")


def test_reads_standby_settings_from_system_config(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "welcome.png").touch()
    config_path = tmp_path / "system_config.json"
    write_system_config(config_path, media_dir, 75)

    controller = StandbyMediaController(config_path=config_path)

    assert controller.mediaDirectory == str(media_dir.resolve())
    assert controller.idleTimeoutSeconds == 75
    assert controller.mediaCount == 1


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

    assert controller.mediaDirectory == str(media_dir.resolve())
    assert controller.idleTimeoutSeconds == 60
    assert "系统配置无效" in controller.statusMessage
```

- [ ] **Step 2: 运行测试确认当前控制器 API 不满足系统配置行为**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_standby_media.py -q`

Expected: tests fail because `reloadConfig` does not exist and the current controller expects `mediaDirectory`/`idleTimeoutSeconds` at the JSON root.

- [ ] **Step 3: 重构控制器为只读系统配置消费者**

Replace `QStandardPaths`, `setMediaDirectory`, `setIdleTimeoutSeconds`, `_save_settings`, and `_load_settings` with the following behavior:

```python
from PySide6.QtCore import QFileSystemWatcher

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

    @Slot(result=bool)
    def reloadConfig(self) -> bool:
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            standby = data.get("standby")
            if not isinstance(standby, dict):
                raise ValueError("缺少 standby 分区")
            directory = standby.get("media_directory")
            seconds = standby.get("idle_timeout_seconds")
            if not isinstance(directory, str) or not isinstance(seconds, int) or isinstance(seconds, bool) or seconds <= 0:
                raise ValueError("standby 分区无效")
        except (OSError, ValueError, json.JSONDecodeError):
            self._configuration_error = "系统配置无效，保留当前待机设置"
            self.refreshMedia()
            self._ensure_config_watched()
            return False

        next_directory = str(Path(directory).expanduser().resolve()) if directory else ""
        changed = next_directory != self._media_directory or seconds != self._idle_timeout_seconds
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
        file_name = str(self._config_path)
        parent_name = str(self._config_path.parent)
        if self._config_path.exists() and file_name not in watched:
            self._watcher.addPath(file_name)
        if self._config_path.parent.exists() and parent_name not in watched:
            self._watcher.addPath(parent_name)
```

Update `app.py` construction to:

```python
standby_media_controller = StandbyMediaController(config_path=SYSTEM_CONFIG_PATH)
```

Keep `refreshMedia`, QML properties, media filtering, and `eventFilter` unchanged. In `refreshMedia`, preserve the current scan message but prefix it with `_configuration_error` when present. Do not leave setter slots in the controller because no GUI can modify the configuration.

- [ ] **Step 4: 运行控制器测试确认通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_standby_media.py -q`

Expected: all standby controller tests pass.

- [ ] **Step 5: 提交热重载控制器**

```bash
git add src/voc_app/gui/standby_media.py src/voc_app/gui/app.py tests/test_standby_media.py
git commit -m "feat: reload standby settings from system config"
```

### Task 3: 删除待机设置 GUI 和所有引用

**Files:**
- Delete: `src/voc_app/gui/qml/views/config/ConfigStandbyPage.qml`
- Delete: `src/voc_app/gui/qml/commands/Config_standbyCommands.qml`
- Modify: `src/voc_app/gui/qml/InformationPanel.qml:23-28`
- Modify: `src/voc_app/gui/qml/views/ConfigView.qml:12-21`
- Modify: `tests/test_qml_components.py:429-562`

**Interfaces:**
- Consumes: 待机媒体仍由主窗口的 `standbyMediaController` 只读属性驱动。
- Produces: 配置子导航只包含 `loadport` 和 `foup`；没有 `standby` 子页或命令组件。

- [ ] **Step 1: 将现有待机设置页测试改成失败的移除测试**

Delete `TestStandbyMediaSettingsQml` and replace it with:

```python
class TestStandbyMediaSettingsRemoved(unittest.TestCase):
    def test_config_navigation_has_no_standby_page(self):
        info_content = (ROOT_DIR / "src" / "voc_app" / "gui" / "qml" / "InformationPanel.qml").read_text(encoding="utf-8")
        config_content = (ROOT_DIR / "src" / "voc_app" / "gui" / "qml" / "views" / "ConfigView.qml").read_text(encoding="utf-8")

        self.assertNotIn('{ key: "standby", title: "待机动画" }', info_content)
        self.assertNotIn('case "standby": return "config/ConfigStandbyPage.qml"', config_content)

    def test_standby_settings_qml_files_are_removed(self):
        qml_root = ROOT_DIR / "src" / "voc_app" / "gui" / "qml"

        self.assertFalse((qml_root / "views" / "config" / "ConfigStandbyPage.qml").exists())
        self.assertFalse((qml_root / "commands" / "Config_standbyCommands.qml").exists())
```

- [ ] **Step 2: 运行测试确认旧页面仍存在**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_qml_components.py::TestStandbyMediaSettingsRemoved -q`

Expected: both tests fail because the current navigation still exposes `standby` and both QML files exist.

- [ ] **Step 3: 删除页面、命令组件和路由**

Remove this entry from `InformationPanel.qml`:

```qml
            { key: "standby", title: "待机动画" }
```

Remove this `ConfigView.qml` switch branch:

```qml
            case "standby": return "config/ConfigStandbyPage.qml"
```

Delete `ConfigStandbyPage.qml` and `Config_standbyCommands.qml` with `apply_patch`; do not delete any media overlay or `main.qml` idle-timer code.

- [ ] **Step 4: 运行 QML 移除测试确认通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_qml_components.py::TestStandbyMediaSettingsRemoved -q`

Expected: `2 passed`.

- [ ] **Step 5: 运行完整回归和离屏启动检查**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests -q`

Expected: all tests pass.

Run: `QT_QPA_PLATFORM=offscreen timeout 5s python3 src/voc_app/gui/app.py`

Expected: process exits with `124` only because `timeout` ends the GUI event loop; output contains no QML errors mentioning `standby`, `ConfigStandbyPage`, or `Config_standbyCommands`.

- [ ] **Step 6: 提交 GUI 清理**

```bash
git add src/voc_app/gui/qml/InformationPanel.qml src/voc_app/gui/qml/views/ConfigView.qml tests/test_qml_components.py
git add -u src/voc_app/gui/qml/views/config/ConfigStandbyPage.qml src/voc_app/gui/qml/commands/Config_standbyCommands.qml
git commit -m "refactor: configure standby from system config"
```

## Plan Self-Review

### Spec coverage

- 新的 `system_config.json` 名称、嵌套日志/待机分区与指定默认目录：Task 1。
- 日志模块与 GUI 启动路径同步迁移：Task 1。
- 待机配置运行时重载和无效配置保留：Task 2。
- 删除全部待机设置 GUI 引用：Task 3。
- 不修改播放行为与全套回归验证：Task 2 和 Task 3。

### Placeholder scan

每项任务都含有精确文件、测试、失败预期、实现代码、验证命令和提交命令；没有未分配的实现工作。

### Interface consistency

`SYSTEM_CONFIG_PATH` 在 Task 1 中定义，并在 Task 2 用于构建 `StandbyMediaController`。控制器公开 `reloadConfig()`、原有只读 QML 属性和原有信号；主窗口继续使用这些属性和信号，因此无需改变媒体覆盖层接口。
