# 任务完成检查清单
- 运行相关测试：至少 `python3 -m unittest tests/test_serial_device.py`；若修改 GUI/采集逻辑需补充或手动验证并记录。
- 记录验证：在 `.codex/testing.md` 写入执行的测试命令/结果；在 `verification.md` 说明无法执行的测试及风险。
- 自检：确认 QML/Python 改动与现有风格一致，Signal/Slot 属性同步更新；socket 连接在 stop/异常时关闭。
- 文档：必要时更新 `.codex/operations-log.md` 记录关键决策与工具调用，新增特性在相关 md/注释中写明日期与 Codex。
- Git 建议：检查 `git status` 确认改动范围，必要时分模块提交（不包含未授权变更）。