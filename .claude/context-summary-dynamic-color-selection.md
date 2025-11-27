## 项目上下文摘要（动态颜色选择功能）
生成时间：2025-11-27 16:30:00

### 1. 现有实现分析

#### 实现1: UiTheme.qml - 核心主题单例
**路径**: `/home/say/code/python/VOC_Project/src/voc_app/gui/qml/components/UiTheme.qml`
**关键发现**:
- **模式**: Singleton 单例模式 (`pragma Singleton`)
- **调色板结构**: 使用 `property var palette` 存储颜色对象（第22-40行）
- **颜色访问**: 通过 `color(role, fallback)` 函数获取颜色（第146-150行）
- **可复用组件**:
  - `fontSize(role)` - 字体大小计算
  - `controlHeight(role)` - 控件高度计算
  - `spacing(level)` - 间距计算
  - `color(role, fallback)` - 颜色获取
- **需注意**:
  - `palette` 是 `property var` 类型，可以动态赋值
  - **缺失 `createDefaultPalette()` 函数** - Config_themeCommands.qml 引用了此函数但不存在
  - 当前硬编码的调色板有 18 个颜色角色

#### 实现2: Config_themeCommands.qml - 主题命令面板
**路径**: `/home/say/code/python/VOC_Project/src/voc_app/gui/qml/commands/Config_themeCommands.qml`
**关键发现**:
- **模式**: 命令面板模式（按钮触发操作）
- **功能**:
  - 重置默认配色（第38-42行）
  - 导出当前配色到日志（第44-51行）
- **可复用组件**:
  - `CustomButton` - 自定义按钮组件
  - `clonePalette(source)` - 深拷贝调色板函数
- **需注意**:
  - **错误**: 第13行引用了不存在的 `Components.UiTheme.createDefaultPalette()`
  - 使用 JSON 序列化来克隆调色板

#### 实现3: ConfigView.qml - 配置视图主页面
**路径**: `/home/say/code/python/VOC_Project/src/voc_app/gui/qml/views/ConfigView.qml`
**关键发现**:
- **模式**: 多子页面切换模式（通过 `currentSubPage` 属性）
- **子页面**: loadport、foup（根据 operations-log 应该还有 theme 子页面）
- **可复用组件**:
  - `Loader` - 动态加载子页面组件
  - `TitleItemCard` - 标题卡片组件（未在当前代码中看到，但存在文件）
- **需注意**:
  - 使用 `Loader.sourceComponent` 切换子页面
  - 所有子页面使用 `Rectangle` + `ColumnLayout` 的统一布局模式

### 2. 项目约定

#### 命名约定
- **QML 文件**: 大驼峰命名（`UiTheme.qml`, `ConfigView.qml`）
- **属性**: 小驼峰命名（`currentSubPage`, `scaleFactor`）
- **颜色角色**: 小驼峰命名（`background`, `textPrimary`, `accentInfo`）
- **函数**: 小驼峰命名（`fontSize`, `color`, `clonePalette`）
- **命令文件**: `{View}Commands.qml` 或 `{View}_{subpage}Commands.qml`

#### 文件组织
```
src/voc_app/gui/qml/
├── components/         # 可复用组件（UiTheme, CustomButton, etc.）
├── views/             # 主视图页面（ConfigView, StatusView, etc.）
├── commands/          # 命令面板（ConfigCommands, Config_themeCommands, etc.）
├── main.qml           # 应用入口
└── {Panel}.qml        # 顶层面板（NavigationPanel, CommandPanel, etc.）
```

#### 导入顺序
1. QtQuick 核心模块
2. QtQuick 子模块（Controls, Layouts, Dialogs）
3. 相对路径组件导入（`"../components"`）
4. 别名导入（`"../components" as Components`）

#### 代码风格
- **缩进**: 4 空格
- **属性声明**: readonly property > property > function
- **颜色引用**: 统一使用 `Components.UiTheme.color("role")`
- **间距引用**: 统一使用 `Components.UiTheme.spacing("level")`
- **注释**: 简体中文

### 3. 可复用组件清单

- `src/voc_app/gui/qml/components/UiTheme.qml`: 主题单例
  - `color(role, fallback)` - 获取颜色
  - `fontSize(role)` - 获取字体大小
  - `spacing(level)` - 获取间距
  - `controlHeight(role)` - 获取控件高度
  - `palette` - 调色板对象

- `src/voc_app/gui/qml/components/CustomButton.qml`: 自定义按钮
- `src/voc_app/gui/qml/components/BaseDialog.qml`: 基础对话框
- `src/voc_app/gui/qml/components/TitleItemCard.qml`: 标题卡片

### 4. 测试策略

#### 测试框架
- **后端**: Python unittest（`tests/test_serial_device.py`）
- **前端**: 手动验证（需要 PySide6 + 显示环境）

