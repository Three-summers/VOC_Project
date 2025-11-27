## 项目上下文摘要（动态颜色选择功能）
生成时间：2025-11-27 16:50:00

### 1. 相似实现分析

**实现1**: src/voc_app/gui/qml/views/ConfigView.qml:76-156
- 模式：Component + Loader 动态子页面切换
- 可复用：loadportComponent 和 foupComponent 的结构模式
- 需注意：使用 Rectangle + ColumnLayout 容器，遵循 UiTheme 间距和圆角

**实现2**: src/voc_app/gui/qml/commands/Config_foupCommands.qml
- 模式：命令面板侧边栏布局
- 可复用：CustomButton + Column 垂直排列模式
- 需注意：需要绑定全局对象（如 foupAcquisition）

**实现3**: src/voc_app/gui/qml/views/DataLogView.qml:1-8
- 模式：使用 QtQuick.Dialogs 模块导入 ColorDialog
- 可复用：直接导入 QtQuick.Dialogs 即可使用 ColorDialog
- 需注意：需要 import QtQuick.Dialogs

### 2. 项目约定

**命名约定**:
- QML文件：PascalCase，如 ConfigView.qml, UiTheme.qml
- 组件ID：camelCase，如 configView, informationPanel
- 函数名：camelCase，如 displayValue(), updateScales()
- 属性名：camelCase，如 currentSubPage, scaleFactor

**文件组织**:
- views/：视图文件（ConfigView.qml等）
- components/：可复用组件（UiTheme.qml, CustomButton.qml等）
- commands/：命令面板文件（Config_themeCommands.qml等）
- 子页面使用 <主页面>_<子页面>Commands.qml 命名

**导入顺序**:
1. QtQuick 核心模块
2. QtQuick.Controls, QtQuick.Layouts 等扩展模块
3. QtQuick.Dialogs（如果需要）
4. 相对路径组件导入（"../components"）
5. 命名空间导入（import "../components" as Components）

**代码风格**:
- 缩进：4空格
- 属性顺序：id → property → readonly property → function → signal
- 组件绑定优先使用 Components.UiTheme.xxx() 函数
- 颜色使用 Components.UiTheme.color("role") 获取

### 3. 可复用组件清单

- `src/voc_app/gui/qml/components/UiTheme.qml`: 主题单例，提供 palette 属性和工具函数
- `src/voc_app/gui/qml/components/CustomButton.qml`: 标准按钮组件
- `src/voc_app/gui/qml/components/SubNavigationBar.qml`: 子导航栏组件
- `QtQuick.Dialogs.ColorDialog`: Qt 官方颜色选择对话框

### 4. 测试策略

**测试框架**: 手动UI验证（QML应用）
**测试模式**: 功能测试 + 视觉验证
**参考文件**: 无自动化测试（UI应用特性）
**覆盖要求**:
- 正常流程：点击颜色卡片 → 打开ColorDialog → 选择颜色 → 更新palette → 全局UI响应
- 边界条件：重置默认配色、快速切换颜色、取消选择
- 错误处理：palette为空、颜色角色不存在

### 5. 依赖和集成点

**外部依赖**:
- QtQuick 6.x（已有）
- QtQuick.Controls（已有）
- QtQuick.Dialogs（需确认是否已导入）

**内部依赖**:
- UiTheme.qml：单例，提供palette属性
- InformationPanel.qml：需要添加 theme 子导航项到 subNavigationConfig
- ConfigView.qml：需要添加 themeComponent 并在 Loader 中处理

**集成方式**:
- 属性绑定：所有使用 Components.UiTheme.color() 的组件自动响应 palette 变化
- 配置注入：通过 subNavigationConfig 添加导航项

**配置来源**:
- .claude/CLAUDE.md：开发规范
- docs/color.png：UI参考截图

### 6. 技术选型理由

**为什么用 UiTheme 单例 + 属性绑定**:
- 单例模式保证全局唯一主题实例
- QML属性绑定机制自动传播颜色变更
- 无需手动通知或刷新UI

**优势**:
- 实现简单，符合QML响应式编程范式
- 性能优秀，属性绑定由QML引擎优化
- 扩展性好，新增颜色角色只需修改palette对象

**劣势和风险**:
- 缺少createDefaultPalette()函数，需要实现
- palette对象是var类型，修改后需要重新赋值才能触发绑定更新
- ColorDialog在某些平台可能显示不一致

### 7. 关键风险点

**并发问题**: 无（QML单线程UI）

**边界条件**:
- UiTheme.palette 为 undefined 或 null
- 颜色角色名称拼写错误
- ColorDialog 取消选择时不应修改palette

**性能瓶颈**:
- 频繁修改palette可能触发大量属性重新计算
- 解决方案：使用JSON.parse/stringify克隆对象，一次性赋值

**安全考虑**:
- 无（按CLAUDE.md，安全需求优先级最低）

### 8. 已发现的缺失实现

**UiTheme.qml 缺失 createDefaultPalette() 函数**:
- 位置：src/voc_app/gui/qml/components/UiTheme.qml
- 问题：Config_themeCommands.qml 第13行调用了不存在的函数
- 解决：添加 createDefaultPalette() 函数，返回当前硬编码的默认palette
