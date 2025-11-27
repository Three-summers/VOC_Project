# 动态颜色选择功能 - 详细实施计划

**生成时间**: 2025-11-27 16:52:00
**任务类型**: 功能完整实现
**预计总时长**: 60-70分钟
**优先级**: P0（核心功能）

---

## 一、任务概述

### 1.1 目标
在VOC项目的ConfigView中实现动态颜色选择功能，允许用户通过UI界面实时修改应用的18个颜色角色，并立即全局生效。

### 1.2 背景
- **用户需求**: 用户希望在config中添加可以动态选择各个组件颜色的功能
- **技术架构**: 基于UiTheme单例 + QML属性绑定机制
- **参考设计**: docs/color.png 截图显示完整UI布局
- **当前状态**: Config_themeCommands.qml已创建但存在阻塞性缺陷

### 1.3 核心问题
1. **UiTheme.qml缺失createDefaultPalette()函数**（阻塞性）
2. **ConfigView.qml未定义themeComponent**（核心功能缺失）
3. **InformationPanel.qml未配置theme导航项**（入口缺失）

### 1.4 技术方案
- **颜色选择器**: QtQuick.Dialogs.ColorDialog
- **布局方式**: Flow + Rectangle（颜色卡片）
- **状态管理**: UiTheme.palette属性（var类型）
- **更新机制**: 克隆对象 + 重新赋值触发绑定

---

## 二、详细任务列表

### 任务1：修复UiTheme.qml - 添加createDefaultPalette()函数

#### 2.1.1 任务元信息
- **任务ID**: TASK-001
- **优先级**: P0（阻塞性）
- **预计时间**: 5分钟
- **依赖**: 无
- **阻塞**: TASK-004（验证依赖此函数）

#### 2.1.2 输入
- 文件: `src/voc_app/gui/qml/components/UiTheme.qml`
- 行号: 第22-40行（现有palette定义）
- 数据: 18个颜色角色及其默认值

#### 2.1.3 输出
- 新增函数: `function createDefaultPalette()`
- 返回值: JavaScript对象（18个键值对）
- 位置: 第41行（紧接palette定义之后）

#### 2.1.4 接口规格
```qml
// 函数签名
function createDefaultPalette()

// 返回值类型
{
    background: string,      // "#050505"
    surface: string,         // "#121212"
    panel: string,           // "#1e1e1e"
    panelAlt: string,        // "#2d2d2d"
    outline: string,         // "#666666"
    outlineStrong: string,   // "#999999"
    buttonBase: string,      // "#333333"
    buttonHover: string,     // "#444444"
    buttonDown: string,      // "#555555"
    textPrimary: string,     // "#ffffff"
    textSecondary: string,   // "#e0e0e0"
    textOnLight: string,     // "#000000"
    textOnLightMuted: string,// "#333333"
    accentInfo: string,      // "#2979ff"
    accentSuccess: string,   // "#00e676"
    accentWarning: string,   // "#ffab00"
    accentAlarm: string      // "#ff1744"
}

// 调用方式
const defaultPalette = Components.UiTheme.createDefaultPalette()
```

#### 2.1.5 实现要点
1. **深拷贝机制**: 返回新对象，避免引用共享
2. **完整性**: 必须包含所有18个颜色角色
3. **格式规范**: 使用 "#RRGGBB" 六位十六进制格式
4. **不可变性**: 每次调用返回新对象副本

#### 2.1.6 验收标准
- [ ] 函数定义在UiTheme.qml中（第41行附近）
- [ ] 返回对象包含18个颜色角色
- [ ] 所有颜色值为有效的十六进制字符串
- [ ] Config_themeCommands.qml第13行调用不报错
- [ ] 命令面板"重置默认配色"按钮功能正常

#### 2.1.7 测试用例
```qml
// 测试1: 函数存在性
console.assert(typeof UiTheme.createDefaultPalette === "function")

// 测试2: 返回值完整性
const p = UiTheme.createDefaultPalette()
console.assert(Object.keys(p).length === 18)

// 测试3: 深拷贝验证
const p1 = UiTheme.createDefaultPalette()
const p2 = UiTheme.createDefaultPalette()
p1.background = "#000000"
console.assert(p2.background === "#050505")

// 测试4: 颜色格式验证
console.assert(/^#[0-9a-fA-F]{6}$/.test(p.background))
```

