"""界面清理测试：频谱页下线 + 删除无实际作用的按钮。"""

from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
QML_ROOT = ROOT_DIR / "src" / "voc_app" / "gui" / "qml"

# 这些页面里的按钮只打 console.log，没有任何后端动作
DEAD_BUTTON_FILES = (
    "commands/Status_foupCommands.qml",
    "commands/Config_loadportCommands.qml",
    "commands/HelpCommands.qml",
    "commands/StatusCommands.qml",
    "commands/ConfigCommands.qml",
)


def _read(relative: str) -> str:
    return (QML_ROOT / relative).read_text(encoding="utf-8")


def _without_comment_lines(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("//")
    )


def test_spectrum_subpage_is_removed_from_sub_navigation() -> None:
    info = _without_comment_lines(_read("InformationPanel.qml"))
    assert '"spectrum"' not in info, "频谱子页仍出现在子导航配置里"


def test_status_view_does_not_route_to_spectrum_page() -> None:
    """频谱组件定义保留（便于恢复），但不能再有生效的路由。"""
    view = _read("views/StatusView.qml")
    live = _without_comment_lines(view)
    assert 'currentSubPage === "spectrum"' not in live, "StatusView 仍会切到频谱页"
    assert "spectrumComponent" in view, "频谱组件定义被删除，恢复时需要重写"


def test_command_placeholder_component_exists() -> None:
    assert (QML_ROOT / "components" / "CommandPlaceholder.qml").exists()


def test_dead_buttons_are_removed() -> None:
    for relative in DEAD_BUTTON_FILES:
        text = _read(relative)
        assert "CustomButton" not in text, f"{relative} 仍有按钮"
        assert "console.log" not in _without_comment_lines(text), (
            f"{relative} 仍有只打日志的按钮"
        )
        assert "CommandPlaceholder" in text, f"{relative} 未使用统一占位提示"


def test_functional_command_panels_are_untouched() -> None:
    """功能性命令面板不能被误删"""
    assert "loadportActuatorController" in _read("commands/Status_loadportCommands.qml")
    assert "startAcquisition" in _read("commands/Config_foupCommands.qml")
    assert "closeAlarms" in _read("commands/AlarmsCommands.qml")
    assert "plotSelectedColumns" in _read("commands/DataLogCommands.qml")
