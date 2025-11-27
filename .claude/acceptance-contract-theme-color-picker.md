# 动态颜色选择功能 - 验收契约

**项目**: VOC_Project
**功能**: 动态颜色选择
**生成时间**: 2025-11-27 16:53:00
**计划文档**: .claude/task-plan-theme-color-picker.md

---

## 一、功能性验收标准

### 1.1 核心功能（必须全部通过）

#### ✅ 颜色选择功能
- [ ] 用户能通过UI界面访问调色子页面
- [ ] 显示18个颜色角色的选择卡片
- [ ] 点击"选色"按钮打开颜色选择器
- [ ] 选择颜色后立即更新palette
- [ ] 全局UI自动响应颜色变化

#### ✅ 导航与入口
- [ ] Config主页面子导航栏显示"调色"标签
- [ ] 点击"调色"标签进入theme子页面
- [ ] 子页面布局与参考截图一致

#### ✅ 交互反馈
- [ ] 颜色预览矩形实时显示当前颜色值
- [ ] 修改颜色后全局UI立即刷新
- [ ] 颜色选择器初始颜色为当前角色颜色

#### ✅ 辅助功能
- [ ] "重置默认配色"按钮恢复初始配色
- [ ] "导出当前配色到日志"按钮输出JSON
- [ ] 命令面板正确加载Config_themeCommands.qml

### 1.2 边界条件（必须全部通过）

- [ ] 快速连续修改多个颜色，无崩溃或卡顿
- [ ] 打开颜色选择器后点击"取消"，颜色不变
- [ ] 重置配色后再修改，功能正常
- [ ] 切换子页面后返回theme，颜色保持最新值
- [ ] 修改后切换到其他主视图（Status、Alarms），颜色保持

---

## 二、技术性验收标准

### 2.1 代码质量（必须全部通过）

#### ✅ 代码规范
- [ ] 文件命名符合PascalCase规范
- [ ] 属性/函数命名符合camelCase规范
- [ ] 导入顺序符合项目约定
- [ ] 所有注释和文本使用简体中文

#### ✅ 架构一致性
- [ ] 复用UiTheme单例（不创建新主题系统）
- [ ] 复用CustomButton组件（不内联按钮）
- [ ] 复用Loader机制（不手动if/else切换）
- [ ] 遵循既有子页面模式（参考loadportComponent）

#### ✅ 实现完整性
- [ ] UiTheme.qml包含createDefaultPalette()函数
- [ ] ConfigView.qml包含themeComponent定义
- [ ] InformationPanel.qml包含theme导航项
- [ ] palette修改使用克隆机制（JSON.parse/stringify）

### 2.2 接口契约（必须全部通过）

#### ✅ createDefaultPalette()函数
```qml
// 签名
function createDefaultPalette(): Object

// 返回值
{
    background: "#050505",
    surface: "#121212",
    panel: "#1e1e1e",
    panelAlt: "#2d2d2d",
    outline: "#666666",
    outlineStrong: "#999999",
    buttonBase: "#333333",
    buttonHover: "#444444",
    buttonDown: "#555555",
    textPrimary: "#ffffff",
    textSecondary: "#e0e0e0",
    textOnLight: "#000000",
    textOnLightMuted: "#333333",
    accentInfo: "#2979ff",
    accentSuccess: "#00e676",
    accentWarning: "#ffab00",
    accentAlarm: "#ff1744"
}

// 验证
- [ ] 返回对象包含18个键值对
- [ ] 所有值为"#RRGGBB"格式
- [ ] 每次调用返回新对象（深拷贝）
```

#### ✅ updatePaletteColor()函数
```qml
// 签名
function updatePaletteColor(roleKey: string, colorValue: color): void

// 行为
1. 克隆当前UiTheme.palette
2. 修改指定角色颜色
3. 重新赋值UiTheme.palette触发绑定

// 验证
- [ ] 修改后UiTheme.palette[roleKey] === colorValue
- [ ] 全局UI自动刷新
- [ ] 不修改原palette对象（深拷贝）
```

#### ✅ 子导航配置
```qml
// InformationPanel.qml
subNavigationConfig["Config"] = [
    { key: "loadport", title: "Loadport" },
    { key: "foup", title: "FOUP" },
    { key: "theme", title: "调色" }
]

// 验证
- [ ] 数组长度为3
- [ ] theme项为第3项
- [ ] key值为"theme"（匹配ConfigView逻辑）
```

---

## 三、性能验收标准

### 3.1 响应性能（必须全部通过）

- [ ] 颜色修改后UI响应延迟 < 100ms
- [ ] 连续修改100次颜色无卡顿
- [ ] 打开/关闭颜色选择器延迟 < 50ms

### 3.2 资源占用（必须全部通过）

- [ ] 内存占用增长 < 10MB（相比未实现前）
- [ ] CPU占用峰值 < 30%（单核）
- [ ] 无内存泄漏（连续使用30分钟无异常增长）

---

## 四、兼容性验收标准

### 4.1 环境兼容性（必须全部通过）

- [ ] Qt 6.x 环境正常运行
- [ ] ColorDialog可用或已实现降级方案
- [ ] WSL环境下功能正常（如有显示后端）

