# Testing Log

## 2025-12-05
- Executor: Codex
- Scope: Config Foup 图表布局自适应（两列滚动）
- Commands: 未执行 GUI 相关自动化测试
- Result: 未运行
- Details: 当前环境缺少 PySide6，无法启动 QML 界面验证 1/2/3/4/5+ 通道布局；仅进行了代码审查。待具备 PySide6 和采集数据源后在目标设备手动确认布局与性能。

- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures；确认 Python 层改动未影响串口回归。GUI 布局仍需在安装 PySide6 的环境手动验证。

- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures；在动态通道数配置刷新改动后回归，Python 层串口逻辑仍稳定。GUI 需实机验证动态通道数切换时标题/单位更新。 

## 2025-12-09
- Executor: Codex
- Scope: 采集模式切换、版本查询、E84 自动触发桥接
- Command: `python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures；确认基础串口模块未受新改动影响。FOUP 正常/测试模式切换、版本查询、日志下载与 E84 自动建连需在具备服务端与硬件的环境手动验证。正常模式下载流程未在无服务器环境下执行。 
