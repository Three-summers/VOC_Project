# VOC_Project 架构说明

- Date: 2025-12-03T10:08:17+08:00
- Executor: Codex

本文基于代码与现有文档（`docs/STRUCTURE.md`）整理 VOC_Project 的整体架构与信号 / 数据流转路径，方便后续维护与扩展。

---

## 1. 顶层结构概览

根目录（节选）：

- `docs/`
  - `STRUCTURE.md`：目录结构说明
  - `ARCHITECTURE.md`：架构与信号流说明（本文）
- `src/voc_app/`
  - `gui/`：PySide6 + QML 图形界面
  - `loadport/`：E84 协议与 GPIO 控制、串口工具
- `tests/`
  - `test_serial_device.py`：通用串口模块单元测试

从架构上可分为两大子系统：

1. **GUI 子系统 (`voc_app.gui`)**
   - PySide6 应用入口：`gui/app.py`
   - QML 视图与组件：`gui/qml/**`
   - TCP Socket 客户端：`gui/socket_client.py`
   - FOUP 采集控制器：`gui/foup_acquisition.py`
   - CSV 日志模型与数据图表：`gui/csv_model.py`
   - 报警存储：`gui/alarm_store.py`
   - 文件树与预览：`gui/file_tree_browser.py`
   - QML 与 socket 客户端桥接：`gui/qml_socket_client_bridge.py`

2. **Loadport 子系统 (`voc_app.loadport`)**
   - E84 控制 CLI 入口：`loadport/main.py`
   - E84 控制器线程封装：`loadport/e84_thread.py`
   - E84 状态机与 GPIO 控制：`loadport/e84_passive.py`
   - GPIO 抽象：`loadport/gpio_controller.py`
   - 通用串口模块：`loadport/serial_device.py`

---

## 2. GUI 子系统模块关系

### 2.1 应用入口与上下文注入（`gui/app.py`）

- 入口脚本：`src/voc_app/gui/app.py`
- 主要职责：
  - 创建 `QApplication` 和 `QQmlApplicationEngine`
  - 设置 QML 上下文属性（context properties）
  - 构建图表数据模型
  - 实例化 FOUP 采集控制器与报警、文件管理等对象
  - 加载 `qml/main.qml`

关键对象注入 QML 上下文的流程（简化）：

```text
QApplication
  └─ QQmlApplicationEngine
       ├─ setContextProperty("clientBridge", QmlSocketClientBridge)
       ├─ setContextProperty("csvFileManager", CsvFileManager)
       ├─ setContextProperty("authManager", AuthenticationManager)
       ├─ setContextProperty("fileController", FilePreviewController)
       ├─ setContextProperty("fileRootPath", Log 目录)
       ├─ setContextProperty("chartLegendHelper", ChartLegendHelper)
       ├─ setContextProperty("chartListModel", ChartDataListModel)
       ├─ setContextProperty("foupAcquisition", FoupAcquisitionController)
       └─ setContextProperty("alarmStore", AlarmStore)
```

> 证据：`app.py` 中 `engine.rootContext().setContextProperty(...)` 调用链。

### 2.2 图表数据模型与 CSV（`gui/csv_model.py`）

主要类：

- `SeriesTableModel`（`QAbstractTableModel` 子类）
  - 二维表结构：每行 `[x, y]`
  - 维护 `minX/maxX/minY/maxY/hasData` 等边界属性（`@Property`）
  - 提供 `append_point(x, y)` 追加数据并裁剪历史（`max_rows`）
  - 提供 `clear()`/`force_rebuild()` 供 QML 刷新

- `ChartDataListModel`（`QAbstractListModel` 子类）
  - role：`title`、`seriesModel`、`xColumn`、`yColumn`
  - 用于在 QML 中通过索引获取某个 “曲线条目”

- `CsvFileManager`
  - 扫描日志目录 `gui/Log` 下的 `.csv` 文件（`csvFiles` 属性）
  - `parse_csv_file(filename)` 解析 CSV：
    - 第一列视为时间列，统一规范为毫秒时间戳
    - 之后若干列转换为 `[{x, y}, ...]` 列表
  - 内部维护 `CsvDataModel`，供 `DataLogView.qml` 绑定

数据流（CSV→图表）：

