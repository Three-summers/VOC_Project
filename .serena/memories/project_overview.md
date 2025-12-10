# VOC_Project 项目概览
- 目标：提供 VOC/噪声等传感数据的桌面 GUI（PySide6+QML），并集成 Loadport E84 控制与 TCP/串口通讯；支持实时曲线、CSV 日志浏览、文件预览、报警。
- 主要模块：
  - `src/voc_app/gui/`：QML UI、PySide6 桥接与 socket 客户端；入口 `python3 -m voc_app.gui.app`。
  - `src/voc_app/loadport/`：E84 被动控制、GPIO 抽象、串口通用模块；CLI 入口 `python3 -m voc_app.loadport.main`。
  - `docs/ARCHITECTURE.md`、`docs/STRUCTURE.md`：结构与信号流说明。
- 数据流：GUI 通过 `FoupAcquisitionController` 连接 TCP（长度前缀协议），解析多通道数值并推送到 `SeriesTableModel`→QML 图表；`CsvFileManager` 扫描 `gui/Log` 下 CSV 并提供数据模型；`QmlSocketClientBridge` 封装 run/get 文件。
- 当前测试：仅 `tests/test_serial_device.py` 覆盖通用串口；GUI/E84 尚无自动化测试。