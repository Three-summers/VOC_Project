# 变更记录

## 2025-12-09 — Codex

### 后端采集与命令流程
- `src/voc_app/gui/foup_acquisition.py` 增加采集模式：`operationMode`（normal/test）、`normalModeRemotePath`（默认 `Log`）、`serverVersion` 属性与信号，UI 可直接绑定。
- 引入类型化命令表：VOC/Noise（兼容 PID）分别映射 sample_normal/sample_test/start/stop，未匹配时回退 VOC 指令。
- 建连后先发送 `get_function_version_info`，根据返回如 `VOC_Version,V1.0.0` / `Noise_Humility,V1.0.0` 设置服务类型与版本。
- 测试模式：发送采样类型与 start 命令后进入实时接收循环；ACK 应答仅提示不解析；停止时发送类型化 stop 并关闭 socket。
- 正常模式：发送采样类型后使用独立连接通过 `Client.get_file` 下载远端目录（默认 `Log`）到本地 `gui/Log`，完成后状态提示文件数量。
- ACK 兼容：收到 “ACK” 直接更新状态不再作为数据解析；版本字符串会被识别避免误当数据点。

### E84 自动触发
- `src/voc_app/loadport/e84_passive.py` 新增 `all_keys_set` 信号，三键同时为真且边沿触发时发射。
- `src/voc_app/loadport/e84_thread.py` 转发 `all_keys_set`；`src/voc_app/gui/app.py` 启动时可创建 LoadportBridge 监听信号并自动调用采集（默认启用，可通过环境变量 `DISABLE_E84_BRIDGE=1|true|yes` 关闭，异常会打印警告不阻塞）。

### 配置页 UI
- `src/voc_app/gui/qml/commands/Config_foupCommands.qml` 增加模式切换下拉、正常模式远端目录输入，按钮根据模式显示“下载日志”或“开始采集”，展示服务类型与版本。
- `src/voc_app/gui/qml/views/config/ConfigFoupPage.qml` 状态区新增模式、服务器类型、版本号展示。

### 测试与验证
- 执行：`python3 -m unittest tests/test_serial_device.py` ✅ 通过。
- 未验证：正常模式远端下载、真实服务器版本应答、E84 三键自动触发需在具备服务端与硬件的环境实机测试，相关风险已在 `verification.md` 说明。
