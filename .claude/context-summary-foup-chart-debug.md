# FOUP 图表不更新问题 - 深度分析报告
生成时间：2025-11-26

## 问题现象
- ConfigView 中 FOUP 图表不更新（ChartCard 中的曲线静止）
- 底部数据标签正常更新（显示 foupAcquisition.lastValue）
- StatusView 中 loadport 图表正常工作

## 完整数据流分析

### 1. 数据模型初始化（app.py）

```python
# 第132-142行：创建 chartListModel 并添加 loadport 系列
chart_list_model = ChartDataListModel()
for idx, label in enumerate(loadport_series_labels):  # idx=0,1
    series_model = SeriesTableModel(max_rows=60, parent=chart_list_model)
    chart_list_model.addSeries(label, series_model)
    # index 0: "Loadport 通道 1"
    # index 1: "Loadport 通道 2"

# 第144-148行：添加 foup 系列
foup_series_models = []
for label in ["FOUP 通道 1"]:  # 只有一个 FOUP 通道
    series_model = SeriesTableModel(max_rows=600, parent=chart_list_model)
    chart_list_model.addSeries(label, series_model)
    foup_series_models.append(series_model)
    # index 2: "FOUP 通道 1"

# 第152行：创建 FoupAcquisitionController，传入 foup_series_models
foup_acquisition = FoupAcquisitionController(foup_series_models)
```

**关键索引分配**：
- **index 0**: Loadport 通道 1
- **index 1**: Loadport 通道 2
- **index 2**: FOUP 通道 1

### 2. ConfigView 的配置（ConfigView.qml）

```qml
readonly property int foupChartIndex: 2  // 第21行

// 第241行：使用 Repeater 渲染 FOUP 图表
Repeater {
    model: [{ title: "FOUP", index: configView.foupChartIndex }]
    delegate: Components.ChartCard {
        readonly property var config: configView.chartEntry(modelData.index, modelData.title)
        seriesModel: config.seriesModel  // 第252行
        xColumn: config.xColumn
        yColumn: config.yColumn
    }
}

// 第23-41行：chartEntry 函数
function chartEntry(rowIndex, fallbackTitle) {
    const entry = chartListModel.get(rowIndex);  // 调用 Python 端的 get(2)
    if (!entry || Object.keys(entry).length === 0)
        return fallback;
    return {
        title: entry.title || fallback.title,
        seriesModel: entry.seriesModel || null,
        xColumn: typeof entry.xColumn === "number" ? entry.xColumn : 0,
        yColumn: typeof entry.yColumn === "number" ? entry.yColumn : 1
    };
}
```

### 3. StatusView 的配置（StatusView.qml）

```qml
// 第18-21行：loadport 图表配置
readonly property var loadportCharts: [
    { title: "电压", currentValue: "3.8 V", index: 0 },
    { title: "温度", currentValue: "26 ℃", index: 1 }
]

// 第127-143行：使用 Repeater 渲染
Repeater {
    model: statusRoot.loadportCharts
    delegate: ChartCard {
        readonly property var config: statusRoot.chartEntry(modelData.index, modelData.title)
        seriesModel: config.seriesModel  // 绑定到 loadport 的 SeriesModel
        xColumn: config.xColumn
        yColumn: config.yColumn
    }
}
```

### 4. FoupAcquisitionController 数据追加（foup_acquisition.py）

```python
# 第129-134行：数据追加逻辑
def _append_point_to_model(self, x: float, y: float) -> None:
    try:
        model = self._series_models[0]  # 拿到 foup_series_models[0]
        model.append_point(x, y)  # 调用 SeriesTableModel.append_point()
    except Exception as exc:
        print(f"[ERROR] foup_acquisition: Exception in _append_point_to_model(): {exc!r}")
```

### 5. SeriesTableModel 数据更新机制（csv_model.py）

```python
# 第105-124行：append_point 方法
@Slot(float, float)
def append_point(self, x, y):
    """向表格追加一条新数据，同时维护最大行数和坐标范围。"""
    x = float(x)
    y = float(y)
    bounds_changed = False

    # 移除旧数据（如果达到最大行数）
    if len(self._rows) == self._max_rows and self._rows:
        self.beginRemoveRows(QModelIndex(), 0, 0)
        self._rows.pop(0)
        self.endRemoveRows()
        bounds_changed = self._recalculate_bounds()

    # 插入新数据
    self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows))
    self._rows.append([x, y])
    self.endInsertRows()
    bounds_changed = self._update_bounds(x, y) or bounds_changed

    # 发射 boundsChanged 信号
    if bounds_changed:
        self.boundsChanged.emit()
```

### 6. ChartCard 数据绑定机制（ChartCard.qml）