```text
磁盘 CSV 文件
  └─ CsvFileManager.list_csv_files() 枚举路径
       └─ DataLogView.qml 通过 fileTree 选择文件
            └─ csvFileManager.parse_csv_file(relativePath)
                 └─ CsvFileManager._data_model.resetModelData(...)
                      └─ DataLogView.qml 读取 model.columnNames / model.get(i)
                           └─ 将列映射为可绘制数据点 (dataPoints)
                           └─ 通过 ChartCard.dataPoints 绘图（非实时模式）
```

### 2.3 图表组件（`gui/qml/components/ChartCard.qml`）

`ChartCard.qml` 是 QML 侧的通用图表组件：

- 使用 `QtCharts.ChartView + LineSeries + ScatterSeries`
- 支持两种数据来源：
  1. `seriesModel`（`SeriesTableModel`）+ `VXYModelMapper`（实时曲线）
  2. `dataPoints` 数组（静态 CSV 曲线）
- 动态调整轴范围：
  - `updateAxesFromSeries()` 按 `minX/maxX/minY/maxY` 以及 OOC/OOS/Target 综合决定 Y 轴范围
  - X 轴使用 `DateTimeAxis`，窗口宽度与 `maxRows` 成比例
- 绘制多条 “参考线”：
  - `oosSeries`/`oosLowerSeries`/`oocSeries`/`oocLowerSeries`/`targetSeries`
  - 由上层设置 `oocLimitValue`/`oosLimitValue`/`targetValue` 等属性控制

实时模式数据流（基于 `SeriesTableModel`）：

```text
SeriesTableModel.append_point(x, y)
  └─ 更新 _rows & 边界 (min/max)
      └─ 发出 boundsChanged 信号
           └─ ChartCard.Connections.onBoundsChanged()（在 QML 中）
                └─ 调用 updateAxesFromSeries()
                     └─ 更新 xAxis/yAxis 范围
                     └─ 调用 updateLimitLines()
  └─ VXYModelMapper 自动将 model 中的数据映射到 LineSeries/ScatterSeries
```

### 2.4 FOUP 采集控制器与实时曲线（`gui/foup_acquisition.py`）

关键类：

- `SocketCommunicator`（定义在 `gui/socket_client.py`）
  - TCP 客户端封装：
    - 在构造时连接 `(host, port)`，默认 2s 超时（`sock.settimeout(2.0)`）
    - `send(data)` / `recv(size)` 提供最小读写接口

- `ServerTypeRegistry`
  - 管理不同类型服务端的预设（PID / NOISE / UNKNOWN）
  - 提供 `detect_by_channel_count(channel_count)` 根据通道数推断类型
  - 提供 `get_preset(server_type)` 返回 `ServerTypePreset`

- `ChannelConfig` + `ChannelConfigManager`
  - 按 `{server_type}_{channel_idx}` 键管理通道配置，持久化到 `channel_config.json`
  - 提供 `get()/set()/update()` 等方法

- `FoupAcquisitionController(QObject)`
  - PySide6 Q 对象，负责：
    - 管理采集线程（内部使用 Python `threading.Thread`）
    - 管理 `SocketCommunicator` 连接与协议收发
    - 将采集到的多通道数据追加到对应 `SeriesTableModel`
    - 向 QML 提供属性与信号，如：
      - `running` / `statusMessage` / `lastValue` / `channelCount` / `serverTypeDisplayName`
      - `channelValuesChanged(int)` / `channelConfigChanged(int)` / `errorOccurred(str)` 等

Foup 采集线程内部协议（`_run_loop`）：

```text
FoupAcquisitionController.startAcquisition()
  └─ 清空所有 series model
  └─ 重置状态 (serverType/通道数等)
  └─ 启动后台线程 -> _run_loop()
       ├─ 创建 SocketCommunicator(host, port)
       ├─ _set_running(True), _set_status(\"采集中\")
       ├─ _send_command(\"voc_data_coll_ctrl_start\")
       └─ while not _stop_event.is_set():
             message = _recv_message()
             if message is None: break
             _handle_line(message)
```

消息格式：

- 服务端使用 **长度前缀协议**：
  - 先发送 4 字节大端整数（消息体长度）
  - 再发送 UTF-8 文本 payload
- `_recv_message()` 负责按长度读取并解码为字符串：
  - 若 `recv` 超时或出错则返回 `None`，结束循环

采集数据解析（`_handle_line`）：