#### 2.1.8 风险评估
- **风险等级**: 低
- **潜在问题**: 无
- **回滚方案**: 删除函数定义（影响范围：仅重置功能不可用）

---

### 任务2：实现ConfigView.qml的theme子页面

#### 2.2.1 任务元信息
- **任务ID**: TASK-002
- **优先级**: P0（核心功能）
- **预计时间**: 40分钟
- **依赖**: 无
- **阻塞**: TASK-004（验证依赖此页面）

#### 2.2.2 输入
- 文件: `src/voc_app/gui/qml/views/ConfigView.qml`
- 参考: docs/color.png（UI设计截图）
- 数据: UiTheme.palette的18个颜色角色
- 组件: QtQuick.Dialogs.ColorDialog

#### 2.2.3 输出
- 新增Component: `themeComponent`
- 位置: 第281行（foupComponent之后）
- 行数: 约120行（包含18个颜色卡片 + 辅助函数）

#### 2.2.4 接口规格

**Component结构**:
```qml
Component {
    id: themeComponent

    Item {
        anchors.fill: parent

        // 主容器
        Rectangle {
            // 样式: 与loadportComponent/foupComponent一致
            color: Components.UiTheme.color("panel")
            border.color: Components.UiTheme.color("outline")
            radius: Components.UiTheme.radius(18)

            ColumnLayout {
                // 标题
                Text { text: "调色板调整" }

                // 说明文本
                Text { text: "修改 UiTheme.palette 后..." }

                // 顶部按钮组
                RowLayout {
                    CustomButton { text: "重置默认配色" }
                    CustomButton { text: "刷新当前值" }
                }

                // 颜色卡片容器
                ScrollView {
                    Flow {
                        // 18个ColorRoleCard
                        Repeater {
                            model: [18个颜色角色定义]
                            delegate: ColorRoleCard {...}
                        }
                    }
                }
            }
        }
    }
}
```

**ColorRoleCard子组件**:
```qml
Rectangle {
    width: 计算值（响应式）
    height: 固定值（根据截图）

    Column {
        // 标签（中文 + 英文key）
        Text { text: roleLabel + " (" + roleKey + ")" }

        // 颜色预览矩形
        Rectangle {
            color: Components.UiTheme.color(roleKey)
            // 尺寸、边框根据截图调整
        }

        // 选色按钮
        CustomButton {
            text: "选色"
            onClicked: colorDialog.open()
        }
    }

    // ColorDialog（每个卡片一个实例）
    ColorDialog {
        id: colorDialog
        selectedColor: Components.UiTheme.color(roleKey)
        onAccepted: {
            updatePaletteColor(roleKey, selectedColor)
        }
    }
}
```

**辅助函数**:
```qml
// 颜色更新函数
function updatePaletteColor(roleKey, colorValue) {
    // 1. 克隆当前palette
    const next = JSON.parse(JSON.stringify(Components.UiTheme.palette))

    // 2. 修改指定角色
    next[roleKey] = colorValue

    // 3. 重新赋值触发绑定
    Components.UiTheme.palette = next
}

// 批量重置函数
function resetPalette() {
    const defaultPalette = Components.UiTheme.createDefaultPalette()
    Components.UiTheme.palette = defaultPalette
}

// 刷新显示函数
function refreshDisplay() {
    // 强制Repeater重新绑定
    colorRoleModel = colorRoleModel.slice()
}
```

**颜色角色模型**:
```qml
readonly property var colorRoleModel: [
    { key: "background", label: "背景" },
    { key: "surface", label: "表面" },
    { key: "panel", label: "面板" },
    { key: "panelAlt", label: "面板替代" },
    { key: "outline", label: "边框" },
    { key: "outlineStrong", label: "边框(强)" },
    { key: "buttonBase", label: "按钮基础" },
    { key: "buttonHover", label: "按钮悬停" },
    { key: "buttonDown", label: "按钮按下" },
    { key: "textPrimary", label: "文本主色" },
    { key: "textSecondary", label: "文本次色" },
    { key: "textOnLight", label: "亮底文本" },
    { key: "textOnLightMuted", label: "亮底柔和文本" },
    { key: "accentInfo", label: "强调(信息)" },
    { key: "accentSuccess", label: "强调(成功)" },
    { key: "accentWarning", label: "强调(警告)" },
    { key: "accentAlarm", label: "强调(报警)" }
]
```

