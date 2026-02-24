# Verification Report

- Date: 2025-11-25T10:50:06+08:00
- Executor: Codex
- Scope: GUI 调试（禁用 loadport 硬件依赖）
- Command: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen python3 -m voc_app.gui.app`
- Result: ⚠️ Blocked
- Details: 命令因缺少 `PySide6` 模块而失败，说明当前阻塞已切换为 GUI 依赖；此前最先触发的 `RPi.GPIO` 导入错误不再出现，证明注释 loadport 硬件代码已生效。
- Risk Assessment: 中偏低。只需在具备 PySide6 的环境重试即可验证 GUI；恢复 loadport 逻辑时重新取消注释即可。

## Verification - 2025-11-25T10:50:08+08:00
- Executor: Codex
- Scope: GenericSerialDevice regression
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures。确认在注释 loadport 代码后串口模块仍按预期工作。
- Risk Assessment: 低。串口层未受本次修改影响，可作为最小回归依据。

## Verification - 2025-11-19T10:02:05+08:00
- Executor: Codex
- Scope: Config 视图 loadport/foup 子页面与命令面板
- Command: `QT_QPA_PLATFORM=offscreen python3 -m voc_app.gui.app`
- Result: ⚠️ Blocked
- Details: 启动 GUI 时 Python 报错 `ModuleNotFoundError: No module named 'PySide6'`，当前环境缺少 PySide6 依赖，无法验证 QML。为避免引入非标准依赖，暂不在此环境安装；需在具备 PySide6 的目标环境重新执行以确认子页面 UI 与命令加载。
- Risk Assessment: 中。代码层面的 QML 语法已通过静态检查，预期安装依赖后可正常渲染；风险集中在运行环境缺少 PySide6。

## Verification - 2025-11-19T15:02:30+08:00
- Executor: Codex
- Scope: new_loadport 无串口依赖
- Command: `QT_QPA_PLATFORM=offscreen python3 -m voc_app.loadport.main`
- Result: ⚠️ Blocked
- Details: 缺少 `PySide6` 模块导致无法启动 QCoreApplication。由于串口模块已移除，运行时不会再访问 pyserial；待安装 PySide6 后可在设备上验证。
- Risk Assessment: 低。修改仅删除串口逻辑，不影响 GPIO 操作，风险来自环境依赖缺失。

## Verification - 2025-11-24T10:50:00+08:00
- Executor: Codex
- Scope: GenericSerialDevice regression
- Command: `python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test in 0.12s，確認串口命令/解析流程在最新分析後仍穩定。GUI/Loadport 驗證仍受 PySide6/RPi.GPIO 缺失阻塞，未重試。
- Risk Assessment: 低。串口模組已可在純 Python 環境持續驗證；整體交付仍依賴外部 GUI/硬體環境。

## Verification - 2025-11-25T11:25:19+08:00
- Executor: Codex
- Scope: 工业风 UI 改造后基础回归
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures。UI 仅修改 QML/样式层，串口单测仍然通过，说明后端逻辑未受影响。
- Risk Assessment: 中。GUI 冒烟测试仍因 PySide6 缺失而无法执行，需在具备依赖的目标站点重新运行以验证 QML。当前结果仅覆盖 Python 层。