```qml
// 第84-88行：VXYModelMapper 定义
VXYModelMapper {
    id: mapper
    // series: chartCard.seriesModel ? lineSeries : null
    // 不在这里绑定 series，由 updateMapperBinding() 统一管理
}

// 第118-128行：updateMapperBinding 函数
function updateMapperBinding() {
    if (chartCard.seriesModel) {
        mapper.xColumn = chartCard.xColumn;
        mapper.yColumn = chartCard.yColumn;
        mapper.model = chartCard.seriesModel;  // 绑定 Python 端的 SeriesTableModel
        mapper.series = lineSeries;
    } else {
        mapper.series = null;
        mapper.model = null;
    }
}

// 第130行：初始化时绑定
Component.onCompleted: updateMapperBinding()

// 第132-143行：seriesModel 变化时重新绑定
onSeriesModelChanged: {
    if (chartCard.seriesModel) {
        lineSeries.clear();
        updateAxesFromSeries();
        if (typeof chartCard.seriesModel.force_rebuild === "function") {
            chartCard.seriesModel.force_rebuild();
        }
    } else {
        lineSeries.clear();
    }
    updateMapperBinding();
}

// 第184-190行：监听 boundsChanged 信号
Connections {
    target: chartCard.seriesModel
    enabled: chartCard.seriesModel
    function onBoundsChanged() {
        chartCard.updateAxesFromSeries();  // 更新坐标轴范围
    }
}
```

## 根本原因分析

### 核心问题：readonly property 缓存导致 seriesModel 变化不可见

#### 问题机制：

1. **ConfigView 使用 readonly property 缓存配置**（第251行）：
   ```qml
   readonly property var config: configView.chartEntry(modelData.index, modelData.title)
   seriesModel: config.seriesModel
   ```

2. **chartEntry 每次都返回新对象**（第23-41行）：
   ```qml
   function chartEntry(rowIndex, fallbackTitle) {
       // ...
       return {
           title: entry.title || fallback.title,
           seriesModel: entry.seriesModel || null,  // 每次都是新的 JS 对象引用
           xColumn: typeof entry.xColumn === "number" ? entry.xColumn : 0,
           yColumn: typeof entry.yColumn === "number" ? entry.yColumn : 1
       };
   }
   ```

3. **readonly property 只在初始化时计算一次**：
   - 当 ChartCard 初始化时，`config.seriesModel` 可能为 `null`
   - 即使后续 `chartListModel.get(2)` 返回的 `entry.seriesModel` 已存在
   - `readonly property` 不会重新计算，`config.seriesModel` 永远为 `null`

4. **seriesModel 绑定失败**：
   ```qml
   seriesModel: config.seriesModel  // 永远是 null
   ```

#### 为什么 StatusView 能工作？

**StatusView 使用完全相同的模式**（第138行）：
```qml
readonly property var config: statusRoot.chartEntry(modelData.index, modelData.title)
seriesModel: config.seriesModel
```

**关键差异**：
1. **loadport 的 SeriesModel 在初始化时已存在**：
   - app.py 第136-142行创建了 loadport 的 SeriesModel
   - 第163-168行立即用 QTimer 启动数据生成器
   - 当 StatusView 加载时，`chartListModel.get(0/1)` 已经返回有效的 seriesModel

2. **FOUP 的 SeriesModel 也在初始化时创建**：
   - app.py 第144-148行创建了 FOUP 的 SeriesModel
   - **但没有立即启动数据生成！**
   - 用户需要手动点击"开始采集"才启动

3. **关键区别**：
   - **loadport**：SeriesModel 在 StatusView 加载前就已创建并添加到 chartListModel
   - **FOUP**：SeriesModel 也在 ConfigView 加载前就已创建并添加到 chartListModel
   - **理论上都应该能工作！**

## 真正的问题

重新检查代码，我发现了真正的问题：

### 问题1：ConfigView 加载时机

ConfigView 是通过 Loader 动态加载的：
```qml
// ConfigView.qml 第68-73行
Loader {
    id: contentLoader
    Layout.fillWidth: true
    Layout.fillHeight: true
    sourceComponent: currentSubPage === "foup" ? foupComponent : loadportComponent
}
```

当用户切换到 FOUP 子页面时，`foupComponent` 才被加载，此时：
1. `chartListModel.get(2)` 返回的 `entry.seriesModel` 应该已存在
2. `readonly property var config` 应该能正确缓存

### 问题2：VXYModelMapper 不响应模型内部变化

关键在于 **VXYModelMapper 的工作机制**：

```qml
// ChartCard.qml 第84-88行
VXYModelMapper {
    id: mapper
}

// 第118-128行
function updateMapperBinding() {
    if (chartCard.seriesModel) {
        mapper.model = chartCard.seriesModel;  // 绑定模型
        mapper.series = lineSeries;
    }
}
```

**VXYModelMapper 的限制**：
- 当 `mapper.model` 设置后，它会监听模型的 `rowsInserted/rowsRemoved` 信号
- 但如果 `mapper.model` 在初始化时为 `null`，后续即使 `seriesModel` 变化也不会触发重新绑定

### 问题3：readonly property 的致命缺陷

