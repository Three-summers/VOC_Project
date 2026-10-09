# 变更记录

## 2026-10-08 — 部署路径收敛（部署脚手架）

### 路径只填一次
- `deploy/systemd/user/*.service|*.path` 改为 `*.in` 模板，现场路径统一用
  `@VOC_BASE@` / `@VOC_PYTHON@` / `@QT_QPA_PLATFORM@` 占位符，不再写死
  `/home/kasp/Project/voc_project`。
- 新增 `deploy/install.sh`：`VOC_BASE` 是唯一路径入口，负责创建部署目录、渲染并
  安装 systemd 用户单元与 autostart、生成 `updater/config.yaml`、按需复制升级器，
  并执行 `systemctl --user daemon-reload`。幂等，默认不覆盖现场 `config.yaml`
  （`--force-config` 才覆盖）。
- 新增 `deploy/updater/config.yaml.example`：升级器配置模板，`install.sh` 渲染，
  也可手工复制后替换 `@...@` 占位符；渲染结果能被 `load_config` 直接解析。
- 新增 `deploy/README.md`：脚手架用法与可配置项说明。
- 回归测试 `tests/test_deploy_templates.py` 重写：校验模板占位符、渲染后无残留
  占位符、`config.yaml` 可被真实 `load_config` 解析，以及 `install.sh` 在自定义
  基目录下一次性渲染全部产物。

## 2026-10-08 — 审查遗留项与升级事务化（第三轮）

### 界面与图表
- 通道配置弹窗：选择器与保存通道共用唯一状态，重开后不再“显示第三通道、保存到
  第一通道”（R08）。
- 图表报警颜色按限界显示开关着色，与后台 `_check_channel_limits` 规则一致；
  `system_config.json` 新增 `chart.alarm_color_sync_with_limits`，置 false 时可关闭
  同步，允许“界面红色提示但不设后台报警”（R22）。
- 图表 Y 轴下界按数据量纲决定：含负值时显示负半轴，全正数据仍从 0 起；新增
  `chart.y_axis_mode`（`auto`/`zero`）控制策略（R23）。

### 线程、串口与模型
- 串口读线程异常退出后 `is_connected` 变为 False，释放失效串口并发出失效通知，
  `connect()` 可重建串口与读线程（R16）。
- E84 控制器线程停止时排队执行清理并有界等待线程退出，控制器定时器在所属线程内
  停止，停止通知幂等（R17）。
- QML Socket 桥接改用主线程队列信号清除 busy，不再“执行一次后永久忙碌”（R33）。
- 全零/近零时域信号不再被频谱归一化成满量程 0 dB（R34）。

### 升级器
- systemd 服务通过 `PYTHONPATH=<base>/current/src` 加载当前 release；安装器校验
  MainPID 的 `/proc/<pid>/cwd` 属于目标 release（R13）。
- 停止 → 切换 current → 启动 → 确认事务化，任何异常回滚旧版本；stop 后必须确认
  服务 inactive，并确认 MainPID 已更换（R14/R27）。
- ssh 与 scp 共用 `-i <key>`、`BatchMode=yes`、`StrictHostKeyChecking=accept-new`（R26）。
- 升级状态区分实际运行版本与目标版本（`loadport_target_version`），整个升级尝试
  纳入 failed 生命周期，不再残留 running 或沿用上一次 succeeded（R29/R30）。

### 安全联锁与设备切换（第二批）
- E84 握手撤销（GO/CS_0/VALID 变低）时撤回 READY/L_REQ/U_REQ 并回到 IDLE，
  不再对已撤销的请求继续响应（R01）。
- 分离“检测到载具”（任意一键）与“完整落位”（三键全落）：Load 完成必须三键全落
  才撤回 L_REQ（R02）。
- 执行机构本机连接/写入失败与设备上报错误一样发出 `serialErrorDetected`，进入
  E84 故障锁存并拉低 READY（R03）。
- `E84Controller.stop()` 回到 IDLE 并撤回 READY/L_REQ/U_REQ、关闭 LOAD/UNLOAD LED
  （R04）。
- 修改 FOUP IP 时在 E84 控制锁内关闭旧控制连接并清除旧身份，控制命令不再发往
  旧地址（R20）。
- R01–R04 行为固定，不新增配置项。

### 测试与验证
- 新增 12 个回归测试文件；全量 `pytest` → 439 passed / 3 skipped。
- `conftest.py` 的 `qapp` 改用 `QApplication`：QtCharts 的 `ChartView` 在只有
  `QGuiApplication` 时离屏实例化会段错误。
- 真实 Ubuntu 主机（systemd --user）验证升级、服务重启确认与回滚，证据见
  `docs/reviews/evidence/2026-09-29/host-upgrade-verification.txt`，
  脚本见 `tools/host_upgrade_verification/`。

## 2026-09-29 — 与下位机源码对齐（第二轮）

### 采集时序
- E84 Unload 改为**先启动采集、再断开对插并解锁**（对插承载到 FOUP 的网络通道，
  原顺序会让 START 发不到下位机）。
- E84 Unload 启动前补发 `{prefix}_sample_type_normal`：下位机 `VOC_Sample_Type`
  是全局标志，只有 normal 模式 start 才写 CSV；此前一次测试模式会让整趟飞行不记录数据。
- 已知前缀时跳过版本查询，控制连接独立 1.5s 超时且不重连重试，避免拖住机械动作。
- E84 Load 改为**先下载日志、再发送 STOP**：下位机收到 stop 后 5 秒反挂载 SD 分区。

### 数据正确性与可见性
- 数据帧改为整帧校验（任一字段非法即丢弃），避免跳过字段造成通道错位与通道数误判。
- 流式身份识别收紧：科学计数法、NaN/inf、报错文本、带前缀数据包不再污染 serverType。
- OOC/OOS 越限产生报警（文案稳定，复用 60s 去重）；采集错误此前完全未接线，现已
  通过主线程 `GuiAlarmNotifier` 写入报警列表与消息栏。
- 设备 CSV 时间戳（`YYYY-MM-DD HH:MM:SS.mmm`）可解析、表头去空格、NaN 不画点。
- 下载完成自动刷新文件列表并打开最新文件；0 个文件按错误上报。
- 空 CSV 在 DataLog 页显示"该文件没有数据点"。
- 远端日志目录默认改为下位机真实路径 `/home/root/files`。

### E84 状态机
- `WAIT_L_REQ`/`WAIT_U_REQ` 现在消费 60s 超时，卡死可恢复（原为死代码）。
- load/unload 方向在握手瞬间锁定，不再按实时 `FOUP_status` 二次判定。

### 升级器
- FOUP 不可达不再阻塞 Loadport 升级，状态写 failed 而非永久 running。
- 选最新包并归档到 `processed/`/`failed/`；解析器清理残留 work 目录。
- 安装时把 `loadport/manifest.json` 写进 release，版本比较恢复有效。

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