## Verification - 2025-11-25T14:39:20+08:00
- Executor: Codex
- Scope: FOUP 采集控制器 + Config UI
- Command: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen python3 -m voc_app.gui.app` (未执行)
- Result: ⚠️ Blocked
- Details: 当前环境仍缺少 PySide6，无法启动 GUI 验证开始/停止按钮及折线图渲染；逻辑层面已通过单元测试和代码审查确认。待目标设备安装 PySide6 并提供本地 65432 采集服务后再运行，验证 chartListModel 是否收到实时数据。
- Risk Assessment: 中。若采集服务器回传格式与假设不同，需要调整 foup_acquisition.py 的解析逻辑；建议上线前在目标网络环境实机测试一次。

## Verification - 2025-11-26T15:06:25+08:00
- Executor: Codex
- Scope: FOUP 采集清空与滑动窗口改动回归
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures。确认新增 clear/轴重置逻辑未影响串口回归；ChartCard 空数据处理依赖 PySide6/QML 运行环境暂未实机验证。
- Risk Assessment: 中。GUI 冒烟仍受 PySide6 缺失阻塞；需在目标环境启动 Config/Status 页面观察二次采集时曲线是否按预期清空并保持固定窗口。

## Verification - 2025-11-27T16:00:17+08:00
- Executor: Codex
- Scope: Config 调色子页与命令面板
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures；确认 Python 层未受 QML 调色改动影响。GUI 调色/ColorDialog 交互需在具备 PySide6 的环境手动验证，当前机器仍未运行 GUI 冒烟。
- Risk Assessment: 中。ColorDialog 依赖 QtQuick.Dialogs，需在目标设备确认模块可用；若 PySide6/显示缺失则功能无法直观验证，上线前应在实际 GUI 环境检查调色刷新与重置行为。

## Verification - 2025-11-30T19:29:14+08:00
- Executor: Codex
- Scope: FOUP IP 可配置 + 命令面板输入框
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures；新增 host Property 和 QML TextField 未影响串口模块。GUI 冒烟仍因缺少 PySide6 无法执行，未验证 TextField 默认值与运行中禁用提示。
- Risk Assessment: 中。需在具备 PySide6/显示的目标设备手动检查：默认显示 192.168.1.8、运行中禁用编辑提示、修改 IP 后重新开始采集能否连接到新地址。若仍缺依赖则保持风险标注。 

## Verification - 2025-11-30T19:40:54+08:00
- Executor: Codex
- Scope: FOUP IP 配置对话框
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures；将命令面板 IP 输入改为对话框后，后端串口回归依旧通过。GUI 冒烟仍受 PySide6 缺失阻塞，未验证对话框弹出与确认流程。
- Risk Assessment: 中。待目标环境安装 PySide6/显示后手动确认：按钮可弹出对话框、默认值显示当前 IP、运行中禁用确定、修改后停止再启动可连接新 IP。继续保留环境依赖风险提示。

## Verification - 2025-12-01T11:30:52+08:00
- Executor: Codex
- Scope: 时间轴改造（ChartCard DateTimeAxis、CSV/Foup/生成器时间戳统一）
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures；后端时间戳改为毫秒、前端改用 DateTimeAxis 未影响现有串口单测。GUI 时间标签/滚动/放大/导出需在具备 PySide6 的环境手动确认。
- Risk Assessment: 中。若某处仍输出秒级或序号，DateTimeAxis 标签可能偏移；需在目标设备加载 CSV、实时采集和放大模式检查 X 轴时间显示与界限线范围。 

## Verification - 2025-12-01T11:54:22+08:00
- Executor: Codex
- Scope: 浅色主题切换（UiTheme palette/defaultPalette）
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures；仅颜色常量更新，Python 层无回归。GUI 需在 PySide6 环境确认浅色背景/按钮/文字对比度以及调色子页重置是否应用新默认值。
- Risk Assessment: 中。若某些视图存在硬编码深色叠层，可能与浅色不协调；需实机检查主界面、对话框、放大遮罩。 

## Verification - 2025-12-01T15:44:11+08:00
- Executor: Codex
- Scope: FOUP OOC/OOS 配置对话框 + 限界线绑定
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures；后端新增 OOC/OOS 属性，前端使用对话框设置并传递给 ChartCard。需在具备 PySide6 的环境手工验证：
  1) Config 命令面板“配置 OOC/OOS”按钮弹出对话框并可输入数值；
  2) 确认后 ChartCard 限界线随数值更新（所有 FOUP 通道）；
  3) 再次打开对话框回显当前值；
  4) 采集中修改若无需求可保留（目前未禁用）。
- Risk Assessment: 中。GUI 渲染需实机检查，若某处仍使用默认限界值或对话框定位偏移需调整。 

## Verification - 2025-12-01T16:03:11+08:00
- Executor: Codex
- Scope: FOUP OOC/OOS 前端共享配置（无后端信号）
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures；OOC/OOS 对话框改用前端共享状态 QtObject，Config Foup ChartCard 绑定该状态显示限界线，不依赖后端属性。需实机验证：
  1) 命令面板“配置 OOC/OOS”弹窗位置与 IP 弹窗一致；
  2) 修改后界限线立即反映在 Config Foup 图表；
  3) 再次打开弹窗回显最新值；
  4) 采集中/停止状态下行为是否符合预期（目前未禁用）。
- Risk Assessment: 中。GUI 渲染与行为需在 PySide6 环境观察，若与采集中状态交互有要求需再补逻辑。 

## Verification - 2025-12-01T16:09:22+08:00
- Executor: Codex
- Scope: 移除后端 OOC/OOS 属性（改用前端共享状态）
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures；后端不再暴露 OOC/OOS 属性，前端共享 QtObject 保持功能。需在 PySide6 环境确认：弹窗回显、修改后界限线更新、位置与 IP 弹窗一致。
- Risk Assessment: 中。GUI 行为仍需实机观察。 

## Verification - 2025-12-01T18:29:11+08:00
- Executor: Codex
- Scope: FOUP 通道级 OOC/OOS 上下界 + Target 配置、图表显示
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 1 test, 0 failures；前端通过共享 limitsMap 按通道配置 OOC/OOS 上下界与 Target，ChartCard 新增多条限界线并随通道配置更新。无后端信号依赖。
- Hand-check (需 PySide6 环境):
  1) 命令面板“配置 OOC/OOS/Target”弹窗含通道下拉 + 5 个输入，回显当前通道值；
  2) 确定后 Config FOUP 图表限界线与 Target 立即更新且仅作用于选定通道；
  3) 多通道切换时回显与显示对应通道值；
  4) 与 IP 弹窗位置一致。 
- Risk Assessment: 中。GUI 行为需实机确认；若通道数未知时下拉默认 1，需结合采集控制器 channelCount 实际检查。 

## Verification - 2025-12-05T09:51:10+08:00
- Executor: Codex
- Scope: Config FOUP 图表自适应网格（1全宽；2两列；3首卡跨两列半高；4 2x2 半高；>4 溢出半高滚动）
- Command: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen python3 -m voc_app.gui.app`（未执行）
- Result: ⚠️ Blocked
- Details: 当前环境缺少 PySide6，无法运行 GUI 验证。已进行代码审查：移除分页，GridLayout 两列，三张及以上时首卡跨两列但仅占一行半高，其余卡片半高并可滚动，ChartCard 数据绑定保持不变。需在具备 PySide6 的目标设备验证 1/2/3/4/5+ 通道布局与滚动性能。
- Risk Assessment: 中。布局逻辑依赖实际视口高度和通道数量，需实机确认高度比例与视觉效果是否符合需求。 

