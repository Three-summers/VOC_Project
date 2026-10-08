# 2026-09-29 审查报告修复状态

- 对应报告：[2026-09-29-code-review.md](2026-09-29-code-review.md)
- 更新日期：2026-10-08
- 本轮提交：`e0ac126`（代码、回归测试、真实主机验证证据）
- 说明：本文件只记录**修复状态**，不修改原报告正文。行号可能随后续改动变化，
  请按问题编号与函数名追踪。

## 一、已修复

### 1. 上一批（A 组，13 项 + R31）

| 编号 | 结论 | 提交 | 关键改动 |
| --- | --- | --- | --- |
| R05 | 已修复 | `aab5a39` | `Client.get_file` 归一化并校验服务端路径必须落在请求目录内，创建父目录后再用 `realpath` 复核，拒绝符号链接逃逸 |
| R06 | 已修复 | `aab5a39` | 先写同目录 `.part` 临时文件，字节数校验通过后原子替换；失败清理临时文件并保留原日志 |
| R10 | 已修复 | `8dc32d4` | 逐项解包，拒绝符号链接/硬链接/特殊文件，父目录自建，不再使用 `extractall` |
| R11 | 已修复 | `8dc32d4` | 版本字符串格式校验 + release 目标必须是 `releases/` 的直接子目录 |
| R12 | 已修复 | `8dc32d4` | manifest 声明 sha256 时逐项校验（路径归属、文件存在、摘要匹配） |
| R15 | 已修复 | `8dc32d4` | 暂存目录复制 + 完整性校验 + 原子发布；残缺 release 重建，暂存目录必清理 |
| R31 | 已修复 | `8dc32d4` | manifest 的 `ps_file`/`pl_file` 限定为组件内普通文件（绝对路径、`..`、外部文件均拒绝） |
| R07 | 已修复 | `5d08c05` | 登录框打开/关闭都清空用户名与密码，注销后必须重新输入 |
| R09 | 已修复 | `5d08c05` + `39924e4` | 命令区改为可滚动；内边距改由 `CommandPanel` 统一提供，最后一个按钮（故障复位）可滚入可视区 |
| R21 | 已修复 | `5d08c05` | 查询阶段与流式阶段共用 `_parse_identity`，`1.2e5`、`ERROR no device` 等不再被当成设备身份 |
| R24 | 已修复 | `5d08c05` | `CsvDataModel.resetModelData` 中用 `deleteLater()` 释放旧列对象 |
| R25 | 已修复 | `5d08c05` | 0 字节 CSV 走统一收尾流程，文件名/点数/提示同步更新为"该文件没有数据点" |
| R28 | 已修复 | `dd31521` | 状态文件路径按部署根推导（向上寻找同时含 `releases/` 与 `current` 的目录） |
| R32 | 已修复 | `dd31521` | `uv lock` 补齐 pyyaml 6.0.3，`uv lock --check` 通过 |

### 2. 本批（2026-10-08，纯软件可复现项 + 升级事务化）

| 编号 | 结论 | 关键改动 | 回归测试 |
| --- | --- | --- | --- |
| R08 | 已修复 | `Config_foupCommands.qml` 的 ComboBox 与 `selectedChannel` 共用唯一状态：`loadChannel()` 同时收敛通道范围并回写 `channelSelector.currentIndex`，`openWithChannel(0)` 重开后选择器不再保留上一次索引 | `tests/test_qml_channel_selection.py`（真实组件 + `QQmlExpression` 驱动） |
| R16 | 已修复 | `AsciiSerialClient` 记录读线程存活性：读异常时释放失效串口、`is_connected` 变 False、`connection_lost_callback` 通知上层；`connect()` 可重建串口与读线程 | `tests/test_ascii_serial_recovery.py` |
| R17 | 已修复 | `E84ControllerThread.stop()` 排队执行 `stop_controller` 后有界等待线程真正退出（默认 5s，超时才终止）；worker 清理幂等；`stopped_controller` 只发一次 | `tests/test_e84_thread_shutdown.py` |
| R22 | 已修复 | `ChartCard.qml` 提取 `currentValueColor`，按 `showOosUpper/showOosLower/showOoc*` 开关着色，与 `_check_channel_limits` 规则一致；新增配置 `chart.alarm_color_sync_with_limits`，置 false 时可"界面红色、但不设后台报警" | `tests/test_chart_card_limits.py`、`tests/test_chart_options.py` |
| R23 | 已修复 | Y 轴下界改由 `resolveYAxisMin()` 按数据量纲决定：含负值时显示负半轴，全正数据仍从 0 起；新增配置 `chart.y_axis_mode`（`auto`/`zero`） | `tests/test_chart_card_limits.py` |
| R33 | 已修复 | `QmlSocketClientBridge` 用绑定主线程 QObject 的队列信号 `_asyncFinished`/`_asyncFailed` 取代 `QTimer.singleShot`，异步操作结束后 `busy` 可靠清零 | `tests/test_socket_bridge_async.py` |
| R34 | 已修复 | `SpectrumDataModel.updateFromTimeDomain` 在峰值幅度低于数值噪声阈值（1e-12）时按"无信号"处理，输出归一化下界，不再把全零信号变成满量程 | `tests/test_spectrum_silence.py` |
| R13 | 已修复 | systemd 模板增加 `Environment=PYTHONPATH=<base>/current/src`，进程加载当前 release 的 `voc_app`；安装器用 MainPID 的 `/proc/<pid>/cwd` 校验运行进程属于目标 release | `tests/test_deploy_templates.py`、`tests/test_upgrade_transaction.py`，真实主机验证 |
| R14 | 已修复 | `LoadportInstaller.install` 事务化：停止 → 切换 current → 启动 → 确认；启动返回非零、超时或确认失败的异常统一回滚到旧版本并抛出说明 | `tests/test_upgrade_transaction.py`，真实主机验证 |
| R26 | 已修复 | `FoupInstaller` 抽出 `_ssh_auth_options()`，ssh 与 scp 共用 `-i <key> -o BatchMode=yes -o StrictHostKeyChecking=accept-new` | `tests/test_foup_installer.py`、`tests/test_upgrade_transaction.py` |
| R27 | 已修复 | `_stop_service()` 无论 stop 返回码如何都要求服务真的 inactive；`_confirm_running()` 额外校验 MainPID 已更换、current 指向目标 | `tests/test_upgrade_transaction.py`、`tests/test_loadport_installer.py`，真实主机验证 MainPID 变化 |
| R29 | 已修复 | 状态文件区分 `loadport_version`（实际运行版本）与 `loadport_target_version`（目标版本）；回滚后写入实际版本，`UpdateStatusController` 暴露 `targetVersion` | `tests/test_updater_orchestrator.py`，真实主机验证 |
| R30 | 已修复 | `UpdateOrchestrator.run` 把读包、读当前版本、安装全部纳入状态生命周期；任何前置失败都写 `failed`，不再残留 running 或沿用上一次 succeeded | `tests/test_updater_orchestrator.py` |

