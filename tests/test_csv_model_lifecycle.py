"""CSV 模型生命周期测试（R24 / R25）。

R24：反复加载 CSV 会累积旧的 ColumnData 子对象（仍挂在模型上），长时间切换
     日志会持续占用内存。
R25：打开零字节 CSV 后，文件名/点数/提示仍停留在上一个文件，界面无法解释空图。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.csv_model import CsvFileManager

GOOD_CSV = "Time,Value\n0,10\n1,12\n"
EMPTY_CSV = ""


def _drain(app) -> None:
    """模拟真实事件循环：处理排队事件并回收 deleteLater 的对象。"""
    from PySide6.QtCore import QCoreApplication, QEvent

    app.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    time.sleep(0.01)


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture()
def csv_env(qapp, tmp_path):
    log_dir = tmp_path / "Log"
    _write(log_dir / "good.csv", GOOD_CSV)
    _write(log_dir / "empty.csv", EMPTY_CSV)
    return CsvFileManager(log_dir=log_dir), qapp


def test_repeated_parsing_does_not_accumulate_column_objects(csv_env) -> None:
    manager, app = csv_env
    for _ in range(10):
        manager.parse_csv_file("good.csv")
        _drain(app)

    children = manager.dataModel.children()
    assert len(children) == 1, (
        f"旧列对象没有被释放，仍有 {len(children)} 个：{[c.metaObject().className() for c in children]}"
    )


def test_repeated_parsing_between_files_keeps_only_current_columns(csv_env) -> None:
    manager, app = csv_env
    for _ in range(5):
        manager.parse_csv_file("good.csv")
        _drain(app)

    assert len(manager.dataModel.children()) == 1
    assert manager.dataModel.rowCount() == 1  # 一列数据


def test_opening_zero_byte_file_updates_visible_state(csv_env) -> None:
    manager, app = csv_env

    manager.parse_csv_file("good.csv")
    _drain(app)
    assert manager.dataPointCount == 2
    assert manager.parseMessage == ""

    manager.parse_csv_file("empty.csv")
    _drain(app)

    assert manager.activeFile == "empty.csv", "打开空文件后仍显示上一个文件名"
    assert manager.dataPointCount == 0
    assert manager.parseMessage == "该文件没有数据点"
    assert manager.dataModel.rowCount() == 0