```text
message: str (UTF-8 文本)
  ├─ 去除空白，空字符串直接丢弃
  ├─ 如果包含逗号：
  │     tokens = message.split(',')
  │     values = [float(token.strip()) for token in tokens 可解析部分]
  └─ 否则：
        values = [float(message)]  # 单通道兼容

首次收到数据：
  └─ channel_count = len(values)
  └─ _serverTypeDetected.emit(channel_count)  # 信号，主线程中处理
```

服务端类型与通道配置应用（`_on_server_type_detected`）：

```text
_serverTypeDetected(channel_count)
  └─ new_type = ServerTypeRegistry.detect_by_channel_count(channel_count)
  └─ 若 serverType 变化：
       ├─ _server_type = new_type
       ├─ _config_manager.set_server_type(new_type)
       ├─ _apply_preset_config(new_type)
       │    └─ 遍历 preset.channel_count:
       │         ├─ ChannelConfig.from_preset(...)
       │         ├─ _config_manager.set(channel_idx, config)
       │         └─ channelConfigChanged.emit(channel_idx)
       └─ serverTypeChanged.emit()
```

数据点推送至图表（跨线程信号）：

```text
_handle_line(...)
  ├─ 更新 _channel_values / _last_value，并发出：
  │    ├─ channelValuesChanged()
  │    └─ lastValueChanged()
  ├─ 生成 timestamp_ms（毫秒时间戳）
  └─ dataPointReceived.emit(timestamp_ms, values)  # 信号

dataPointReceived(x, values[])  # 主线程槽 _append_point_to_model
  └─ 遍历所有通道值：
       for channel_idx, y in enumerate(values):
           if channel_idx < len(_series_models):
               _series_models[channel_idx].append_point(x, y)
```

QML Foup 配置页绑定（`gui/qml/views/config/ConfigFoupPage.qml`）：

- 通过 `chartListModel.get(rowIndex)` 获取对应 `SeriesTableModel`
- `root.foupChartIndex = 2`，即：
  - index 0 / 1：Loadport 演示曲线（随机数据）
  - index ≥2：FOUP 实时曲线
- 使用单列 `ScrollView` + `ChartCard` 列表：

```text
chartListModel (Python)
  └─ ConfigFoupPage.chartEntry(rowIndex)
       └─ 返回 {title, seriesModel, xColumn, yColumn}
            └─ Repeater.delegate: ChartCard.seriesModel = seriesModel
                 ├─ yAxisUnit / 限界值等通过 foupAcquisition.getXxx(channelIdx)
                 └─ currentValue 通过 foupAcquisition.getChannelValue(channelIdx)
```

信号流（Foup 采集 → QML 图表）：

```text
[TCP Server]
  └─ socket 数据帧 (len + UTF-8 文本: "v1,v2,...")
      └─ SocketCommunicator.recv()
           └─ FoupAcquisition._recv_message()
                └─ FoupAcquisition._handle_line()
                     ├─ 更新 channelValues / lastValue
                     │    └─ Qt 信号: channelValuesChanged(), lastValueChanged()
                     │         └─ QML ConfigFoupPage.Connections.onChannelValuesChanged()
                     │              └─ 更新 ChartCard.currentValue
                     └─ Qt 信号: dataPointReceived(x, values[])
                          └─ _append_point_to_model()
                               └─ SeriesTableModel.append_point(x, y)
                                    └─ boundsChanged()
                                         └─ ChartCard.Connections.onBoundsChanged()
                                              └─ updateAxesFromSeries(), updateLimitLines()
```

### 2.5 QML 与 socket 客户端桥接（`gui/qml_socket_client_bridge.py`）

`QmlSocketClientBridge` 主要用于 QML 发起命令执行与文件下载，不直接参与图表绘制，但属于整体架构一部分。

主要职责：

- 管理 `Client` + `SocketCommunicator` 生命周期：
  - `connectSocket(host, port)` / `close()`
- 暴露同步槽：
  - `runShell(command: str) -> str`
  - `getFile(remote_path: str, dest_root: str) -> list`
- 暴露异步槽（推荐）：
  - `runShellAsync(command: str)`
    - 结果通过 `runShellFinished(str)` 信号返回
  - `getFileAsync(remote_path: str, dest_root: str)`
    - 结果通过 `getFileFinished(list)` 信号返回
- 状态属性：
  - `connected: bool`
  - `busy: bool`

信号流（QML 命令执行）示例：

```text
QML:
  clientBridge.connectSocket("127.0.0.1", 9000)
  clientBridge.runShellAsync("ls -la")
  onRunShellFinished: 显示或记录输出

内部：
  runShellAsync(cmd)
    └─ _run_async(_op, runShellFinished, cmd)
         └─ 后台线程:
              └─ Client.run_shell(cmd)  # 同样使用长度前缀协议
              └─ runShellFinished.emit(result)
```