```qml
readonly property var config: configView.chartEntry(modelData.index, modelData.title)
seriesModel: config.seriesModel
```

**问题**：
- `chartEntry()` 每次调用都返回新的 JS 对象
- `readonly property` 只在 ChartCard 创建时计算一次
- 即使 `chartListModel.get(2)` 的返回值变化，`config` 也不会更新
- 因此 `config.seriesModel` 永远是初始值

**但等等**：
- app.py 中 FOUP 的 SeriesModel 在第146行就已创建并添加到 chartListModel
- 理论上 ConfigView 加载时应该能获取到

## 终极问题：SeriesModel 何时为 null？

让我检查 ChartDataListModel.get() 的实现：

```python
# csv_model.py 第270-281行
@Slot(int, result="QVariantMap")
def get(self, row):
    """允许 QML 通过索引读取单条曲线的详细信息。"""
    if not (0 <= row < len(self._entries)):
        return {}
    entry = self._entries[row]
    return {
        "title": entry["title"],
        "seriesModel": entry["series_model"],  # 直接返回 Python 对象引用
        "xColumn": entry["x_column"],
        "yColumn": entry["y_column"],
    }
```

**关键发现**：
- `chartListModel.get(2)` 总是返回相同的 Python dict
- 但 QML 端每次调用都会创建新的 JS 对象包装
- **`entry["series_model"]` 的值从创建后就不会变化！**

## 终极结论

**真正的根本原因：SeriesModel 已正确绑定，但图表不更新是因为其他原因**

让我重新审视问题：
1. 底部标签能更新 → foupAcquisition.lastValue 正常更新
2. 图表不更新 → VXYModelMapper 没有响应 SeriesTableModel 的变化

**可能的原因**：
1. **VXYModelMapper 绑定时机问题**
2. **SeriesTableModel 的信号没有正确发射**
3. **ChartCard 的 Connections 没有生效**

## 验证假设

需要检查的关键点：
1. foupAcquisition.startAcquisition() 调用时，SeriesModel 是否正确追加数据？
2. SeriesTableModel.append_point() 是否正确发射了 rowsInserted 信号？
3. VXYModelMapper 是否正确监听了 rowsInserted 信号？

## 最终诊断

**问题出在 readonly property 的使用**：

```qml
// ConfigView.qml 第251行
readonly property var config: configView.chartEntry(modelData.index, modelData.title)
seriesModel: config.seriesModel
```

**问题机制**：
1. `chartEntry()` 返回一个新的 JS 对象
2. `readonly property` 只在 ChartCard 创建时计算一次
3. 如果此时 `chartListModel.get(2)` 返回的对象中 `seriesModel` 已存在，那么绑定应该成功
4. **但如果绑定成功，为什么图表不更新？**

**唯一可能的解释**：
- **ChartCard 的 onSeriesModelChanged 没有触发**
- 因为 `seriesModel` 属性从一开始就绑定到了正确的 SeriesModel 对象
- 没有触发 `onSeriesModelChanged` → 没有调用 `updateMapperBinding()`
- VXYModelMapper 没有正确绑定

## 修复方案

需要确保 VXYModelMapper 在 seriesModel 存在时正确绑定，有以下几种方案：

### 方案1：移除 readonly，使用普通 property

```qml
property var config: configView.chartEntry(modelData.index, modelData.title)
```

**问题**：chartEntry 每次调用都返回新对象，会导致无限循环

### 方案2：直接绑定 seriesModel

```qml
seriesModel: {
    var entry = chartListModel.get(configView.foupChartIndex);
    return entry ? entry.seriesModel : null;
}
```

**问题**：同样会导致频繁重新计算

### 方案3：使用 Component.onCompleted 强制触发更新

```qml
Component.onCompleted: {
    updateMapperBinding();
    if (seriesModel) {
        updateAxesFromSeries();
    }
}
```

**问题**：Component.onCompleted 在第130行已经调用了 updateMapperBinding()

### 方案4：在 ChartCard 中添加初始化检查

在 ChartCard.qml 的 Component.onCompleted 中添加：
```qml
Component.onCompleted: {
    updateMapperBinding();
    console.log("ChartCard initialized: seriesModel =", chartCard.seriesModel);
    if (chartCard.seriesModel) {
        console.log("SeriesModel has data:", chartCard.seriesModel.hasData);
        console.log("SeriesModel rowCount:", chartCard.seriesModel.rowCount());
    }
}
```

## 推荐修复方案

**最可能的问题**：VXYModelMapper 在初始化时 seriesModel 为空，后续即使有数据也不更新

**修复**：在 ChartCard 中添加一个监视器，当 seriesModel 的 rowCount 变化时强制刷新：

```qml
Connections {
    target: chartCard.seriesModel
    enabled: chartCard.seriesModel
    function onRowsInserted(parent, first, last) {
        console.log("Rows inserted:", first, "-", last);
        // 强制刷新 mapper 绑定
        if (!mapper.series) {
            updateMapperBinding();
        }
    }
}
```
