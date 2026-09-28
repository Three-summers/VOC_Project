# 变更记录

## 2026-09-28 — 配置/数据目录与采集健壮性

### 运行期状态移出 release
- 新增 `src/voc_app/app_paths.py`：统一解析系统配置与数据目录。优先级
  `VOC_SYSTEM_CONFIG` > `<数据目录>/system_config.json` > 包内默认；数据目录
  `VOC_DATA_DIR` > `paths.data_directory` > `$XDG_DATA_HOME/voc`。
- 首次启动把包内默认配置复制到数据目录，并把旧的 `gui/channel_config.json`
  迁移到数据目录；通道配置与采集日志不再写在源码目录，升级切换 `current`
  软链后不会丢失。
- `channel_config.py`、`csv_model.py`、`foup_acquisition.py`、`app.py` 改用数据目录。

### 硬编码移入 system_config.json
- 新增 `paths`、`acquisition`（host/port/模式/远端目录/socket 超时）、`loadport`
  （两个串口、波特率、超时、E84 桥接开关）、`update.state_file` 分区；
  `app.py` 从配置读取，环境变量仍优先。

### 采集与告警健壮性
- 流式接收阶段只有严格形如 `{PREFIX},{version}` 的报文才允许改写服务器类型，
  科学计数法数值、NaN/inf、报错文本与带前缀的数据包不再污染 `serverType`。
- 采集因接收超时或对端关闭而结束时，显式发出 `errorOccurred` 并写入状态文本，
  不再静默停止；新增 `socket_timeout_seconds` 配置。
- E84 GO 低电平告警改为边沿触发，避免每 200ms 刷屏。
- `AlarmModel.add_alarm` 在 `endInsertRows()` 之后再发 `countChanged`。
- 注释掉依赖空生成器列表的演示定时器，避免每秒空转。
- 通道数 → 前缀映射去重，只保留 `DEFAULT_PREFIX_BY_CHANNEL`。

### 测试与文档
- 新增 `conftest.py`：强制 `QT_QPA_PLATFORM=offscreen`（否则导入 `app.py` 会把平台
  写成 xcb，导致后续 `QGuiApplication` abort）并把数据目录指向临时目录。
- `pyproject.toml` 增加 `[tool.pytest.ini_options]`，限定收集 `tests` 与 `src`，
  不再把 `examples/` 联调脚本当测试。
- 新增 `tests/test_app_paths.py`、`foup_acquisition` 身份识别回归用例；
  裸跑 `pytest` 由崩溃（exit 134）变为 273 passed / 3 skipped。
- 重写 `docs/STRUCTURE.md`，补充 `ARCHITECTURE.md` 的配置/数据目录与测试环境章节，
  同步 GPIO 状态指示器设计文档的引脚与电平定义，删除失效的 `qml/.qmlls.ini`。

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