### 2.6 报警与文件预览

#### AlarmStore（`gui/alarm_store.py`）

- 维护报警列表（时间戳 + 消息）
- 暴露模型给 QML（`AlarmsView.qml`）用于显示报警历史
- 常见流向：硬件/采集异常 → Python 调用 `addAlarm(...)` → QML 视图刷新

目前示例：`app.py` 中在启动时注入了若干示例报警，方便 UI 调试。

#### FilePreviewController（`gui/file_tree_browser.py`）

- 提供遍历、预览日志目录的能力
- 注入为 `fileController`，配合 `FileTreeBrowserView.qml` 使用

---

## 3. Loadport 子系统架构与信号流

### 3.1 CLI 入口与线程封装（`loadport/main.py`，`loadport/e84_thread.py`）

`src/voc_app/loadport/main.py`：

- 使用 `QCoreApplication` 启动 Qt 事件循环
- 创建 `E84ControllerThread` 并连接其信号到 `ConsoleBridge` 打印：
  - `started_controller` / `stopped_controller`
  - `error` / `e84_state_changed` / `e84_warning`
- 启动线程并在退出时调用 `worker.stop()`

`E84ControllerThread`（`loadport/e84_thread.py`）：

- 内部结构：

```text
E84ControllerThread(QObject)
  ├─ _thread: QThread
  ├─ _worker: _E84Worker(QObject)
  └─ _controller: E84Controller | None

_E84Worker(QObject)
  ├─ started(E84Controller)
  ├─ stopped()
  ├─ error(str)
  ├─ start_controller()
  └─ stop_controller()
```

运行流程：

```text
E84ControllerThread.start()
  └─ QThread.start()
       └─ _worker.start_controller()  # 在新线程中
            ├─ self.controller = E84Controller(...)
            ├─ self.controller.start()
            └─ started.emit(controller)

E84ControllerThread._on_worker_started(controller)
  ├─ 保存 controller 引用
  ├─ _connect_controller_signals(controller)
  │    ├─ controller.state_changed -> _relay_controller_state
  │    ├─ controller.warning       -> _relay_controller_warning
  │    └─ controller.fatal_error   -> _relay_controller_fatal
  ├─ controller_ready.emit(controller)
  └─ started_controller.emit()
```

信号中继：

```text
controller.state_changed(str)
  └─ _relay_controller_state(state)
       ├─ e84_state_changed.emit(state)
       └─ system_event.emit("e84_state", state)

controller.warning(str)
  └─ e84_warning.emit(message), system_event.emit("e84_warning", message)

controller.fatal_error(str)
  └─ e84_fatal_error.emit(message), system_event.emit("e84_fatal_error", message)
```

### 3.2 E84 状态机与 GPIO（`loadport/e84_passive.py`，`loadport/gpio_controller.py`）

`E84Controller(QObject)`：

- 使用 `QTimer` 驱动周期性处理：
  - `refresh_timer`：按 `refresh_interval` 调用 `_run_cycle()`
  - `timeout_timer`：用于多阶段超时控制（`ShortTimer`/`LongTimer`）
- `Refresh_Input()` 定期读取 E84 输入信号和 FOUP 位置按键信号：
  - 使用 `GPIOController.read_all_inputs()` 读取电平，并转换为布尔状态
  - 更新 `FOUP_status`，驱动 LED 状态与报警
- 状态机 `_process_state()`：
  - 枚举：`IDLE`/`WAIT_TR_REQ`/`WAIT_BUSY`/`WAIT_L_REQ`/`WAIT_U_REQ`/`WAIT_COMPT`/`WAIT_DONE`
  - 每个状态调用对应 `E84_wait_*()` 函数以检查输入、驱动输出并决定下一状态
  - 当状态改变时：

```text
if self.prev_state != self.state:
    print(f"当前状态:{self.state.value}")
    self.state_changed.emit(self.state.value)
    self.prev_state = self.state
```

GPIO 抽象（`GPIOController`）：

- 使用 `RPi.GPIO` 对输入/输出引脚进行统一封装：
  - 初始化输入引脚（上拉 / 下拉）
  - 初始化输出引脚并设置默认电平
  - 提供 `read_input(name)` / `read_all_inputs()` / `set_output(name, state)` / `set_all_outputs(state)`
  - 提供 `cleanup()` 释放 GPIO 资源（目前由调用方自行决定何时调用）

