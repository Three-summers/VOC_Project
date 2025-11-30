# Testing Log

## $ts
- Executor: Codex
- Command: `QT_QPA_PLATFORM=offscreen python gui_main/main.py`
- Result: Failed
- Output Summary: Python 报错 `ModuleNotFoundError: No module named 'RPi'`，源于 new_loadport/GPIOController 依赖 RPi.GPIO（树莓派环境），当前容器未安装该硬件库，导致线程初始化中断。
- Notes: 由于缺少 RPi.GPIO 与硬件接口，本地无法完成真实 GUI 启动；已确认导入路径修复并将 new_loadport 线程桥接到 GUI。建议在具备硬件依赖的目标环境复测。

## 2025-11-19T10:02:05+08:00
- Executor: Codex
- Command: `cd gui_main && QT_QPA_PLATFORM=offscreen python3 main.py`
- Result: Failed
- Output Summary: Python 报错 `ModuleNotFoundError: No module named 'PySide6'`，当前容器未安装 GUI 运行所需的 PySide6 依赖，无法继续加载 QML。
- Notes: 该环境缺失 PySide6 库，无法进行 GUI 冒烟测试。待安装依赖后应重新运行以验证新子页面与命令面板。

## 2025-11-19T15:02:30+08:00
- Executor: Codex
- Command: `QT_QPA_PLATFORM=offscreen python3 new_loadport/main.py`
- Result: Failed
- Output Summary: `ModuleNotFoundError: No module named 'PySide6'`，环境未安装 PySide6，无法实测线程启动。
- Notes: 串口模块已移除，因此错误与之前不同（仅缺少 PySide6）。待目标环境安装 PySide6 后再运行确认。

## 2025-11-19T16:09:05+08:00
- Executor: Codex
- Command: `python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures，验证 GenericSerialDevice 发送命令与响应处理正常。

## 2025-11-19T17:08:45+08:00
- Executor: Codex
- Command: `python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures，验证重构后包路径可用。

## 2025-11-24T10:50:00+08:00
- Executor: Codex
- Command: `python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures，確認 GenericSerialDevice 行為在最新結構掃描後仍可運作。

## 2025-11-25T10:50:06+08:00
- Executor: Codex
- Command: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen python3 -m voc_app.gui.app`
- Result: Failed
- Output Summary: `ModuleNotFoundError: No module named 'PySide6'`，当前环境缺少 GUI 运行依赖；但已确认未再出现 `RPi.GPIO` 相关导入错误。
- Notes: 需在具有 PySide6 的环境复测；本次目标仅验证注释 loadport 后阻塞原因已切换为 PySide6 缺失。

## 2025-11-25T10:50:08+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures，确认串口模块在移除 loadport 依赖后仍工作正常。
- Notes: 作为基础回归，证明注释硬件代码未影响核心串口逻辑。

## 2025-11-25T11:25:19+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；证明新增工业风 UI 改动未影响现有串口逻辑。
- Notes: 继续保留 GUI 冒烟测试的 PySide6 缺失风险，待依赖安装后再运行。

## 2025-11-25T14:39:20+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；确认串口模块改动后仍稳定。
- Notes: GUI 功能仍需在具备 PySide6 的环境中运行以验证 FOUP 采集流程。

## 2025-11-25T15:24:32+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；确认 socket 模块修改未影响串口功能。
- Notes: GUI 验证仍需 PySide6 环境配合。 

## 2025-11-26T15:06:25+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；确认 FOUP 采集清空/滑动窗口改动未影响串口模块。
- Notes: GUI 仍需在具备 PySide6 的环境验证曲线展示效果。

## 2025-11-27T16:00:17+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；确认调色子页改动未影响串口模块。
- Notes: GUI 调色交互需在具备 PySide6 的环境中手动验证。

## 2025-11-30T19:29:14+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；本次 FOUP IP 可配置改动未影响串口模块。
- Notes: GUI 验证仍需具备 PySide6/显示环境，命令面板新 TextField 需在目标设备上手动检查。

## 2025-11-30T19:40:54+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；将 IP 输入改为对话框后，串口单测仍通过。
- Notes: GUI 对话框交互需在具备 PySide6/显示的设备上手动验证。

## 2025-11-30T19:49:53+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；补充 QtQuick.Layouts 导入后回归依旧通过。
- Notes: QML 模块加载需在目标环境验证，PySide6 仍缺。 

## 2025-11-30T19:57:00+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；移除当前 IP 文本并调整弹窗居中计算后回归正常。
- Notes: GUI 弹窗居中效果需在 PySide6 环境确认。 

## 2025-11-30T20:03:00+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；改为使用 Qt.application.activeWindow 居中对话框后回归无变化。
- Notes: 需在 PySide6 环境确认弹窗位置与告警/登录对齐效果。 

## 2025-11-30T20:10:00+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；在 onOpened 强制以 window 尺寸计算 x/y 居中后回归正常。
- Notes: 请在 PySide6 环境再次查看弹窗位置，应与登录弹窗居中一致。 

## 2025-11-30T20:15:00+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；对话框锚定信息面板（无则回退窗口）后回归正常。
- Notes: 请在 PySide6 环境核对弹窗位置是否与登录弹窗一致；依赖信息面板尺寸居中。 

## 2025-11-30T20:22:00+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；标题消息区域与时间区域等宽（绑定 dateFrame）后回归正常。
- Notes: GUI 顶栏视觉需在 PySide6 环境确认。 

## 2025-11-30T20:28:00+08:00
- Executor: Codex
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: Passed
- Output Summary: 1 test, 0 failures；增高消息行、加宽消息区域并放大加粗字号后回归正常。
- Notes: 请在 PySide6 环境确认标题消息区高度与字号是否满足工业面板需求。 
