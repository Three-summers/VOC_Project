"""升级流程的包选择与归档测试（A8）。

设计文档要求：每次只处理一个包；处理成功后移动到 processed/，失败后移动到
failed/，避免坏包反复触发、也避免第二次运行时又挑到同一个已处理过的包。
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.flow import archive_package, find_next_package


def _make_package(directory: Path, name: str, age_seconds: float = 0.0) -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"package")
    if age_seconds:
        stamp = time.time() - age_seconds
        os.utime(path, (stamp, stamp))
    return path


def test_find_next_package_picks_newest(tmp_path: Path) -> None:
    updates = tmp_path / "updates"
    _make_package(updates, "voc-update-1.0.0.tar.gz", age_seconds=120)
    newest = _make_package(updates, "voc-update-1.2.3.tar.gz", age_seconds=5)

    assert find_next_package(updates) == newest


def test_find_next_package_ignores_archived_subdirectories(tmp_path: Path) -> None:
    updates = tmp_path / "updates"
    _make_package(updates, "processed/voc-update-0.9.0.tar.gz")
    pending = _make_package(updates, "voc-update-1.2.3.tar.gz")

    assert find_next_package(updates) == pending


def test_find_next_package_raises_when_empty(tmp_path: Path) -> None:
    try:
        find_next_package(tmp_path / "updates")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError")


def test_archive_package_moves_to_processed(tmp_path: Path) -> None:
    updates = tmp_path / "updates"
    package = _make_package(updates, "voc-update-1.2.3.tar.gz")

    archived = archive_package(package, updates, success=True)

    assert not package.exists()
    assert archived == updates / "processed" / "voc-update-1.2.3.tar.gz"
    assert archived.exists()


def test_archive_package_moves_to_failed(tmp_path: Path) -> None:
    updates = tmp_path / "updates"
    package = _make_package(updates, "voc-update-1.2.3.tar.gz")

    archived = archive_package(package, updates, success=False)

    assert archived == updates / "failed" / "voc-update-1.2.3.tar.gz"
    assert archived.exists()


def test_archive_package_overwrites_previous_same_name(tmp_path: Path) -> None:
    updates = tmp_path / "updates"
    first = _make_package(updates, "voc-update-1.2.3.tar.gz")
    archive_package(first, updates, success=True)

    second = _make_package(updates, "voc-update-1.2.3.tar.gz")
    archived = archive_package(second, updates, success=True)

    assert archived.exists()
    assert not second.exists()


def test_archive_package_keeps_original_when_missing(tmp_path: Path) -> None:
    """包已经不在时不要抛异常，直接返回 None 即可"""
    updates = tmp_path / "updates"
    updates.mkdir()

    assert archive_package(updates / "gone.tar.gz", updates, success=True) is None