#### 2.2.5 布局规格（基于截图）

**容器层级**:
```
Rectangle (主容器)
└── ColumnLayout
    ├── Text (标题：调色板调整)
    ├── Text (说明文本)
    ├── RowLayout (按钮组)
    │   ├── CustomButton (重置默认配色)
    │   └── CustomButton (刷新当前值)
    └── ScrollView
        └── Flow (颜色卡片网格)
            └── Repeater (18个卡片)
```

**尺寸规格**:
- 主容器: 填充父容器（anchors.fill: parent）
- 颜色卡片: 宽度约160-180px，高度约120px（响应式调整）
- Flow间距: Components.UiTheme.spacing("md")
- 颜色预览矩形: 宽度填充卡片，高度约40px
- 按钮高度: Components.UiTheme.controlHeight("buttonThin")

#### 2.2.6 验收标准
- [ ] themeComponent定义在ConfigView.qml中
- [ ] Loader能正确加载themeComponent（通过currentSubPage="theme"）
- [ ] 显示18个颜色卡片，布局与截图一致
- [ ] 每个卡片显示：标签（中英文）、颜色预览、选色按钮
- [ ] 点击"选色"按钮打开ColorDialog
- [ ] ColorDialog初始颜色为当前角色颜色
- [ ] 选择颜色后点击"确定"，立即更新palette
- [ ] 全局UI（如侧边栏、标题栏、按钮）立即响应颜色变化
- [ ] 点击"重置默认配色"按钮，恢复初始配色
- [ ] 点击"刷新当前值"按钮，颜色预览同步最新值

#### 2.2.7 测试用例
```qml
// 测试1: 组件加载
configView.currentSubPage = "theme"
Qt.callLater(() => {
    console.assert(contentLoader.item !== null)
    console.assert(contentLoader.item.toString().includes("themeComponent"))
})

// 测试2: 颜色卡片数量
console.assert(repeater.count === 18)

// 测试3: 颜色更新传播
const originalBackground = UiTheme.color("background")
updatePaletteColor("background", "#FF0000")
Qt.callLater(() => {
    console.assert(UiTheme.color("background") === "#ff0000")
    // 恢复
    updatePaletteColor("background", originalBackground)
})

// 测试4: 重置功能
updatePaletteColor("background", "#FF0000")
resetPalette()
console.assert(UiTheme.color("background") === "#050505")
```

#### 2.2.8 风险评估
- **风险等级**: 中
- **潜在问题**:
  1. ColorDialog在WSL环境可能无法显示
  2. palette修改可能触发大量重绘导致性能问题
  3. Flow布局在不同窗口尺寸下可能错位
- **缓解措施**:
  1. 测试ColorDialog可用性，失败则降级为TextField输入
  2. 使用JSON.parse/stringify克隆对象，减少中间状态更新
  3. 使用ScrollView包裹Flow，确保内容可滚动
- **回滚方案**: 删除themeComponent定义，移除Loader选择逻辑

---

### 任务3：在InformationPanel.qml添加theme导航项

#### 2.3.1 任务元信息
- **任务ID**: TASK-003
- **优先级**: P0（入口必需）
- **预计时间**: 3分钟
- **依赖**: TASK-002（theme子页面必须存在）
- **阻塞**: TASK-004（验证依赖导航功能）

#### 2.3.2 输入
- 文件: `src/voc_app/gui/qml/InformationPanel.qml`
- 行号: 第16-25行（subNavigationConfig定义）
- 现有结构: Config数组包含 loadport 和 foup

#### 2.3.3 输出
- 修改: subNavigationConfig["Config"] 数组
- 新增项: `{ key: "theme", title: "调色" }`
- 位置: 数组第三项（foup之后）

#### 2.3.4 接口规格
```qml
property var subNavigationConfig: ({
    "Status": [
        { key: "loadport", title: "Loadport" },
        { key: "foup", title: "FOUP" }
    ],
    "Config": [
        { key: "loadport", title: "Loadport" },
        { key: "foup", title: "FOUP" },
        { key: "theme", title: "调色" }  // 新增
    ]
})
```

