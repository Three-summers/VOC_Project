"""R08：通道配置弹窗"显示第三通道却保存到第一通道"。

入口固定调用 ``openWithChannel(0)``，它会重置 ``selectedChannel``，但 ComboBox
仍保留上一次的 ``currentIndex``。保存以 ``selectedChannel`` 为准，于是界面显示
第三通道、实际改写第一通道。

回归口径：无论重开多少次、选择器此前停在哪一项，选择器显示与保存通道必须一致。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Property, QObject, Qt, QUrl, Signal, Slot
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlExpression

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

QML_DIR = ROOT_DIR / "src" / "voc_app" / "gui" / "qml"
CONFIG_QML = QML_DIR / "commands" / "Config_foupCommands.qml"


class _FakeAcquisition(QObject):
    channelCountChanged = Signal()
    hostChanged = Signal()
    operationModeChanged = Signal()
    runningChanged = Signal()
    statusMessageChanged = Signal()
    channelConfigChanged = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._channel_count = 3
        self._host = "127.0.0.1"
        self._operation_mode = "test"
        self._running = False
        self._status = "idle"
        self.saved: list[tuple] = []

    @Property(int, notify=channelCountChanged)
    def channelCount(self) -> int:  # noqa: D102
        return self._channel_count

    @Property(str, notify=hostChanged)
    def host(self) -> str:  # noqa: D102
        return self._host

    @Property(str, notify=operationModeChanged)
    def operationMode(self) -> str:  # noqa: D102
        return self._operation_mode

    @Property(bool, notify=runningChanged)
    def running(self) -> bool:  # noqa: D102
        return self._running

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:  # noqa: D102
        return self._status

    @Slot(int, result=str)
    def getUnit(self, idx: int) -> str:  # noqa: D102
        return f"unit{idx}"

    @Slot(int, result=float)
    def getOocUpper(self, idx: int) -> float:  # noqa: D102
        return 70.0 + idx

    @Slot(int, result=float)
    def getOocLower(self, idx: int) -> float:  # noqa: D102
        return 20.0 + idx

    @Slot(int, result=float)
    def getOosUpper(self, idx: int) -> float:  # noqa: D102
        return 80.0 + idx

    @Slot(int, result=float)
    def getOosLower(self, idx: int) -> float:  # noqa: D102
        return 10.0 + idx

    @Slot(int, result=float)
    def getTarget(self, idx: int) -> float:  # noqa: D102
        return 50.0 + idx

    @Slot(int, str)
    def setChannelUnit(self, idx: int, unit: str) -> None:  # noqa: D102
        self.saved.append(("unit", idx, unit))

    @Slot(int, float, float, float, float, float)
    def setChannelLimits(self, idx, a, b, c, d, e) -> None:  # noqa: D102
        self.saved.append(("limits", idx, a, b, c, d, e))


def _eval(engine: QQmlApplicationEngine, obj: QObject, expression: str):
    expr = QQmlExpression(engine.rootContext(), obj, expression)
    value = expr.evaluate()
    return value


@pytest.fixture()
def channel_dialog(qapp):
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    acquisition = _FakeAcquisition()
    engine.rootContext().setContextProperty("foupAcquisition", acquisition)

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(CONFIG_QML)))
    assert component.status() != QQmlComponent.Status.Error, [
        error.toString() for error in component.errors()
    ]
    root = component.create()
    assert root is not None

    dialog = root.findChild(QObject, "limitDialog")
    selector = root.findChild(QObject, "channelSelector")
    assert dialog is not None, "未找到通道配置弹窗"
    assert selector is not None, "未找到通道路选择器"

    # 给 Popup 一个可见的锚点，避免无窗口时 open() 失败
    root.setProperty("informationPanelRef", root)
    qapp.processEvents()
    yield root, dialog, selector, engine, acquisition
    root.deleteLater()
    qapp.processEvents()


def test_reopen_syncs_selector_with_selected_channel(channel_dialog) -> None:
    _root, dialog, selector, engine, _acquisition = channel_dialog

    # 操作员选择第三通道
    _eval(engine, dialog, "loadChannel(2)")
    assert dialog.property("selectedChannel") == 2
    assert selector.property("currentIndex") == 2

    # 关闭后再从固定入口打开（openWithChannel(0)）
    _eval(engine, dialog, "close()")
    _eval(engine, dialog, "openWithChannel(0)")

    assert dialog.property("selectedChannel") == 0
    assert selector.property("currentIndex") == 0, (
        "重开后选择器必须与将要保存的通道一致"
    )


def test_selector_and_saved_channel_stay_consistent(channel_dialog) -> None:
    _root, dialog, selector, engine, acquisition = channel_dialog

    _eval(engine, dialog, "openWithChannel(0)")
    _eval(engine, dialog, "loadChannel(1)")
    assert selector.property("currentIndex") == 1

    # "确定"按钮保存的是 limitDialog.selectedChannel，这里用同一来源执行保存
    acquisition.setChannelLimits(
        int(dialog.property("selectedChannel")), 1.0, 2.0, 3.0, 4.0, 5.0
    )

    limits_call = [call for call in acquisition.saved if call[0] == "limits"]
    assert limits_call and limits_call[-1][1] == 1, (
        f"保存的通道必须与选择器一致，实际保存: {limits_call}"
    )


def test_open_clamps_channel_to_available_count(channel_dialog) -> None:
    _root, dialog, selector, engine, _acquisition = channel_dialog

    _eval(engine, dialog, "loadChannel(9)")

    assert dialog.property("selectedChannel") == 2, "越界通道必须收敛到最后一个可用通道"
    assert selector.property("currentIndex") == 2