## Verification - 2025-12-02T16:11:49+08:00
- Executor: Codex
- Scope: 为 SocketCommunicator 设置 2s 超时，避免 socket recv 长时间阻塞线程
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 串口单测 1/1 通过，未覆盖 socket 行为。新超时仅影响 socket 模块；预期超时时抛出 `socket.timeout`，将被采集线程捕获并退出循环。
- Hand-check (需 PySide6 + 服务器环境):
  1) 启动 GUI，调用 `startAcquisition` 后在无数据/断流时应在 2s 左右触发 error/status 更新，线程退出；
  2) 正常数据流应持续更新曲线，无异常日志；
  3) 停止时 socket 能及时关闭，不遗留阻塞线程。 
- Risk Assessment: 中。未在真实 TCP 环境验证，需实机确认超时触发路径与用户提示是否满足预期。 

## Verification - 2025-12-02T16:17:57+08:00
- Executor: Codex
- Scope: Socket 超时/异常处理健壮性（recv 返回空包，捕获异常，stop 时容忍已关闭 socket）
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 单测 1/1 通过；_recv_exact 捕获 socket 异常返回 None，_send_command 捕获发送异常避免 Bad file descriptor。
- Hand-check (需 PySide6 + 服务器环境):
  1) 采集过程中点击“停止”时不应出现 Bad file descriptor 日志，线程退出且状态更新为“已停止/异常”；
  2) 服务器断开或停发数据时，约 2s 后采集线程退出并上报 error/status；
  3) 正常数据流不受影响。 