#### 2.3.5 实现要点
1. **顺序**: 放在foup之后（符合直觉：基础配置 → 调色）
2. **key值**: "theme"（必须与ConfigView.qml的Loader逻辑匹配）
3. **title**: "调色"（简体中文，符合CLAUDE.md规范）
4. **格式**: 保持与现有项一致的对象结构

#### 2.3.6 验收标准
- [ ] subNavigationConfig["Config"]包含3个项
- [ ] 第3项为 `{ key: "theme", title: "调色" }`
- [ ] Config主页面子导航栏显示3个标签：Loadport、FOUP、调色
- [ ] 点击"调色"标签切换到theme子页面
- [ ] SubNavigationBar高亮显示当前选中的标签

#### 2.3.7 测试用例
```qml
// 测试1: 配置完整性
const configItems = subNavigationConfig["Config"]
console.assert(configItems.length === 3)
console.assert(configItems[2].key === "theme")
console.assert(configItems[2].title === "调色")

// 测试2: 导航功能
informationPanel.currentView = "Config"
Qt.callLater(() => {
    console.assert(subNavBar.items.length === 3)
    subNavBar.setCurrentKey("theme", true)
    Qt.callLater(() => {
        console.assert(viewLoader.item.currentSubPage === "theme")
    })
})
```

#### 2.3.8 风险评估
- **风险等级**: 极低
- **潜在问题**: 无
- **回滚方案**: 删除新增的数组项

---

### 任务4：验证功能完整性

#### 2.4.1 任务元信息
- **任务ID**: TASK-004
- **优先级**: P1（质量保证）
- **预计时间**: 15分钟
- **依赖**: TASK-001, TASK-002, TASK-003
- **阻塞**: 无

#### 2.4.2 验证清单

**基础功能验证**:
- [ ] 应用启动无报错
- [ ] 点击"配置"主导航进入ConfigView
- [ ] 子导航栏显示3个标签（Loadport、FOUP、调色）
- [ ] 点击"调色"标签进入theme子页面

**颜色选择验证**:
- [ ] theme子页面显示18个颜色卡片
- [ ] 每个卡片显示标签、颜色预览、选色按钮
- [ ] 颜色预览矩形显示当前颜色
- [ ] 点击任意"选色"按钮打开ColorDialog
- [ ] ColorDialog初始颜色与预览矩形一致
- [ ] 选择新颜色点击"确定"，预览矩形立即更新

**全局响应验证**:
- [ ] 修改background，整个应用背景色改变
- [ ] 修改textPrimary，所有主要文本颜色改变
- [ ] 修改buttonBase，所有按钮基础色改变
- [ ] 修改accentAlarm，报警相关元素颜色改变
- [ ] 切换到其他视图（Status、Alarms等），颜色保持修改后的值

**命令面板验证**:
- [ ] 命令面板显示"调色命令"区域
- [ ] 点击"重置默认配色"按钮，所有颜色恢复初始值
- [ ] 点击"导出当前配色到日志"按钮，控制台输出JSON

**边界条件验证**:
- [ ] 快速连续修改多个颜色，无崩溃或卡顿
- [ ] 打开ColorDialog后点击"取消"，颜色不变
- [ ] 重置配色后再修改，功能正常
- [ ] 切换子页面后返回theme，颜色保持最新值

**性能验证**:
- [ ] 修改颜色后，UI响应延迟 < 100ms
- [ ] 内存占用无异常增长
- [ ] CPU占用无异常峰值

#### 2.4.3 验证方法
1. **手动UI测试**: 主要验证方法，覆盖所有功能点
2. **控制台日志检查**: 确认无报错和警告
3. **Python后端测试**: 确保GUI修改未破坏后端逻辑
   ```bash
   cd /home/say/code/python/VOC_Project
   python -m pytest tests/
   ```

#### 2.4.4 问题记录模板
```markdown
## 验证问题记录

### 问题1: [简要描述]
- **发现时间**: YYYY-MM-DD HH:mm:ss
- **严重程度**: [Critical/Major/Minor/Trivial]
- **复现步骤**:
  1. ...
  2. ...
- **预期行为**: ...
- **实际行为**: ...
- **截图/日志**: ...
- **解决方案**: ...
- **验证状态**: [Open/Fixed/Verified]
```