### 4.2 功能兼容性（必须全部通过）

- [ ] 不破坏现有功能（Status、Alarms、DataLog等）
- [ ] Python后端单元测试全部通过
- [ ] 现有命令面板功能正常（非theme子命令）

---

## 五、文档验收标准

### 5.1 代码文档（必须全部通过）

- [ ] 关键函数有简体中文注释
- [ ] 复杂逻辑有实现说明
- [ ] 颜色角色用途有注释说明

### 5.2 交付文档（必须全部通过）

- [ ] 上下文摘要: .claude/context-summary-theme-color-picker.md
- [ ] 操作日志: .claude/operations-log.md
- [ ] 任务计划: .claude/task-plan-theme-color-picker.md
- [ ] 验收契约: .claude/acceptance-contract-theme-color-picker.md（本文件）
- [ ] 验证报告: .claude/verification-report.md（验证完成后生成）

---

## 六、质量门禁

### 6.1 通过标准
- 功能性验收: 通过率 ≥ 95%（至多1项Minor问题）
- 技术性验收: 通过率 = 100%（零容忍）
- 性能验收: 通过率 = 100%（零容忍）
- 兼容性验收: 通过率 = 100%（零容忍）
- 文档验收: 通过率 = 100%（零容忍）

### 6.2 拒绝标准
以下任一条件触发，验收不通过：
- ❌ 存在Critical或Major级别缺陷
- ❌ 核心功能不可用（颜色选择、全局响应）
- ❌ Python单元测试失败
- ❌ 性能指标超标（响应 > 100ms，内存增长 > 10MB）
- ❌ 代码规范违反（命名、导入、注释）

### 6.3 有条件通过
以下情况可有条件通过：
- ⚠️ ColorDialog在WSL环境不可用，但已实现TextField降级方案
- ⚠️ 部分颜色角色未被所有组件使用，但已在UI中说明
- ⚠️ 存在≤2个Trivial级别问题，但已记录到issues

---

## 七、验收流程

### 7.1 验收步骤
1. **代码实现完成** → 提交验收申请
2. **执行验证清单** → 记录每项检查结果
3. **运行Python单测** → 确认后端未破坏
4. **生成验证报告** → .claude/verification-report.md
5. **评估质量门禁** → 判定通过/拒绝/有条件通过
6. **用户确认** → 最终验收决策

### 7.2 验收角色
- **实施者**: Claude Code（编码 + 自验证）
- **验收者**: Claude Code（质量审查）
- **最终确认**: 用户

### 7.3 验收时间
- 预计验收时间: TASK-004（任务4：功能验证）
- 预计时长: 15分钟
- 包含: 手动UI测试 + Python单测 + 报告生成

---

## 八、风险声明

### 8.1 已知限制
本次实施明确不包含以下功能：
- ❌ 配色持久化存储（重启后恢复默认）
- ❌ 预设主题切换（深色/浅色）
- ❌ 导入/导出配色文件
- ❌ 颜色修改历史记录
- ❌ 撤销/重做功能

如用户需要上述功能，需单独立项评估。

### 8.2 环境依赖
- 需要Qt 6.x环境
- 需要QtQuick.Dialogs模块可用
- 需要显示后端（X11/Wayland）以显示ColorDialog

### 8.3 降级方案
如ColorDialog不可用，自动降级为TextField手动输入：
- 格式验证: 正则表达式 `^#[0-9a-fA-F]{6}$`
- 实时反馈: 输入框边框颜色提示
- 用户体验: 略低于图形化选择器，但功能完整

---

## 九、签署确认

### 9.1 计划确认
- [x] 已阅读完整任务计划（task-plan-theme-color-picker.md）
- [x] 已理解验收标准和质量门禁
- [x] 已明确功能边界和排除项

### 9.2 实施授权
- [ ] 用户确认计划可行
- [ ] 用户确认验收标准合理
- [ ] 授权开始实施

### 9.3 验收承诺
- [ ] 实施者承诺按计划执行
- [ ] 验收者承诺客观评估
- [ ] 双方承诺遵守质量门禁

---

**契约版本**: v1.0
**生成时间**: 2025-11-27 16:53:00
**有效期**: 至任务完成或用户明确终止
**文档路径**: /home/say/code/python/VOC_Project/.claude/acceptance-contract-theme-color-picker.md

---

## 附录：快速验收清单

用于快速检查验收通过条件，完整清单见上文。

### 快速核心检查（10项）
- [ ] 1. Config页面显示"调色"导航标签
- [ ] 2. 点击"调色"进入theme子页面
- [ ] 3. 显示18个颜色卡片
- [ ] 4. 点击"选色"打开颜色选择器
- [ ] 5. 选择颜色后全局UI立即更新
- [ ] 6. "重置默认配色"按钮恢复初始值
- [ ] 7. Python单元测试全部通过
- [ ] 8. 颜色修改响应 < 100ms
- [ ] 9. 无Critical/Major缺陷
- [ ] 10. 所有文档已生成

**快速判定**:
- ✅ 10/10 → 验收通过
- ⚠️ 9/10 → 审查Minor问题后决定
- ❌ ≤8/10 → 验收拒绝，返回修复

---

**准备状态**: 等待用户确认后开始实施