- Risk Assessment: 中。需实机验证日志与状态提示是否符合预期。 

## Verification - 2025-12-02T16:29:15+08:00
- Executor: Codex
- Scope: Config FOUP 视图改为单列滚动，每次仅显示一张图表
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed
- Details: 仅 QML 布局改动，Python 单测未覆盖 UI，1/1 通过。
- Hand-check (需 GUI):
  1) FOUP 配置页图表区域为单列 ScrollView，可上下滚动查看多通道；
  2) 单张 ChartCard 占满宽度，文本/限界线渲染正常；
  3) 状态行显示服务器类型与通道数，滚动时保持可见。 
- Risk Assessment: 低-中。需在小屏幕设备上确认滚动体验与性能。 

## Verification - 2025-12-03T16:09:00+08:00
- Executor: Codex
- Scope: Config FOUP 图表改为自适应网格（1全宽；2两列；3首卡跨两列+下一行两列；4 2x2；>4 同规则，垂直滚动）
- Command: `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed（仅串口单测，未覆盖 QML）
- Details: 布局改动在 `src/voc_app/gui/qml/views/config/ConfigFoupPage.qml`，ChartCard 数据绑定保持不变，GridLayout 2 列、奇数首卡跨两列，状态行占两列。
- Hand-check (需 GUI 环境，PySide6 与采集数据源):
  1) channelCount=1 时单卡全宽显示；2 时同一行两列；3 时第一行单卡跨两列，第二行两列展示剩余卡片；4 时 2x2；
  2) channelCount>4 时网格继续按两列填充，首卡跨两列（奇数），仅垂直滚动，无水平滚动；
  3) 每张卡片标题/单位/限界线与实时数据正常刷新，状态行显示服务端类型与通道数。
- Risk Assessment: 中。缺少 GUI 自动化测试，需人工验证各通道数场景下的布局与性能。 

## Verification - 2025-12-09T09:40:00+08:00
- Executor: Codex
- Scope: 采集模式切换（正常模式下载日志 / 测试模式实时采集）、版本查询解析、ACK 兼容、E84 三键自动触发桥接、Config UI 模式切换。
- Command: `python3 -m unittest tests/test_serial_device.py`
- Result: ✅ Passed（仅串口单测）
- Details: 后端增加 get_function_version_info 解析、类型化命令表、normal 模式通过 Client.get_file 下载 Log 目录，ACK 直接提示并忽略解析；E84 控制器新增 all_keys_set 信号，GUI 可通过 LoadportBridge 自动调用 startAcquisition（默认启用，可用 DISABLE_E84_BRIDGE 关闭）。Config 页新增模式切换、远端目录输入与类型/版本展示。未在无硬件/无服务器环境下执行实际连接、下载或 E84 信号验证。
- Hand-check (需服务器与硬件环境):
  1) 三键同时落下时 GUI 自动建立长连接并先发送 get_function_version_info；根据返回类型发送 sample_type_normal/test，再按模式开始采集或下载，状态文本更新。
  2) normal 模式下能够从远端目录（默认 Log，可配置）下载文件到本地 Log；下载过程中 running 状态可见，完成后状态提示文件数。
  3) 测试模式下 start/stop 发送类型化命令，ACK 返回不影响数据解析；断流或停止后 socket 正常关闭。
  4) Config 命令面板模式切换/目录输入与后端属性同步，服务器类型与版本在页面显示正确。
- Risk Assessment: 高（缺少真实服务器和 E84 硬件验证）。需在目标设备上实机验证自动建连、日志下载、ACK 行为与 UI 状态。 

## Verification - 2025-12-15T09:59:00+08:00
- Executor: Codex
- Scope: Noise_Spectrum 前缀下的 256 点频谱数据解析与路由（更新频谱页，不创建/追加 FOUP 图表）
- Command: `python -m unittest tests.test_foup_acquisition -v`
- Result: ✅ Passed
- Details: 新增路由逻辑：识别每包前缀为 `Noise_Spectrum`/`SPEC` 的频谱包，支持 `SPEC,<timestamp>,<256 bins...>`，并在输入为 uint32 大整数时按每帧最大值归一化到 0~1 后再调用 `SpectrumDataModel.updateSpectrum()` 整包替换；频谱前缀不覆盖 `serverType`（命令前缀），因此 FOUP 曲线可与频谱同时更新；首帧外部频谱到达后自动停止 `SpectrumSimulator`，避免模拟数据覆盖真实数据。
- Hand-check (需真实服务端与 GUI 环境):
  1) 实时数据流中同时包含 FOUP 数值包与 `Noise_Spectrum,<256点...>` 频谱包时：FOUP 曲线与频谱页同时更新；
  2) `Noise_Spectrum` 包不会影响 FOUP 的通道数/配置（不会误触发 256 通道 UI 或持久化配置）；
  3) 若 GUI 启动时模拟器默认在跑，首次收到真实频谱后模拟器自动停止，频谱图保持使用真实数据。
- Risk Assessment: 中。单测覆盖路由与模型调用，但未在受限沙箱环境中跑通真实 socket 推流与 QML 渲染，需要实机联调确认协议细节（分隔符/浮点格式/更新频率）。 

## Verification - 2026-01-16T10:45:00+08:00
- Executor: Codex
- Scope: GUI_Template 模板目录沉淀（QML 布局外壳 + 单点配置 + 占位页面/命令）与冒烟加载测试
- Command: `python -m pytest -q tests/test_gui_template_qml.py`
- Result: ✅ Passed
- Details:
  - 新增 `GUI_Template/qml/`：复用现有 `components/`，并提供 `TemplateConfig.qml` 单点配置（导航/子页/子命令开关）与四区布局 `main.qml`。
  - 补齐 `views/` 与 `commands/` 占位文件，保证模板在无 Python context properties 时也可加载创建根对象。
  - 新增 `GUI_Template/demo.py`：模板 Python 展示入口（加载 main.qml，并注入最小 `authManager` 用于登录按钮演示）。
  - 新增 `tests/test_gui_template_qml.py`：offscreen 下加载 `GUI_Template/qml/main.qml` 并断言可创建根对象。
  - 完整测试输出记录于 `.codex/testing.md`（包含全量 pytest 运行的已知失败项与环境限制说明）。
- Risk Assessment: 低。模板为新增目录，不影响现有 `src/voc_app/gui/qml`；跨项目复用仍需按目标项目注入所需 context properties（如需要登录/报警等能力）。

## Verification - 2026-01-16T16:32:00+08:00
- Executor: Codex
- Scope: 基于 GUI_Template 新建 `vibration_wafer_bt_gui/` 子项目，拷贝 vibration_wafer_bt BLE 接收端并在模板上实时绘制 AX 三轴曲线
- Command: `python -m pytest -q tests/test_vibration_wafer_bt_gui_simulation.py`
- Result: ✅ Passed
- Details:
  - 新增完整子项目目录 `vibration_wafer_bt_gui/`：包含 `qml/`（模板派生 UI）、`demo.py`（入口）、`src/vibration_wafer_bt_gui/`（控制器/模型）与 `bluetooth_receiver/`（拷贝的 BLE 接收端源码）。
  - `StatusView.qml` 使用 `ChartCard.qml` 绘制 AX X/Y/Z 三张实时曲线卡片；`StatusCommands.qml` 提供 `Start BLE / Start Simulation / Stop` 控制。
  - 新增 `tests/test_vibration_wafer_bt_gui_simulation.py`：不依赖 bleak/真实 BLE，验证 simulation 模式可驱动模型产生数据点。
  - `demo.py --offscreen --exit-after-load` 支持 headless 下的 QML 编译检查（不实例化 QtCharts ChartView，以规避当前环境下的 offscreen 崩溃）。
- Risk Assessment: 中。GUI 实际渲染与 BLE 实机连接需在具备显示与蓝牙适配器的目标环境验证；当前仅在本机完成 QML 编译检查与 simulation 单测。

## Verification - 2026-01-16T16:40:00+08:00
- Executor: Codex
- Scope: 修复 QtCharts/ChartCard 运行时报错（QApplication 依赖、chartLegendHelper 空引用、force_rebuild 缺失）并统一命令栏布局为 VOC 风格
- Command: `python -m pytest -q tests/test_gui_template_qml.py tests/test_vibration_wafer_bt_gui_simulation.py`
- Result: ✅ Passed
- Details:
  - `vibration_wafer_bt_gui/demo.py` 改为使用 `QApplication`，并在 Python 侧持有 `authManager/chartLegendHelper` 引用，避免 QML 侧变为 null。
  - `vibration_wafer_bt_gui/demo.py` 显式导入 `PySide6.QtCharts.QAbstractSeries`，确保 QML 的 `LineSeries/ScatterSeries` 传入 Python Slot 时被正确转换（避免退化成 `QObject` 导致缺少 `chart()`）。
  - `GUI_Template/qml/components/ChartCard.qml` 与 `vibration_wafer_bt_gui/qml/components/ChartCard.qml` 增加 chartLegendHelper 判空保护，避免未注入时直接报错。
  - `vibration_wafer_bt_gui/src/vibration_wafer_bt_gui/series_model.py` 补齐 `force_rebuild()` 以匹配 ChartCard 调用。
  - `GUI_Template/qml/commands/*.qml` 与 `vibration_wafer_bt_gui/qml/commands/*.qml` 从 `ColumnLayout` 调整为 `Column + anchors`（按钮全宽），与 VOC 项目命令栏排布一致。
- Risk Assessment: 低。冒烟测试通过；GUI 实机仍需在目标桌面环境确认图例隐藏效果与按钮布局观感。

## Verification - 2026-02-09T17:25:00+08:00
- Executor: Codex
- Scope: E84（Load/Unload 触发）与串口模块健壮性检查 + 确定性 bug 修复回归
- Command:
  - `PYTHONPATH=src python3 -m unittest tests/test_serial_device.py`
  - `PYTHONPATH=src python3 -c "from voc_app.loadport.ascii_serial import AsciiSerialClient; print('import_ok')"`
  - `python3 -m compileall -q src/voc_app/loadport/e84_passive.py src/voc_app/loadport/ascii_serial.py`
- Result: ✅ Passed
- Details:
  - 修复 `src/voc_app/loadport/e84_passive.py`：data_collection_stop 改为仅在 Load 完成且 FOUP 在位时触发（避免在 Unload 完成误触发）。
  - 修复 `src/voc_app/loadport/ascii_serial.py`：包内导入改为 `voc_app.loadport.serial_device`；`set_unconnect()` 改为发送已注册命令 `disconnect`，不再触发 KeyError。
  - 串口通用层单测 `tests/test_serial_device.py` 通过（1 test, 0 failures）。
- Risk Assessment: 低-中。串口层回归通过；E84 仍需在具备 RPi.GPIO 与真实接线/AMHS 的环境实机验证信号时序与引脚映射（LOAD/UNLOAD LED 与 L_REQ/U_REQ 等）。