#### 2.4.5 验收标准
- [ ] 所有验证清单项通过
- [ ] 无Critical或Major问题
- [ ] Minor问题已记录并评估影响
- [ ] Python单元测试全部通过
- [ ] 生成验证报告文档（.claude/verification-report.md）

#### 2.4.6 风险评估
- **风险等级**: 低
- **潜在问题**:
  1. ColorDialog在特定环境可能无法显示
  2. 某些颜色角色未被所有组件使用，修改后无明显效果
- **缓解措施**:
  1. 在验证报告中记录环境兼容性问题
  2. 在UI中添加提示文本说明各颜色角色的用途

---

## 三、验收契约

### 3.1 成功标准

#### 功能性标准
1. ✅ **颜色选择功能**:
   - 用户能通过UI界面修改18个颜色角色
   - 使用ColorDialog选择颜色（或TextField备用）
   - 修改后立即全局生效

2. ✅ **导航与布局**:
   - Config主页面显示"调色"导航标签
   - 点击导航进入theme子页面
   - 子页面显示18个颜色卡片，布局清晰

3. ✅ **交互反馈**:
   - 颜色预览矩形实时显示当前颜色
   - 全局UI自动响应颜色变化
   - 重置功能恢复默认配色

4. ✅ **命令面板集成**:
   - 命令面板显示调色相关按钮
   - 重置、导出功能正常工作

#### 质量标准
1. ✅ **代码规范**:
   - 遵循项目命名约定（文件名、属性名、函数名）
   - 遵循导入顺序规范
   - 使用简体中文注释和说明文本
   - 使用Components.UiTheme工具函数

2. ✅ **架构一致性**:
   - 复用现有组件（CustomButton、Loader、UiTheme）
   - 遵循既有子页面模式（loadportComponent、foupComponent）
   - 符合命令面板加载机制

3. ✅ **性能要求**:
   - 颜色修改响应延迟 < 100ms
   - 无内存泄漏或异常占用
   - 支持至少100次连续修改不崩溃

4. ✅ **兼容性**:
   - 在目标Qt版本正常运行（Qt 6.x）
   - ColorDialog不可用时有降级方案
   - 不破坏现有功能（Python单元测试通过）

### 3.2 交付物清单

#### 代码文件
1. ✅ **src/voc_app/gui/qml/components/UiTheme.qml**
   - 新增: createDefaultPalette() 函数
   - 行数: +12行

2. ✅ **src/voc_app/gui/qml/views/ConfigView.qml**
   - 新增: themeComponent (Component)
   - 新增: 辅助函数（updatePaletteColor, resetPalette等）
   - 新增: colorRoleModel 数据模型
   - 修改: Loader.sourceComponent 逻辑
   - 行数: +120行

3. ✅ **src/voc_app/gui/qml/InformationPanel.qml**
   - 修改: subNavigationConfig["Config"] 数组
   - 行数: +1行

4. ✅ **src/voc_app/gui/qml/commands/Config_themeCommands.qml**
   - 已存在，无需修改
   - 状态: 待提交

#### 文档文件
1. ✅ **.claude/context-summary-theme-color-picker.md**
   - 上下文摘要（已生成）

2. ✅ **.claude/operations-log.md**
   - 操作日志（持续更新）

3. ✅ **.claude/task-plan-theme-color-picker.md**
   - 详细实施计划（本文件）

4. ✅ **.claude/verification-report.md**
   - 验证报告（任务4完成后生成）

### 3.3 排除项
以下功能明确不包含在本次实施范围内：
- ❌ 配色持久化存储（重启后丢失）
- ❌ 预设主题切换（深色/浅色主题）
- ❌ 导入/导出配色文件
- ❌ 颜色修改历史记录
- ❌ 撤销/重做功能
- ❌ 颜色格式转换（RGB/HSL/HSV）
- ❌ 取色器工具（从屏幕取色）

如用户需要上述功能，需单独评估并制定计划。

---

## 四、实施顺序与时间规划

### 4.1 实施顺序（严格按序）
```
TASK-001 (UiTheme.qml)
   ↓
TASK-002 (ConfigView.qml)
   ↓
TASK-003 (InformationPanel.qml)
   ↓
TASK-004 (功能验证)
```

