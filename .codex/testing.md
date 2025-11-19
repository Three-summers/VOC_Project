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
