# 代码与样式约定
- 语言/框架：Python 3 + PySide6/QML；QML 使用 QtQuick Controls 2 与自定义组件（`components/UiTheme.qml`、`ChartCard.qml` 等）。
- Python 风格：大量使用类型标注、`dataclass`、`Enum`；属性通过 `@Property`/`Signal`/`Slot` 暴露给 QML。TCP 协议使用 4 字节大端长度前缀；`SocketCommunicator` 默认带超时。
- QML 约定：组件统一从 `components` 导入，颜色/尺寸由 `UiTheme` 控制；页面由 `InformationPanel`+`CommandPanel` 组合，子页面依赖 `currentSubPage`（如 Config/Status 下的 loadport/foup）。
- 注释/文档：现有中文 docstring 与行注释，保持简洁说明意图；遵循项目已有命名与布局风格。
- 依赖选择：优先复用现有客户端/模型（`QmlSocketClientBridge`、`ChartDataListModel`、`CsvFileManager`），避免新增自研基础组件。