### 3. 上一轮修复过程中发现的两处"自伤"，已一并纠正

1. **R15 曾被上一轮改动加重**：把 manifest 写到已存在的 release 目录上，
   会让"上次复制中断的残缺目录"看起来像完整版本（报告 R15 证据即此现象）。
   现改为"复用前校验完整性，不完整就重新复制并原子发布"。
2. **R09 第一次修复无效**：把命令区放进 `ScrollView` 后最后一个按钮仍不可达，
   而当时的测试只做 `y - contentY` 的算术，没有验证渲染位移，因此"假通过"。
   现已改为用 `mapToItem` 断言窗口坐标，并修正了三个真实原因：
   命令页 `anchors.margins` 导致内容真实底边超出 `contentHeight`、
   Loader 高度绑定造成 binding loop、以及在 `ScrollView` 上设 `contentY`
   只是创建动态属性（真正可滚动的是其内部 flickable）。

## 二、未修复：仍需现场/策略确认（B 组）

| 编号 | 待定问题 | 需要谁决定 |
| --- | --- | --- |
| R01 | 握手条件撤销时，各阶段应保持哪些输入、撤销后回到哪个安全状态并撤回哪些输出 | 现场/E84 时序确认 |
| R02 | "检测到载具"与"完整落位"的判定口径（是否要求三键全落） | 现场接线与机械协议 |
| R03 | 执行机构本机通信异常是否一律锁存并拉低 READY（会改变现场行为） | 设备安全策略 |
| R04 | 控制器停止/应用退出时 GPIO 输出应置为何种状态 | 设备安全策略 |
| R18 | 协议帧/文件大小上限的具体阈值与超限处理 | 容量与业务约定 |
| R19 | 采集会话清理策略（绑定会话资源或禁止 500ms 内重启） | 交互约定 |
| R20 | 修改 IP 时切换设备连接的时机与并发约束 | 交互约定 |

原先列为"可继续排期"的 R08/R16/R17/R22/R23/R33/R34 与 R13/R14/R26/R27/R29/R30
已在本批修复；剩余 B 组的共同点是**需要现场设备口径或安全策略**，不是纯软件可判定项。

## 三、验收与回归

- 全量测试：`QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q --tb=short -rs`
  → **422 passed / 3 skipped**（`conftest.py` 固定 offscreen 与临时数据目录；
  `qapp` fixture 使用 `QApplication`，因为 QtCharts 的 `ChartView` 在只有
  `QGuiApplication` 时离屏实例化会段错误）。
  证据：[pytest-after-fixes.txt](evidence/2026-09-29/pytest-after-fixes.txt)。
- 新增回归用例覆盖本次修复的触发条件与外部可观察结果：真实 QML 组件里
  "重开后选择器与保存通道一致"、图表颜色与 Y 轴范围、串口失效后重建接收、
  E84 线程清理顺序、异步桥接 busy 归零、静音频谱、升级事务回滚与服务重启确认。
- **真实 Ubuntu 主机验证**（`jinao@192.168.1.241`，Ubuntu 24.04.4 / systemd 255，
  真实 `systemctl --user`）：
  - `current/src` 经 `PYTHONPATH` 生效，导入的 `voc_app` 来自当前 release；
  - 1.0.0 → 2.0.0 升级成功，MainPID 变化（564867 → 564885），进程 cwd 属于目标 release；
  - 构造"运行进程 cwd 不属于目标 release"的 3.0.0 升级：安装器识别并回滚到 2.0.0，
    状态文件记录 `loadport_version=2.0.0`、`loadport_target_version=3.0.0`、
    `update_state=failed`；
  - 证据：[host-upgrade-verification.txt](evidence/2026-09-29/host-upgrade-verification.txt)，
    脚本：[tools/host_upgrade_verification/](../../tools/host_upgrade_verification/README.md)。
- 仍未做：真实 FOUP/天车/GPIO/串口、真实 SSH/SCP 到 FOUP、断电与断网演练、
  PySide6 全版本矩阵与真实触摸屏 DPI 验证。相关结论仍以现场验证为准。
