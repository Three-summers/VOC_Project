"""pytest 全局环境准备。

两个必须的隔离动作：

1. **强制 offscreen Qt 平台**：``voc_app.gui.app`` 在导入期会调用
   ``apply_performance_settings()``，在 WSL2 且没有 ``/dev/dxg`` 的环境下会把
   ``QT_QPA_PLATFORM`` 写成 ``xcb``。一旦该变量被写入，后续任何
   ``QGuiApplication`` 创建都会因 xcb 插件不可用而 abort（exit 134）。
   测试必须在导入任何被测模块之前把平台固定为 offscreen。
2. **隔离运行期数据目录**：``voc_app.app_paths`` 默认把可变状态放在
   ``$XDG_DATA_HOME/voc``。测试统一指向临时目录，避免读写真实用户数据。
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_DATA_DIR = Path(tempfile.mkdtemp(prefix="voc-test-data-"))
os.environ.setdefault("VOC_DATA_DIR", str(_DATA_DIR))
atexit.register(shutil.rmtree, _DATA_DIR, ignore_errors=True)