信号流（E84 状态变化）：

```text
硬件输入(GPIO)
  └─ GPIOController.read_all_inputs()
       └─ E84Controller.Refresh_Input()
            └─ 更新 E84_InSig_Value / E84_Key_Value / FOUP_status
                └─ _process_state()
                     ├─ 根据当前 state 与输入调用 E84_wait_*()
                     ├─ 根据需要设置输出 (READY/L_REQ/U_REQ 等)
                     └─ 若 state 发生变化：
                          └─ state_changed.emit(state.value)
                               └─ E84ControllerThread._relay_controller_state()
                                    └─ e84_state_changed.emit(state)
                                    └─ system_event.emit(\"e84_state\", state)
                                         └─ main.py 中 ConsoleBridge.on_state_changed() 打印日志
```

---

## 4. 串口子系统架构与流转

文件：`src/voc_app/loadport/serial_device.py`

主要类型：

- `SerialTransport(Protocol)`：定义与 `pyserial.Serial` 兼容的最小接口，方便注入 mock
- `GenericSerialCommand`：
  - `name`：命令名
  - `build_frame(...) -> bytes`：构造发送帧
  - `response_parser(raw, device)`：解析响应字节 → 业务对象
  - `response_handler(parsed, device)`：处理解析后的对象
- `GenericSerialDevice`：
  - 管理底层串口对象：
    - 通过 `serial_factory` 创建，默认使用 `serial.Serial`
    - `start()` 启动后台读取线程 `_reader_loop`
    - `stop()` 停止线程并关闭串口
  - 管理命令表 `command_table`：
    - `register_command(GenericSerialCommand)`
    - `send_command(name, **kwargs)` 调用 `build_frame`、`send_raw`
  - 数据读取：
    - `_reader_loop` 按 `in_waiting` 决定本次读取字节数
    - `_dispatch_chunk(chunk)`：
      - 遍历 `raw_listeners` 回调
      - 调用 `parser(chunk, self)` 把chunk交给上层解析

信号 / 回调流（串口命令示例，来自单测）：

单测文件：`tests/test_serial_device.py`

```text
InMemorySerial (测试用串口 stub)
  ├─ 属性 in_waiting = 队列长度
  ├─ read() 从队列取数据
  └─ write() 记录写入的数据

GenericSerialDeviceTests.setUp():
  ├─ 创建 stub_serial, serial_factory 返回该 stub
  ├─ 定义 parser(chunk, device):
  │     └─ device.handle_response(\"ping\", chunk)
  ├─ 定义 ping_command(GenericSerialCommand):
  │     ├─ build_frame(payload) = b\"\\x02\" + payload
  │     ├─ response_parser(raw) = raw.decode(\"ascii\")
  │     └─ response_handler(parsed) = responses.append(parsed)
  └─ 创建 GenericSerialDevice(...) 并 start()

test_send_command_and_handle_response():
  ├─ frame = device.send_command(\"ping\", payload=b\"OK\")
  ├─ stub_serial.written == [b\"\\x02OK\"]
  ├─ stub_serial.feed(b\"OK\")  # 模拟收到响应
  └─ parser(chunk=b\"OK\", device)
       └─ handle_response(\"ping\", b\"OK\")
             └─ response_parser -> \"OK\"
             └─ response_handler -> responses.append(\"OK\")
```

---

## 5. 典型信号 / 数据流总结

本节以场景为单位，概括主要的信号与数据路径。

### 5.1 GUI 启动与视图装载

```text
python3 -m voc_app.gui.app
  └─ QApplication / QQmlApplicationEngine 初始化
       ├─ 构建 ChartDataListModel + SeriesTableModel（Loadport 示例 + FOUP 通道）
       ├─ 创建 CsvFileManager / AlarmStore / FilePreviewController / FoupAcquisitionController 等
       ├─ setContextProperty(...) 注入 QML 上下文
       └─ engine.load(main.qml)
            └─ QML 组件树构建（NavigationPanel / StatusView / ConfigView 等）
```

### 5.2 FOUP 实时采集与图表更新

