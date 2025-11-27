## 项目上下文摘要（app.py 重构）
生成时间：2025-11-26

### 1. 相似实现分析
- **实现1**: src/voc_app/gui/qml_socket_client_bridge.py:17
  - 模式：简单工厂模式，单一职责初始化
  - 可复用：初始化后直接注册到 QML 上下文
  - 需注意：保持初始化和注册分离

- **实现2**: src/voc_app/gui/alarm_store.py:70-108
  - 模式：组合模式（AlarmStore 包含 AlarmModel）
  - 可复用：内部模型在构造函数中初始化
  - 需注意：信号和槽的连接时机

- **实现3**: src/voc_app/gui/csv_model.py:38-100
  - 模式：数据模型类，配置参数在构造函数传入
  - 可复用：使用工厂函数批量创建实例
  - 需注意：父对象关系管理

### 2. 项目约定
- **命名约定**:
  - 类名：大驼峰（AuthenticationManager, AlarmStore）
  - 函数名：蛇形命名（setup_socket_bridge, initialize_chart_models）
  - 私有方法：下划线前缀（_setup_internal）

- **文件组织**:
  - 每个功能模块独立文件
  - app.py 作为应用入口，负责协调和组装

- **导入顺序**:
  1. 标准库导入
  2. 第三方库导入（PySide6）
  3. 项目内导入

- **代码风格**:
  - 使用类型提示（str, Path, QObject）
  - 文档字符串使用简体中文
  - 单一职责原则

### 3. 可复用组件清单
- `voc_app.gui.socket_client`: Client, SocketCommunicator
- `voc_app.gui.qml_socket_client_bridge`: QmlSocketClientBridge
- `voc_app.gui.csv_model`: CsvFileManager, ChartDataListModel, ChartDataGenerator, SeriesTableModel
- `voc_app.gui.alarm_store`: AlarmStore
- `voc_app.gui.file_tree_browser`: FilePreviewController
- `voc_app.gui.foup_acquisition`: FoupAcquisitionController

### 4. 测试策略
- **测试框架**: 无明确测试框架（需补充）
- **测试模式**: 手动测试为主
- **参考文件**: 无专门测试文件
- **覆盖要求**: 基础功能测试（待完善）

### 5. 依赖和集成点
- **外部依赖**:
  - PySide6（Qt 绑定）
  - pathlib（路径处理）

- **内部依赖**:
  - voc_app.gui 模块下的各个组件
  - voc_app.loadport.e84_thread（当前注释掉）

- **集成方式**:
  - QML 上下文属性注册（setContextProperty）
  - 信号槽连接（QTimer.timeout, aboutToQuit）

- **配置来源**:
  - 硬编码路径（APP_DIR, PROJECT_ROOT）
  - 内联配置（测试数据）

### 6. 技术选型理由
- **为什么用 PySide6**:
  - Qt 官方 Python 绑定
  - 完整的 QML 集成支持
  - 跨平台兼容性

- **优势**:
  - 声明式 UI（QML）
  - 信号槽机制
  - 丰富的组件库

- **劣势和风险**:
  - 初始化代码过度集中
  - 缺乏清晰的职责划分
  - 测试数据硬编码在主函数中

### 7. 关键风险点
- **并发问题**:
  - QTimer 回调中的列表推导式（lambda）
  - LoadportBridge 线程管理（已注释）

- **边界条件**:
  - QML 文件加载失败
  - rootObjects 为空
  - 目录创建失败

- **性能瓶颈**:
  - 主函数过长（85行）
  - 初始化逻辑混杂

- **安全考虑**:
  - 硬编码用户凭证（admin/123456）
  - 无输入验证

### 8. 代码结构问题汇总
1. **主函数过长**：85行的 `if __name__ == "__main__"` 块
2. **冗余注释代码**：60多行的 LoadportBridge 类定义（46-108行）
3. **硬编码测试数据**：5个 alarm_store.addAlarm 调用（156-160行）
4. **职责不清**：初始化、配置、启动逻辑混杂
5. **注释过多**：大量解释性注释，代码自解释性不足
6. **缺乏抽象**：重复的初始化模式未提取为函数

### 9. 重构目标
1. **提高可读性**：主函数缩减至 20 行以内
2. **职责分离**：将初始化逻辑拆分为独立函数
3. **消除冗余**：删除注释掉的代码和测试数据
4. **增强可维护性**：提取通用初始化模式
5. **保持兼容性**：不改变任何运行时行为