### 4.2 时间规划
| 任务ID | 任务名称 | 预计时间 | 累计时间 |
|--------|----------|----------|----------|
| TASK-001 | 修复createDefaultPalette() | 5分钟 | 5分钟 |
| TASK-002 | 实现theme子页面 | 40分钟 | 45分钟 |
| TASK-003 | 添加导航项 | 3分钟 | 48分钟 |
| TASK-004 | 功能验证 | 15分钟 | 63分钟 |
| **总计** | | **63分钟** | |

### 4.3 里程碑
- **M1**: TASK-001完成 → 重置功能可用（5分钟）
- **M2**: TASK-002完成 → 颜色选择功能可用（45分钟）
- **M3**: TASK-003完成 → 导航入口可用（48分钟）
- **M4**: TASK-004完成 → 功能全量验证通过（63分钟）

---

## 五、风险管理

### 5.1 技术风险

#### 风险1: ColorDialog在WSL环境无法显示
- **概率**: 中（30%）
- **影响**: 高（核心功能受阻）
- **缓解措施**:
  1. 预先测试ColorDialog可用性
  2. 准备TextField降级方案
  3. 提供"#RRGGBB"格式输入提示
- **应急预案**:
  ```qml
  // 降级方案：使用TextField替代ColorDialog
  TextField {
      text: Components.UiTheme.color(roleKey)
      validator: RegularExpressionValidator {
          regularExpression: /^#[0-9a-fA-F]{6}$/
      }
      onAccepted: updatePaletteColor(roleKey, text)
  }
  ```

#### 风险2: palette修改触发大量重绘导致性能问题
- **概率**: 低（10%）
- **影响**: 中（用户体验受损）
- **缓解措施**:
  1. 使用JSON.parse/stringify克隆，避免中间状态
  2. 测试修改100次颜色的性能表现
  3. 必要时添加防抖机制
- **应急预案**:
  ```qml
  // 防抖机制
  Timer {
      id: paletteUpdateTimer
      interval: 100
      onTriggered: Components.UiTheme.palette = pendingPalette
  }
  function updatePaletteColorDebounced(key, value) {
      pendingPalette[key] = value
      paletteUpdateTimer.restart()
  }
  ```

#### 风险3: 颜色角色未被所有组件使用
- **概率**: 高（50%）
- **影响**: 低（部分颜色修改无明显效果）
- **缓解措施**:
  1. 在UI中添加颜色角色用途说明
  2. 提供示例组件展示各颜色角色效果
- **接受风险**: 本次不实现完整的颜色预览面板

### 5.2 流程风险

#### 风险4: 实现代码与截图不一致
- **概率**: 中（20%）
- **影响**: 中（用户期望不匹配）
- **缓解措施**:
  1. 严格参考docs/color.png截图
  2. 实现后与截图逐项对比
  3. 发现差异立即调整
- **决策规则**: 以用户确认为准，截图仅作参考

#### 风险5: Config_themeCommands.qml与实现脱节
- **概率**: 低（5%）
- **影响**: 低（命令面板功能受损）
- **缓解措施**:
  1. 验证阶段测试命令面板所有按钮
  2. 确保createDefaultPalette()调用成功
- **应急预案**: 修复Config_themeCommands.qml代码

### 5.3 质量风险

#### 风险6: 验证不充分导致潜在缺陷
- **概率**: 中（30%）
- **影响**: 中（发布后发现问题）
- **缓解措施**:
  1. 执行完整验证清单（25项）
  2. 运行Python单元测试
  3. 生成验证报告留存
- **质量门禁**: 验证清单通过率 ≥ 95%

---

## 六、附录

### 6.1 技术参考

#### Qt ColorDialog文档
- **模块**: QtQuick.Dialogs
- **最低版本**: Qt 6.2
- **关键属性**:
  - `selectedColor`: color类型，当前选中的颜色
  - `currentColor`: color类型，对话框内正在调整的颜色
- **关键信号**:
  - `accepted()`: 用户点击"确定"时触发
  - `rejected()`: 用户点击"取消"时触发
- **示例代码**:
  ```qml
  ColorDialog {
      id: colorDialog
      selectedColor: "#ffffff"
      onAccepted: {
          console.log("选中颜色:", selectedColor)
      }
  }
  Button {
      text: "选择颜色"
      onClicked: colorDialog.open()
  }
  ```