#### 测试模式
- **单元测试**: Python 模块测试
- **集成测试**: GUI 实机验证
- **验证文件**: `.codex/testing.md`, `verification.md`

#### 参考文件
- `tests/test_serial_device.py` - Python 单测示例
- `verification.md` - 验证报告模板

#### 覆盖要求
- Python 层：运行 unittest 确保未破坏后端
- QML 层：实机验证颜色刷新、重置、导出功能

### 5. 依赖和集成点

#### 外部依赖
- **Qt/QML**: QtQuick 6+, QtQuick.Controls, QtQuick.Layouts, QtQuick.Dialogs
- **Python**: PySide6（GUI 运行时）

#### 内部依赖
- **主题系统**: `UiTheme.qml` (Singleton)
- **导航系统**: `ConfigView.qml` 通过 `currentSubPage` 切换子页面
- **命令系统**: `CommandPanel.qml` 动态加载对应的 `{View}_{subpage}Commands.qml`

#### 集成方式
- **主题绑定**: 所有组件通过 `Components.UiTheme.color()` 访问颜色
- **状态同步**: 修改 `UiTheme.palette` 后所有绑定自动更新
- **命令通信**: 命令面板通过直接修改 `Components.UiTheme.palette` 触发刷新

#### 配置来源
- **当前**: 硬编码在 `UiTheme.qml` 的 `palette` 属性
- **未来可能**: JSON 配置文件、用户偏好存储

### 6. 技术选型理由

#### 为什么用 Singleton 模式？
- **优势**: 全局唯一实例，所有组件共享同一套主题配置
- **劣势**: 测试时难以隔离，但对于 UI 主题是合理的权衡

#### 为什么用 property var palette 而非具体类型？
- **优势**: 灵活，可以动态赋值新对象，支持任意颜色角色
- **劣势**: 缺少类型检查，运行时错误风险较高

#### 为什么需要 createDefaultPalette()？
- **问题**: 当前缺失此函数导致 Config_themeCommands.qml 运行时错误
- **需求**: 需要能够克隆初始调色板以支持重置功能
- **方案**: 应该返回硬编码调色板的深拷贝

### 7. 关键风险点

#### 并发问题
- **低风险**: QML 单线程模型，palette 修改会触发属性绑定更新

#### 边界条件
- **颜色格式校验**: 用户输入的颜色字符串可能不合法（如 `#gggggg`）
- **缺失颜色角色**: 调用 `color("unknownRole")` 会返回 fallback 或 `#ffffff`
- **palette 为 null**: 如果 palette 被设为 null，所有 color() 调用会失败

#### 性能瓶颈
- **低风险**: 颜色访问是轻量操作，palette 对象小（18 个属性）
- **潜在问题**: 频繁修改 palette 会触发大量重绘，应批量更新

#### 安全考虑
- **无**: 按照 CLAUDE.md 规范，安全性优先级最低

### 8. 现有实现截图分析

根据 `docs/color.png` 截图：
- **已实现**: 调色板调整界面（"调色板调整"标题）
- **功能**:
  - "重置默认配色" 按钮
  - "刷新当前值" 按钮
  - 左侧颜色卡片（background, panel, surface...）
  - 右侧颜色卡片（surface, outline...）
  - 每个颜色角色有：标签、颜色预览块、"选色" 按钮
- **布局**: Flow 布局，卡片式设计
- **观察**:
  - 颜色预览块直观展示当前颜色
  - "选色" 按钮应该触发 ColorDialog
  - 左右分栏展示所有颜色角色

### 9. 待解决的问题

#### 高优先级
1. **UiTheme.qml 缺失 createDefaultPalette() 函数** - 导致 Config_themeCommands.qml 运行时错误
2. **ConfigView.qml 缺少 theme 子页面定义** - 截图显示的界面在哪里定义的？
3. **CommandPanel.qml 如何加载 Config_themeCommands.qml** - 需要了解命令面板的加载逻辑

#### 中优先级
4. **颜色选择器如何工作** - 是否使用 QtQuick.Dialogs.ColorDialog？
5. **palette 修改后如何持久化** - 是否保存到配置文件？
6. **颜色输入验证** - 如何防止非法颜色值？

#### 低优先级
7. **是否支持颜色预设/模板** - 如深色主题、浅色主题、高对比度主题
8. **是否支持导入/导出配色方案** - JSON 文件交换配色

### 10. 需要搜索的关键文件

- [ ] `ConfigView.qml` 的完整版本（可能被截断或有 theme 子页面）
- [ ] `CommandPanel.qml` - 了解如何动态加载命令文件
- [ ] `InformationPanel.qml` - 了解 currentSubPage 如何传递
- [ ] 任何包含 ColorDialog 或颜色选择器的文件
- [ ] 任何包含 theme 子页面定义的文件
