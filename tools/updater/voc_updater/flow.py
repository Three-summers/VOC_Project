"""升级包的选择与归档。

设计文档要求：每次只处理一个包，处理完成后移动到 ``processed/`` 或
``failed/``。否则会出现两类现场问题：

- systemd ``.path`` 反复触发同一个坏包；
- 第二次运行时又挑到同一个已处理过的包，而 work 目录里的解包残留
  会让升级直接失败，形成"再也升级不了"的死局。
"""

from __future__ import annotations

import shutil
from pathlib import Path

PROCESSED_DIR_NAME = "processed"
FAILED_DIR_NAME = "failed"


def find_next_package(updates_dir: str | Path) -> Path:
    """返回待处理的最新升级包（按修改时间取最新）。"""
    directory = Path(updates_dir)
    packages = [path for path in directory.glob("*.tar.gz") if path.is_file()]
    if not packages:
        raise FileNotFoundError(f"no update package found in {directory}")
    return max(packages, key=lambda path: path.stat().st_mtime)


def archive_package(
    package_path: str | Path,
    updates_dir: str | Path,
    success: bool,
) -> Path | None:
    """把处理过的包移动到 processed/ 或 failed/。

    返回归档后的路径；包已不存在时返回 ``None``（不视为错误）。
    """
    source = Path(package_path)
    if not source.exists():
        return None
    target_dir = Path(updates_dir) / (
        PROCESSED_DIR_NAME if success else FAILED_DIR_NAME
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if target.exists() or target.is_symlink():
        target.unlink()
    shutil.move(str(source), str(target))
    return target