```text
用户在 QML 中点击“开始采集”
  └─ 调用 foupAcquisition.startAcquisition()
       ├─ 清空 series models
       ├─ 重置状态（通道数/服务端类型）
       └─ 启动后台线程 _run_loop()

_run_loop():
  ├─ 创建 SocketCommunicator(host, port)
  ├─ 状态改为“采集中”
  ├─ 发送 \"voc_data_coll_ctrl_start\"
  └─ 循环接收消息并调用 _handle_line(message)

_handle_line(message):
  ├─ 解析为 values[]（多通道 float）
  ├─ 首次根据 len(values) 触发 _serverTypeDetected(channel_count)
  │     └─ 检测出 PID/NOISE/UNKNOWN，应用预设限界配置
  ├─ 更新 _channel_values/_last_value 并发出 channelValuesChanged/lastValueChanged
  └─ 生成时间戳 timestamp_ms
        └─ dataPointReceived.emit(timestamp_ms, values)
             └─ _append_point_to_model(x, values)
                  └─ 对每个通道调用 SeriesTableModel.append_point(x, y)
                       └─ boundsChanged()
                            └─ ChartCard.QML 刷新轴与限界线
```

### 5.3 E84 状态变化与控制台输出

```text
python3 -m voc_app.loadport.main
  └─ QCoreApplication
       ├─ 创建 ConsoleBridge (打印回调)
       ├─ 创建 E84ControllerThread()
       ├─ 连接 started_controller / stopped_controller / error / e84_state_changed / e84_warning
       └─ worker.start()
            └─ QThread + _E84Worker 启动 E84Controller
                 └─ E84Controller.start()
                      └─ QTimer 周期性调用 _run_cycle()
                           └─ Refresh_Input() + _process_state()
                                └─ state_changed.emit(state.value)
                                     └─ E84ControllerThread._relay_controller_state()
                                          └─ e84_state_changed.emit(state)
                                               └─ ConsoleBridge.on_state_changed()
                                                    └─ print(\"[主线程] 状态更新: ...\")
```

### 5.4 QML 命令执行（Socket 客户端桥接）

```text
QML:
  Button.onClicked:
      if (clientBridge.connected)
          clientBridge.runShellAsync(\"uptime\")

QmlSocketClientBridge.runShellAsync(cmd):
  └─ _run_async(_op, runShellFinished, cmd)
       └─ 后台线程:
            ├─ _ensure_connected()
            ├─ out = Client.run_shell(cmd)  # 通过 SocketCommunicator
            └─ runShellFinished.emit(out 或 \"\")

QML:
  Connections {
      target: clientBridge
      function onRunShellFinished(out) {
          console.log(\"命令输出:\", out)
      }
  }
```

### 5.5 CSV DataLog 绘图

```text
用户在 DataLogView 中点击某个 CSV 文件:
  └─ FileTreeBrowserView 选中文件 -> DataLogView.handleSelection(path)
       └─ relative = relativePath(path)
       └─ csvFileManager.parse_csv_file(relative)
            ├─ 解析 header 与数据行
            ├─ 构建 ColumnData(name, dataPoints[])
            └─ CsvDataModel.resetModelData([...])

DataLogView:
  ├─ 通过 csvFileManager.dataModel 读取列名与 dataPoints
  ├─ 用户选择要绘制的列
  └─ 将选中列的 dataPoints 传给 ChartCard.dataPoints
       └─ ChartCard.onDataPointsChanged()
            ├─ 将 dataPoints 中的 (x,y) 填入 lineSeries/pointSeries
            ├─ 调整 xAxis/yAxis 范围
            └─ 绘制 OOC/OOS/Target 参考线
```

---

## 6. 后续维护建议

1. **文档维护**
   - 新增模块（例如更多服务器类型、额外图表视图）时，请同步更新本文件：
     - 模块列表（文件路径 + 职责）
     - 若引入新的 Qt 信号/槽，请在“典型信号 / 数据流总结”中新建子节说明

2. **信号与线程**
   - 当前 Foup 采集使用 Python 线程 + Qt 信号回主线程，E84 使用 QThread 包装；如后续引入更多后台任务，建议统一采用 Qt 的线程模型或明确区分两类线程规则。

3. **端口与 IP 配置**
   - 目前 Foup 采集默认 IP 为 `192.168.1.8`，端口为 `65432`，建议从配置文件 / 环境变量读取，并在文档中记录配置路径。

4. **GPIO 与平台兼容**
   - `RPi.GPIO` 在非树莓派环境不可用，如需在 PC 上开发/调试 loadport 逻辑，可考虑增加软模拟实现或条件导入，以便单测和文档示例更易执行。 