#### QML Property Binding机制
- **工作原理**: 属性A依赖属性B时，B变化自动触发A重新计算
- **触发条件**: 属性被重新赋值（即使值相同也触发）
- **对象属性绑定**:
  - ❌ 错误: `palette.background = "#000000"` （不触发绑定）
  - ✅ 正确: `palette = newPaletteObject` （触发绑定）
- **最佳实践**:
  ```qml
  // 修改对象属性需要重新赋值
  function updateObjectProperty(obj, key, value) {
      const next = JSON.parse(JSON.stringify(obj))
      next[key] = value
      return next
  }
  palette = updateObjectProperty(palette, "background", "#000000")
  ```

### 6.2 18个颜色角色详解

| 序号 | key | 中文标签 | 默认值 | 用途说明 |
|------|-----|----------|--------|----------|
| 1 | background | 背景 | #050505 | 应用最外层背景 |
| 2 | surface | 表面 | #121212 | 卡片、对话框背景 |
| 3 | panel | 面板 | #1e1e1e | 信息面板、侧边栏背景 |
| 4 | panelAlt | 面板替代 | #2d2d2d | 嵌套面板、高亮区域 |
| 5 | outline | 边框 | #666666 | 默认边框、分隔线 |
| 6 | outlineStrong | 边框(强) | #999999 | 强调边框、激活状态 |
| 7 | buttonBase | 按钮基础 | #333333 | 按钮默认背景 |
| 8 | buttonHover | 按钮悬停 | #444444 | 按钮鼠标悬停时背景 |
| 9 | buttonDown | 按钮按下 | #555555 | 按钮按下时背景 |
| 10 | textPrimary | 文本主色 | #ffffff | 主要文本、标题 |
| 11 | textSecondary | 文本次色 | #e0e0e0 | 次要文本、说明 |
| 12 | textOnLight | 亮底文本 | #000000 | 浅色背景上的文本 |
| 13 | textOnLightMuted | 亮底柔和文本 | #333333 | 浅色背景上的次要文本 |
| 14 | accentInfo | 强调(信息) | #2979ff | 信息提示、链接 |
| 15 | accentSuccess | 强调(成功) | #00e676 | 成功状态、正常指示 |
| 16 | accentWarning | 强调(警告) | #ffab00 | 警告状态、注意提示 |
| 17 | accentAlarm | 强调(报警) | #ff1744 | 报警状态、错误提示 |

### 6.3 代码风格规范摘要

**文件命名**:
- QML文件: PascalCase（ConfigView.qml）
- 子命令文件: {View}_{subpage}Commands.qml

**标识符命名**:
- 组件ID: camelCase（configView, colorDialog）
- 属性: camelCase（currentSubPage, scaleFactor）
- 函数: camelCase（updatePaletteColor, resetPalette）
- 常量: camelCase（readonly property var colorRoleModel）

**导入顺序**:
```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"
import "../components" as Components
```

**注释规范**:
- 必须使用简体中文
- 描述意图而非重复代码
- 复杂逻辑添加行内注释

**缩进与格式**:
- 4空格缩进（禁用Tab）
- 属性顺序: id → property → readonly property → function → signal
- 左花括号不换行

---

## 七、执行确认

### 7.1 编码前最后检查
- [x] 已阅读上下文摘要文件: .claude/context-summary-theme-color-picker.md
- [x] 已理解18个颜色角色定义及用途
- [x] 已理解UiTheme单例 + 属性绑定架构
- [x] 已理解palette对象修改需克隆机制
- [x] 已确认ColorDialog可用性（或准备降级方案）
- [x] 已明确验收标准和质量门禁

### 7.2 风险确认
- [x] 已识别5个主要风险并制定缓解措施
- [x] 已准备ColorDialog降级方案
- [x] 已评估性能风险并准备防抖机制
- [x] 已制定回滚方案

### 7.3 执行授权
- [ ] 用户确认计划可行性
- [ ] 用户确认功能边界（排除持久化、预设主题等）
- [ ] 用户确认可以开始实施

**等待用户指令**: 请确认本计划，或提出调整建议后开始实施。

---

**文档版本**: v1.0
**生成时间**: 2025-11-27 16:52:00
**预计完成时间**: 2025-11-27 18:00:00（执行+验证）
**文档路径**: /home/say/code/python/VOC_Project/.claude/task-plan-theme-color-picker.md
