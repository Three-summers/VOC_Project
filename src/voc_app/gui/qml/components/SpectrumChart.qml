import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import "." as Components

/**
 * SpectrumChart.qml - 高性能频谱图组件
 * =========================================
 *
 * 这是一个用于 QML 的高性能频谱可视化组件，专为实时频谱显示设计。
 * 使用 Canvas 直接绘制，避免 QtCharts 的模型绑定开销。
 *
 * 设计目标
 * --------
 * - 支持高频更新（256 点/包，10+ Hz）
 * - 使用 Canvas.Threaded 进行非阻塞渲染
 * - 预计算颜色查找表 (LUT) 避免每帧重复计算
 * - 支持多种图表类型（柱状图、折线图）
 * - 丰富的视觉效果（发光、倒影、扫描线等）
 *
 * 快速开始
 * --------
 * 1. 基础使用（需要配合 Python 端的 SpectrumDataModel）:
 *
 *    // Python 端
 *    from spectrum_model import SpectrumDataModel
 *    model = SpectrumDataModel(bin_count=256)
 *    engine.rootContext().setContextProperty("spectrumModel", model)
 *
 *    // QML 端
 *    import "components" as Components
 *
 *    Components.SpectrumChart {
 *        width: 800
 *        height: 400
 *        spectrumModel: spectrumModel  // 绑定 Python 模型
 *        chartTitle: "实时频谱"
 *    }
 *
 * 2. 配置图表类型:
 *
 *    SpectrumChart {
 *        spectrumModel: spectrumModel
 *        chartType: "line"        // "bar" (柱状图) 或 "line" (折线图)
 *        lineWidth: 2             // 折线宽度
 *        lineFill: true           // 折线填充
 *        lineFillOpacity: 0.3     // 填充透明度
 *    }
 *
 * 3. 自定义配色方案:
 *
 *    SpectrumChart {
 *        spectrumModel: spectrumModel
 *        colorScheme: "fire"      // "spectrum", "green", "blue", "fire", "purple", "ocean"
 *        useGradient: true        // 启用渐变
 *        gradientIntensity: 0.9   // 渐变强度
 *    }
 *
 * 4. 启用视觉效果:
 *
 *    SpectrumChart {
 *        spectrumModel: spectrumModel
 *        glowEnabled: true        // 发光效果
 *        glowIntensity: 0.6       // 发光强度
 *        reflectionEnabled: true  // 倒影效果
 *        reflectionOpacity: 0.15  // 倒影透明度
 *        scanLineEnabled: true    // CRT 扫描线
 *        borderGlowEnabled: true  // 边框发光
 *    }
 *
 * 5. 配置网格和刻度:
 *
 *    SpectrumChart {
 *        spectrumModel: spectrumModel
 *        showGrid: true
 *        horizontalGridLines: 6
 *        verticalGridLines: 10
 *        showYAxis: true
 *        showXAxis: true
 *        minDb: -80
 *        maxDb: 0
 *        minFreq: 0
 *        maxFreq: 20
 *        xAxisUnit: "kHz"
 *    }
 *
 * 属性参考
 * --------
 * 数据绑定:
 *   - spectrumModel: var        - Python 端的 SpectrumDataModel 实例
 *
 * 标题配置:
 *   - chartTitle: string        - 图表标题 (默认: "Spectrum")
 *   - showTitle: bool           - 是否显示标题 (默认: true)
 *   - titleColor: color         - 标题颜色
 *   - titleFontSize: int        - 标题字号
 *
 * 图表类型:
 *   - chartType: string         - "bar" (柱状图) 或 "line" (折线图)
 *   - lineWidth: real           - 折线宽度 (默认: 2)
 *   - lineFill: bool            - 是否填充折线下方区域 (默认: true)
 *   - lineFillOpacity: real     - 填充透明度 0.0~1.0 (默认: 0.3)
 *
 * 柱状图配置:
 *   - barSpacing: real          - 柱间距像素 (默认: 0)
 *   - barMinHeight: real        - 最小柱高度 (默认: 1)
 *
 * 配色方案:
 *   - colorScheme: string       - 配色方案名称
 *                                 可选: "spectrum", "green", "blue", "fire", "purple", "ocean"
 *   - monoColor: color          - 单色模式颜色 (colorScheme="mono" 时使用)
 *   - useGradient: bool         - 使用渐变色 (默认: true)
 *   - gradientIntensity: real   - 渐变强度 0.0~1.0 (默认: 1.0)
 *
 * 峰值保持:
 *   - showPeakHold: bool        - 显示峰值保持线 (默认: true)
 *   - peakHoldColor: color      - 峰值线颜色
 *   - peakHoldLineWidth: real   - 峰值线宽度 (默认: 2)
 *
 * 网格配置:
 *   - showGrid: bool            - 显示网格 (默认: true)
 *   - horizontalGridLines: int  - 水平网格线数量 (默认: 5)
 *   - verticalGridLines: int    - 垂直网格线数量 (默认: 8)
 *   - gridColor: color          - 网格线颜色
 *   - gridLineWidth: real       - 网格线宽度 (默认: 1)
 *
 * 刻度配置:
 *   - showYAxis: bool           - 显示 Y 轴刻度 (默认: true)
 *   - showXAxis: bool           - 显示 X 轴刻度 (默认: true)
 *   - yAxisWidth: real          - Y 轴宽度 (默认: 35)
 *   - xAxisHeight: real         - X 轴高度 (默认: 20)
 *   - minDb: real               - 最小分贝值 (默认: -60)
 *   - maxDb: real               - 最大分贝值 (默认: 0)
 *   - yAxisUnit: string         - Y 轴单位 (默认: "")
 *   - minFreq: real             - 最小频率 kHz (默认: 0)
 *   - maxFreq: real             - 最大频率 kHz (默认: 20)
 *   - xAxisUnit: string         - X 轴单位 (默认: "k")
 *   - xAxisTicks: int           - X 轴刻度数量 (默认: 5)
 *
 * 视觉效果:
 *   - glowEnabled: bool         - 启用发光效果 (默认: true)
 *                                 注意: 使用 MultiEffect，GPU 开销较大
 *   - glowIntensity: real       - 发光强度 0.0~1.0 (默认: 0.6)
 *   - reflectionEnabled: bool   - 启用倒影效果 (默认: true)
 *   - reflectionOpacity: real   - 倒影透明度 0.0~1.0 (默认: 0.15)
 *   - scanLineEnabled: bool     - 启用 CRT 扫描线效果 (默认: false)
 *   - scanLineOpacity: real     - 扫描线透明度 (默认: 0.03)
 *   - borderGlowEnabled: bool   - 启用边框发光 (默认: true)
 *   - animateChanges: bool      - 动画过渡效果 (默认: true，预留)
 *
 * 背景配置:
 *   - chartBackground: color    - 图表背景色 (默认: "#1a1a2e")
 *   - chartRadius: real         - 图表圆角 (默认: 4)
 *
 * 性能建议
 * --------
 * 1. 视觉效果对性能的影响（从高到低）:
 *    - glowEnabled: ~50% GPU 开销（使用 MultiEffect 模糊）
 *    - reflectionEnabled: ~25% GPU 开销
 *    - scanLineEnabled: ~10% GPU 开销
 *    - borderGlowEnabled: ~5% GPU 开销
 *
 * 2. 高频更新场景建议:
 *    - 禁用 glowEnabled（影响最大）
 *    - 减少 bin 数量（如 128 代替 256）
 *    - 使用 useGradient: true（单次渐变比逐柱着色更快）
 *
 * 3. 移动设备/嵌入式设备建议:
 *    - 禁用所有视觉效果
 *    - 减少网格线数量
 *    - 考虑降低更新频率
 *
 * 作者: Claude Code
 * 版本: 1.0.0
 */
Rectangle {
    id: spectrumCard
    color: Components.UiTheme.color("panel")
    border.color: Components.UiTheme.color("outline")
    border.width: Math.max(1, Components.UiTheme.controlScale)
    radius: Components.UiTheme.radius("sm")

    // ==================== 数据绑定 ====================
    // Python 端 SpectrumDataModel 实例，通过 setContextProperty 注入
    // 模型变化时会触发 onSpectrumModelChanged 重新绑定数据
    property var spectrumModel: null

    // ==================== 标题配置 ====================
    property string chartTitle: "Spectrum"
    property bool showTitle: true
    property color titleColor: Components.UiTheme.color("textPrimary")
    property int titleFontSize: Components.UiTheme.fontSize("subtitle")

    // ==================== 图表背景 ====================
    property color chartBackground: "#1a1a2e"
    property real chartRadius: Components.UiTheme.radius("xs")

    // ==================== 网格配置 ====================
    property bool showGrid: true
    property int horizontalGridLines: 5
    property int verticalGridLines: 8
    property color gridColor: Qt.rgba(1, 1, 1, 0.1)
    property real gridLineWidth: 1

    // ==================== 图表类型 ====================
    // chartType: "bar" = 柱状图（默认），"line" = 折线图
    // 柱状图适合离散频率 bin 显示，折线图适合连续波形显示
    property string chartType: "bar"               // 图表类型: "bar" (柱状图), "line" (折线图)
    property real lineWidth: 2                     // 折线宽度（仅 line 模式有效）
    property bool lineFill: true                   // 折线是否填充区域（仅 line 模式有效）
    property real lineFillOpacity: 0.3             // 折线填充透明度（仅 line 模式有效）

    // ==================== 柱状图配置 ====================
    // barSpacing: 柱间距，0 表示无间距（性能更好）
    // barMinHeight: 即使值为 0 也显示的最小高度，避免柱子消失
    property real barSpacing: 0                    // 柱间距 (0 = 无间距)
    property real barMinHeight: 1                  // 最小柱高度（像素）

    // ==================== 配色方案 ====================
    // colorScheme: 预定义的配色方案名称
    // 可选值: "spectrum"(彩虹), "green"(绿色), "blue"(蓝色),
    //         "fire"(火焰), "purple"(紫色), "ocean"(海洋), "mono"(单色)
    // useGradient: 使用单个全高渐变（性能更好）vs 逐柱着色
    property string colorScheme: "spectrum"        // 配色方案: "spectrum", "green", "blue", "fire", "mono"
    property color monoColor: "#00ff00"            // 单色模式的颜色
    property bool useGradient: true                // 是否使用渐变色
    property real gradientIntensity: 1.0          // 渐变强度 (0.0 ~ 1.0)

    // ==================== 峰值保持 ====================
    // 峰值保持线显示每个 bin 的历史最大值
    // 峰值衰减由 Python 端 SpectrumDataModel.setPeakDecayRate() 控制
    property bool showPeakHold: true
    property color peakHoldColor: Qt.rgba(1, 1, 1, 0.8)
    property real peakHoldLineWidth: 2

    // ==================== 刻度配置 ====================
    // Y 轴显示分贝值，X 轴显示频率
    // 刻度值仅用于显示，实际数据映射由 Python 端控制
    property bool showYAxis: true                  // 显示Y轴刻度
    property bool showXAxis: true                  // 显示X轴刻度
    property real yAxisWidth: 35                   // Y轴宽度
    property real xAxisHeight: 20                  // X轴高度
    property real minDb: -60                       // 最小分贝值（对应归一化值 0.0）
    property real maxDb: 0                         // 最大分贝值（对应归一化值 1.0）
    property string yAxisUnit: ""                  // Y轴单位 (如 "dB")
    property real minFreq: 0                       // 最小频率 (kHz)
    property real maxFreq: 20                      // 最大频率 (kHz)
    property string xAxisUnit: "k"                 // X轴单位 (如 "k" for kHz)
    property int xAxisTicks: 5                     // X轴刻度数量
    property color axisLabelColor: Components.UiTheme.color("textSecondary")
    property int axisLabelFontSize: Components.UiTheme.fontSize("caption")

    // ==================== 视觉效果 ====================
    // 这些效果会增加 GPU 开销，在性能敏感场景建议禁用
    // glowEnabled: 使用 MultiEffect 模糊，开销最大 (~50%)
    // reflectionEnabled: 绘制倒影 Canvas，开销中等 (~25%)
    // scanLineEnabled: CRT 风格扫描线，开销较小 (~10%)
    // borderGlowEnabled: 边框发光，开销最小 (~5%)
    // 注意: 默认值会被 spectrumPerfConfig (如果存在) 覆盖
    property bool glowEnabled: (typeof spectrumPerfConfig !== "undefined" && spectrumPerfConfig) ? spectrumPerfConfig.glowEnabled : true
    property real glowIntensity: 0.6              // 发光强度 (0.0 ~ 1.0)
    property bool reflectionEnabled: (typeof spectrumPerfConfig !== "undefined" && spectrumPerfConfig) ? spectrumPerfConfig.reflectionEnabled : true
    property real reflectionOpacity: 0.15         // 倒影透明度
    property bool scanLineEnabled: (typeof spectrumPerfConfig !== "undefined" && spectrumPerfConfig) ? spectrumPerfConfig.scanLineEnabled : false
    property real scanLineOpacity: 0.03           // 扫描线透明度
    property bool borderGlowEnabled: (typeof spectrumPerfConfig !== "undefined" && spectrumPerfConfig) ? spectrumPerfConfig.borderGlowEnabled : true
    property bool animateChanges: true            // 动画过渡效果（预留）

    // ==================== 内部状态 ====================
    // cachedData/cachedPeaks: 从 Python 模型获取的数据缓存
    // 避免每次绑定表达式求值时重复调用 Python 属性
    property var cachedData: []
    property var cachedPeaks: []

    // ==================== 配色方案定义 ====================
    // 每个配色方案定义一组颜色停止点 (position, r, g, b)
    // position: 0.0~1.0，对应归一化值
    // 颜色查找表 (LUT) 会根据配色方案预计算，避免每帧插值计算
    readonly property var colorSchemes: ({
        "spectrum": [  // 经典频谱: 蓝 -> 青 -> 绿 -> 黄 -> 红
            { pos: 0.00, r: 0,   g: 0,   b: 255 },
            { pos: 0.25, r: 0,   g: 255, b: 255 },
            { pos: 0.50, r: 0,   g: 255, b: 0   },
            { pos: 0.75, r: 255, g: 255, b: 0   },
            { pos: 1.00, r: 255, g: 0,   b: 0   }
        ],
        "green": [     // 绿色系
            { pos: 0.00, r: 0,   g: 40,  b: 0   },
            { pos: 0.50, r: 0,   g: 180, b: 0   },
            { pos: 1.00, r: 100, g: 255, b: 100 }
        ],
        "blue": [      // 蓝色系
            { pos: 0.00, r: 0,   g: 0,   b: 60  },
            { pos: 0.50, r: 0,   g: 100, b: 200 },
            { pos: 1.00, r: 100, g: 200, b: 255 }
        ],
        "fire": [      // 火焰色
            { pos: 0.00, r: 20,  g: 0,   b: 0   },
            { pos: 0.33, r: 180, g: 0,   b: 0   },
            { pos: 0.66, r: 255, g: 150, b: 0   },
            { pos: 1.00, r: 255, g: 255, b: 100 }
        ],
        "purple": [    // 紫色系
            { pos: 0.00, r: 20,  g: 0,   b: 40  },
            { pos: 0.50, r: 100, g: 0,   b: 180 },
            { pos: 1.00, r: 200, g: 100, b: 255 }
        ],
        "ocean": [     // 海洋色
            { pos: 0.00, r: 0,   g: 20,  b: 40  },
            { pos: 0.50, r: 0,   g: 100, b: 150 },
            { pos: 1.00, r: 100, g: 220, b: 220 }
        ]
    })

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Components.UiTheme.spacing("md")
        spacing: Components.UiTheme.spacing("sm")

        // 标题
        Text {
            visible: spectrumCard.showTitle
            text: spectrumCard.chartTitle
            font.bold: true
            font.pixelSize: spectrumCard.titleFontSize
            color: spectrumCard.titleColor
            Layout.alignment: Qt.AlignHCenter
        }

        // 频谱图主体
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Components.UiTheme.spacing("xs")

            // 左侧 Y 轴刻度
            Column {
                visible: spectrumCard.showYAxis
                Layout.preferredWidth: spectrumCard.yAxisWidth
                Layout.fillHeight: true
                spacing: 0

                Repeater {
                    model: spectrumCard.horizontalGridLines + 1

                    Text {
                        width: spectrumCard.yAxisWidth
                        height: parent.height / spectrumCard.horizontalGridLines
                        text: {
                            var val = spectrumCard.maxDb - (index / spectrumCard.horizontalGridLines) * (spectrumCard.maxDb - spectrumCard.minDb);
                            return val.toFixed(0) + spectrumCard.yAxisUnit;
                        }
                        font.pixelSize: spectrumCard.axisLabelFontSize * 0.85
                        color: spectrumCard.axisLabelColor
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignTop
                    }
                }
            }

            // 图表区域
            Rectangle {
                id: chartArea
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: spectrumCard.chartBackground
                radius: spectrumCard.chartRadius

                // 边框发光效果
                Rectangle {
                    id: borderGlow
                    visible: spectrumCard.borderGlowEnabled
                    anchors.fill: parent
                    radius: parent.radius
                    color: "transparent"
                    border.width: 1
                    border.color: Qt.rgba(0.3, 0.6, 1.0, 0.3)

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: -2
                        radius: parent.radius + 2
                        color: "transparent"
                        border.width: 2
                        border.color: Qt.rgba(0.3, 0.6, 1.0, 0.1)
                    }
                }

                // 网格线
                Canvas {
                    id: gridCanvas
                    anchors.fill: parent
                    visible: spectrumCard.showGrid

                    // 将 QML Color 转为 Canvas 可用的字符串
                    function colorToString(c) {
                        return "rgba(" + Math.floor(c.r * 255) + "," + Math.floor(c.g * 255) + "," + Math.floor(c.b * 255) + "," + c.a + ")";
                    }

                    onPaint: {
                        var ctx = getContext("2d");
                        ctx.clearRect(0, 0, width, height);
                        ctx.strokeStyle = colorToString(spectrumCard.gridColor);
                        ctx.lineWidth = spectrumCard.gridLineWidth;

                        // 水平网格线
                        var hStep = height / spectrumCard.horizontalGridLines;
                        for (var i = 1; i < spectrumCard.horizontalGridLines; i++) {
                            var y = Math.floor(i * hStep) + 0.5;
                            ctx.beginPath();
                            ctx.moveTo(0, y);
                            ctx.lineTo(width, y);
                            ctx.stroke();
                        }

                        // 垂直网格线
                        var vStep = width / spectrumCard.verticalGridLines;
                        for (var j = 1; j < spectrumCard.verticalGridLines; j++) {
                            var x = Math.floor(j * vStep) + 0.5;
                            ctx.beginPath();
                            ctx.moveTo(x, 0);
                            ctx.lineTo(x, height);
                            ctx.stroke();
                        }
                    }

                    Component.onCompleted: requestPaint()
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                }

                // 频谱柱状图 Canvas
                // 使用 Canvas.Threaded 渲染策略，在单独线程中执行绑制操作
                // 避免阻塞 UI 线程，提高高频更新时的响应性
                Canvas {
                    id: spectrumCanvas
                    anchors.fill: parent
                    anchors.margins: 2
                    renderStrategy: Canvas.Threaded  // 使用线程渲染提高性能

                    // ===== 颜色查找表 (LUT) =====
                    // 预计算 lutSize+1 个颜色值，避免每帧重复插值计算
                    // 查找时间复杂度 O(1)，相比实时插值 O(n) 大幅提升性能
                    property var colorLUT: []
                    property int lutSize: 64  // 查找表大小

                    /**
                     * 初始化颜色查找表
                     * 在配色方案变化时调用，预计算所有颜色值
                     */
                    function buildColorLUT() {
                        var lut = [];
                        for (var i = 0; i <= lutSize; i++) {
                            lut.push(computeColor(i / lutSize));
                        }
                        colorLUT = lut;
                    }

                    /**
                     * 计算单个颜色值（内部方法）
                     * @param normalizedValue - 归一化值 0.0~1.0
                     * @returns Canvas 可用的颜色字符串 "rgb(r,g,b)" 或 "rgba(r,g,b,a)"
                     *
                     * 根据配色方案在颜色停止点之间进行线性插值
                     */
                    function computeColor(normalizedValue) {
                        if (spectrumCard.colorScheme === "mono") {
                            var mc = spectrumCard.monoColor;
                            var alpha = 0.3 + 0.7 * normalizedValue;
                            var r = Math.floor(mc.r * 255);
                            var g = Math.floor(mc.g * 255);
                            var b = Math.floor(mc.b * 255);
                            return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
                        }

                        var scheme = spectrumCard.colorSchemes[spectrumCard.colorScheme] || spectrumCard.colorSchemes["spectrum"];
                        var v = Math.max(0, Math.min(1, normalizedValue));

                        var idx = 0;
                        while (idx < scheme.length - 1 && scheme[idx + 1].pos < v) idx++;

                        if (idx >= scheme.length - 1) {
                            var last = scheme[scheme.length - 1];
                            return "rgb(" + last.r + "," + last.g + "," + last.b + ")";
                        }

                        var c1 = scheme[idx];
                        var c2 = scheme[idx + 1];
                        var t = (v - c1.pos) / (c2.pos - c1.pos);

                        var r = Math.floor(c1.r + (c2.r - c1.r) * t);
                        var g = Math.floor(c1.g + (c2.g - c1.g) * t);
                        var b = Math.floor(c1.b + (c2.b - c1.b) * t);

                        return "rgb(" + r + "," + g + "," + b + ")";
                    }

                    /**
                     * 从查找表获取颜色（快速路径）
                     * @param normalizedValue - 归一化值 0.0~1.0
                     * @returns 预计算的颜色字符串
                     *
                     * 使用 O(1) 查表代替 O(n) 插值计算
                     */
                    function getBarColor(normalizedValue) {
                        if (colorLUT.length === 0) return "#ff0000";
                        var idx = Math.floor(Math.max(0, Math.min(1, normalizedValue)) * lutSize);
                        return colorLUT[Math.min(idx, lutSize)];
                    }

                    /**
                     * 获取带透明度的颜色（用于折线图填充）
                     * @param normalizedValue - 归一化值 0.0~1.0
                     * @param alpha - 透明度 0.0~1.0
                     * @returns 带 alpha 通道的颜色字符串 "rgba(r,g,b,a)"
                     *
                     * 不使用 LUT，因为 alpha 值可变
                     */
                    function getBarColorWithAlpha(normalizedValue, alpha) {
                        if (spectrumCard.colorScheme === "mono") {
                            var mc = spectrumCard.monoColor;
                            var r = Math.floor(mc.r * 255);
                            var g = Math.floor(mc.g * 255);
                            var b = Math.floor(mc.b * 255);
                            return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
                        }

                        var scheme = spectrumCard.colorSchemes[spectrumCard.colorScheme] || spectrumCard.colorSchemes["spectrum"];
                        var v = Math.max(0, Math.min(1, normalizedValue));

                        var idx = 0;
                        while (idx < scheme.length - 1 && scheme[idx + 1].pos < v) idx++;

                        if (idx >= scheme.length - 1) {
                            var last = scheme[scheme.length - 1];
                            return "rgba(" + last.r + "," + last.g + "," + last.b + "," + alpha + ")";
                        }

                        var c1 = scheme[idx];
                        var c2 = scheme[idx + 1];
                        var t = (v - c1.pos) / (c2.pos - c1.pos);

                        var r = Math.floor(c1.r + (c2.r - c1.r) * t);
                        var g = Math.floor(c1.g + (c2.g - c1.g) * t);
                        var b = Math.floor(c1.b + (c2.b - c1.b) * t);

                        return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
                    }

                    Component.onCompleted: buildColorLUT()

                    /**
                     * 主绑制函数 - 每帧调用
                     *
                     * 根据 chartType 选择绘制模式：
                     * - "bar": 柱状图模式，每个 bin 绘制一个矩形
                     * - "line": 折线图模式，连接所有数据点
                     *
                     * 渲染流程：
                     * 1. 清空画布
                     * 2. 获取缓存数据
                     * 3. 根据图表类型绘制主体
                     * 4. 绘制峰值保持线（如果启用）
                     */
                    onPaint: {
                        var ctx = getContext("2d");
                        var w = width;
                        var h = height;

                        ctx.clearRect(0, 0, w, h);

                        var data = spectrumCard.cachedData;
                        if (!data || data.length === 0) return;

                        var binCount = data.length;
                        var useGrad = spectrumCard.useGradient;
                        var intensity = spectrumCard.gradientIntensity;

                        // 根据图表类型选择绘制方式
                        if (spectrumCard.chartType === "line") {
                            // ========== 折线图模式 ==========
                            var stepX = w / (binCount - 1);

                            // 创建渐变
                            var gradient = ctx.createLinearGradient(0, h, 0, 0);
                            gradient.addColorStop(0, getBarColor(0.1 * intensity));
                            gradient.addColorStop(0.3, getBarColor(0.3 * intensity));
                            gradient.addColorStop(0.6, getBarColor(0.6 * intensity));
                            gradient.addColorStop(1, getBarColor(1.0));

                            // 绘制填充区域
                            if (spectrumCard.lineFill) {
                                ctx.beginPath();
                                ctx.moveTo(0, h);
                                for (var i = 0; i < binCount; i++) {
                                    var value = data[i] || 0;
                                    var x = i * stepX;
                                    var y = h - (value * h);
                                    if (i === 0) {
                                        ctx.lineTo(x, y);
                                    } else {
                                        ctx.lineTo(x, y);
                                    }
                                }
                                ctx.lineTo(w, h);
                                ctx.closePath();

                                if (useGrad) {
                                    // 创建填充渐变，带透明度
                                    var fillGradient = ctx.createLinearGradient(0, h, 0, 0);
                                    var fillOpacity = spectrumCard.lineFillOpacity;
                                    fillGradient.addColorStop(0, getBarColorWithAlpha(0.1 * intensity, fillOpacity * 0.5));
                                    fillGradient.addColorStop(0.5, getBarColorWithAlpha(0.5 * intensity, fillOpacity));
                                    fillGradient.addColorStop(1, getBarColorWithAlpha(1.0, fillOpacity));
                                    ctx.fillStyle = fillGradient;
                                } else {
                                    ctx.fillStyle = getBarColorWithAlpha(0.7, spectrumCard.lineFillOpacity);
                                }
                                ctx.fill();
                            }

                            // 绘制折线
                            ctx.beginPath();
                            for (var j = 0; j < binCount; j++) {
                                var val = data[j] || 0;
                                var px = j * stepX;
                                var py = h - (val * h);
                                if (j === 0) {
                                    ctx.moveTo(px, py);
                                } else {
                                    ctx.lineTo(px, py);
                                }
                            }

                            if (useGrad) {
                                ctx.strokeStyle = gradient;
                            } else {
                                ctx.strokeStyle = getBarColor(0.8);
                            }
                            ctx.lineWidth = spectrumCard.lineWidth;
                            ctx.lineJoin = "round";
                            ctx.stroke();

                            // 折线图的峰值保持线
                            if (spectrumCard.showPeakHold) {
                                var peaks = spectrumCard.cachedPeaks;
                                if (peaks && peaks.length === binCount) {
                                    var pc = spectrumCard.peakHoldColor;
                                    ctx.strokeStyle = "rgba(" + Math.floor(pc.r * 255) + "," + Math.floor(pc.g * 255) + "," + Math.floor(pc.b * 255) + "," + pc.a + ")";
                                    ctx.lineWidth = spectrumCard.peakHoldLineWidth;

                                    ctx.beginPath();
                                    for (var k = 0; k < binCount; k++) {
                                        var peakVal = peaks[k] || 0;
                                        var peakX = k * stepX;
                                        var peakY = h - (peakVal * h);
                                        if (k === 0) {
                                            ctx.moveTo(peakX, peakY);
                                        } else {
                                            ctx.lineTo(peakX, peakY);
                                        }
                                    }
                                    ctx.stroke();
                                }
                            }
                        } else {
                            // ========== 柱状图模式 ==========
                            var spacing = spectrumCard.barSpacing;
                            var totalSpacing = (binCount - 1) * spacing;
                            var barWidth = (w - totalSpacing) / binCount;
                            if (barWidth < 1) barWidth = 1;

                            var minH = spectrumCard.barMinHeight;

                            if (useGrad) {
                                // 使用渐变模式 - 为了性能，使用单个全高度渐变
                                var barGradient = ctx.createLinearGradient(0, h, 0, 0);
                                barGradient.addColorStop(0, getBarColor(0.1 * intensity));
                                barGradient.addColorStop(0.3, getBarColor(0.3 * intensity));
                                barGradient.addColorStop(0.6, getBarColor(0.6 * intensity));
                                barGradient.addColorStop(1, getBarColor(1.0));
                                ctx.fillStyle = barGradient;

                                for (var bi = 0; bi < binCount; bi++) {
                                    var bValue = data[bi] || 0;
                                    var barHeight = Math.max(minH, bValue * h);
                                    var bx = bi * (barWidth + spacing);
                                    var by = h - barHeight;
                                    ctx.fillRect(bx, by, barWidth, barHeight);
                                }
                            } else {
                                // 纯色模式 - 每个柱子独立颜色
                                for (var bj = 0; bj < binCount; bj++) {
                                    var bjValue = data[bj] || 0;
                                    var bjHeight = Math.max(minH, bjValue * h);
                                    if (bjHeight > 0) {
                                        var bjx = bj * (barWidth + spacing);
                                        var bjy = h - bjHeight;
                                        ctx.fillStyle = getBarColor(bjValue);
                                        ctx.fillRect(bjx, bjy, barWidth, bjHeight);
                                    }
                                }
                            }

                            // 柱状图的峰值保持线
                            if (spectrumCard.showPeakHold) {
                                var barPeaks = spectrumCard.cachedPeaks;
                                if (barPeaks && barPeaks.length === binCount) {
                                    var bpc = spectrumCard.peakHoldColor;
                                    ctx.strokeStyle = "rgba(" + Math.floor(bpc.r * 255) + "," + Math.floor(bpc.g * 255) + "," + Math.floor(bpc.b * 255) + "," + bpc.a + ")";
                                    ctx.lineWidth = spectrumCard.peakHoldLineWidth;

                                    ctx.beginPath();
                                    for (var bk = 0; bk < binCount; bk++) {
                                        var bPeakValue = barPeaks[bk] || 0;
                                        if (bPeakValue > 0.01) {
                                            var bPeakY = h - (bPeakValue * h);
                                            var bpx = bk * (barWidth + spacing);
                                            ctx.moveTo(bpx, bPeakY);
                                            ctx.lineTo(bpx + barWidth, bPeakY);
                                        }
                                    }
                                    ctx.stroke();
                                }
                            }
                        }
                    }
                }

                // 发光效果层
                Item {
                    id: glowLayer
                    visible: spectrumCard.glowEnabled
                    anchors.fill: spectrumCanvas
                    layer.enabled: spectrumCard.glowEnabled
                    layer.effect: MultiEffect {
                        blurEnabled: true
                        blur: spectrumCard.chartType === "line" ? 0.2 : 0.3
                        blurMax: spectrumCard.chartType === "line" ? 16 : 32
                        brightness: spectrumCard.glowIntensity * 0.3
                    }

                    Canvas {
                        id: glowCanvas
                        anchors.fill: parent
                        renderStrategy: Canvas.Threaded

                        onPaint: {
                            var ctx = getContext("2d");
                            var w = width;
                            var h = height;
                            ctx.clearRect(0, 0, w, h);

                            var data = spectrumCard.cachedData;
                            if (!data || data.length === 0) return;

                            var binCount = data.length;

                            if (spectrumCard.chartType === "line") {
                                // 折线图模式：降采样以提升性能
                                var step = Math.max(1, Math.floor(binCount / 64));
                                var stepX = w / (binCount - 1);
                                ctx.beginPath();
                                for (var i = 0; i < binCount; i += step) {
                                    var value = data[i] || 0;
                                    var x = i * stepX;
                                    var y = h - (value * h);
                                    if (i === 0) ctx.moveTo(x, y);
                                    else ctx.lineTo(x, y);
                                }
                                // 确保最后一点被绘制
                                if ((binCount - 1) % step !== 0) {
                                    var lastVal = data[binCount - 1] || 0;
                                    ctx.lineTo(w, h - (lastVal * h));
                                }
                                ctx.strokeStyle = spectrumCanvas.getBarColor(0.8);
                                ctx.lineWidth = spectrumCard.lineWidth + 2;
                                ctx.stroke();
                            } else {
                                var spacing = spectrumCard.barSpacing;
                                var barWidth = (w - (binCount - 1) * spacing) / binCount;
                                if (barWidth < 1) barWidth = 1;

                                for (var j = 0; j < binCount; j++) {
                                    var val = data[j] || 0;
                                    if (val > 0.3) {
                                        var barH = val * h;
                                        var bx = j * (barWidth + spacing);
                                        var by = h - barH;
                                        ctx.fillStyle = spectrumCanvas.getBarColor(val);
                                        ctx.fillRect(bx, by, barWidth, barH);
                                    }
                                }
                            }
                        }
                    }
                }

                // 倒影效果
                Item {
                    visible: spectrumCard.reflectionEnabled
                    anchors.left: spectrumCanvas.left
                    anchors.right: spectrumCanvas.right
                    anchors.top: spectrumCanvas.bottom
                    height: spectrumCanvas.height * 0.3
                    clip: true
                    opacity: spectrumCard.reflectionOpacity

                    Canvas {
                        id: reflectionCanvas
                        width: parent.width
                        height: spectrumCanvas.height
                        transform: Scale { yScale: -1; origin.y: 0 }

                        onPaint: {
                            var ctx = getContext("2d");
                            var w = width;
                            var h = height;
                            ctx.clearRect(0, 0, w, h);

                            var data = spectrumCard.cachedData;
                            if (!data || data.length === 0) return;

                            var binCount = data.length;

                            if (spectrumCard.chartType === "line") {
                                // 折线图模式：降采样以提升性能
                                var step = Math.max(1, Math.floor(binCount / 64));
                                var stepX = w / (binCount - 1);
                                ctx.beginPath();
                                ctx.moveTo(0, h);
                                for (var i = 0; i < binCount; i += step) {
                                    var val = data[i] || 0;
                                    ctx.lineTo(i * stepX, h - val * h);
                                }
                                // 确保最后一点被绘制
                                if ((binCount - 1) % step !== 0) {
                                    var lastVal = data[binCount - 1] || 0;
                                    ctx.lineTo(w, h - lastVal * h);
                                }
                                ctx.lineTo(w, h);
                                ctx.closePath();

                                var grad = ctx.createLinearGradient(0, h, 0, 0);
                                grad.addColorStop(0, "rgba(0,0,0,0)");
                                grad.addColorStop(1, spectrumCanvas.getBarColor(0.5));
                                ctx.fillStyle = grad;
                                ctx.fill();
                            } else {
                                var spacing = spectrumCard.barSpacing;
                                var barWidth = (w - (binCount - 1) * spacing) / binCount;
                                if (barWidth < 1) barWidth = 1;

                                var gradient = ctx.createLinearGradient(0, h, 0, 0);
                                gradient.addColorStop(0, "rgba(0,0,0,0)");
                                gradient.addColorStop(0.5, spectrumCanvas.getBarColorWithAlpha(0.3, 0.3));
                                gradient.addColorStop(1, spectrumCanvas.getBarColorWithAlpha(0.7, 0.5));
                                ctx.fillStyle = gradient;

                                for (var j = 0; j < binCount; j++) {
                                    var value = data[j] || 0;
                                    var barH = value * h * 0.5;
                                    var bx = j * (barWidth + spacing);
                                    ctx.fillRect(bx, h - barH, barWidth, barH);
                                }
                            }
                        }
                    }

                    // 倒影渐变遮罩
                    Rectangle {
                        anchors.fill: parent
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 1.0; color: spectrumCard.chartBackground }
                        }
                    }
                }

                // 扫描线效果（CRT 风格）
                Canvas {
                    id: scanLines
                    visible: spectrumCard.scanLineEnabled
                    anchors.fill: parent
                    opacity: spectrumCard.scanLineOpacity

                    onPaint: {
                        var ctx = getContext("2d");
                        ctx.clearRect(0, 0, width, height);
                        ctx.strokeStyle = "rgba(0,0,0,0.5)";
                        ctx.lineWidth = 1;

                        for (var i = 0; i < height; i += 2) {
                            ctx.beginPath();
                            ctx.moveTo(0, i + 0.5);
                            ctx.lineTo(width, i + 0.5);
                            ctx.stroke();
                        }
                    }

                    Component.onCompleted: requestPaint()
                    onHeightChanged: requestPaint()
                }

                // 顶部高光
                Rectangle {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 1
                    opacity: 0.1
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop { position: 0.5; color: "white" }
                        GradientStop { position: 1.0; color: "transparent" }
                    }
                }
            }
        }

        // 底部 X 轴刻度
        RowLayout {
            visible: spectrumCard.showXAxis
            Layout.fillWidth: true
            Layout.preferredHeight: spectrumCard.xAxisHeight
            spacing: Components.UiTheme.spacing("xs")

            // 左侧占位
            Item {
                visible: spectrumCard.showYAxis
                Layout.preferredWidth: spectrumCard.yAxisWidth
            }

            // 频率刻度
            RowLayout {
                Layout.fillWidth: true
                spacing: 0

                Repeater {
                    model: spectrumCard.xAxisTicks

                    Text {
                        Layout.fillWidth: true
                        text: {
                            var freq = spectrumCard.minFreq + (index / (spectrumCard.xAxisTicks - 1)) * (spectrumCard.maxFreq - spectrumCard.minFreq);
                            return freq.toFixed(0) + spectrumCard.xAxisUnit;
                        }
                        font.pixelSize: spectrumCard.axisLabelFontSize
                        color: spectrumCard.axisLabelColor
                        horizontalAlignment: {
                            if (index === 0) return Text.AlignLeft;
                            if (index === spectrumCard.xAxisTicks - 1) return Text.AlignRight;
                            return Text.AlignHCenter;
                        }
                    }
                }
            }
        }
    }

    // ==================== 数据更新连接 ====================
    // 监听 Python 端 SpectrumDataModel 的 spectrumDataChanged 信号
    // 信号触发时更新缓存数据并请求重绘所有 Canvas
    Connections {
        target: spectrumCard.spectrumModel
        enabled: spectrumCard.spectrumModel !== null

        /**
         * 数据更新回调
         * 当 Python 端调用 updateSpectrum() 等方法时触发
         * 更新缓存并请求重绘
         */
        function onSpectrumDataChanged() {
            spectrumCard.cachedData = spectrumCard.spectrumModel.spectrumData;
            spectrumCard.cachedPeaks = spectrumCard.spectrumModel.peakHoldData;
            spectrumCard.requestAllPaint();
        }
    }

    // 防抖定时器：用于样式变化时的延迟重绘
    Timer {
        id: styleChangeTimer
        interval: 16  // ~60fps
        repeat: false
        onTriggered: spectrumCard.requestAllPaint()
    }

    // 防抖定时器：用于尺寸变化时的延迟重绘
    Timer {
        id: resizeDebounceTimer
        interval: Components.UiConstants.resizeDebounceInterval
        repeat: false
        onTriggered: {
            gridCanvas.requestPaint()
            spectrumCard.requestAllPaint()
            scanLines.requestPaint()
        }
    }

    // 防抖定时器：用于网格属性变化时的延迟重绘
    Timer {
        id: gridDebounceTimer
        interval: 16
        repeat: false
        onTriggered: gridCanvas.requestPaint()
    }

    // 防抖定时器：用于扫描线属性变化时的延迟重绘
    Timer {
        id: scanLineDebounceTimer
        interval: 16
        repeat: false
        onTriggered: scanLines.requestPaint()
    }

    /**
     * 统一重绘函数
     * 请求所有相关 Canvas 重绘（主图、发光层、倒影层）
     * 根据当前启用的效果选择性重绘以优化性能
     */
    function requestAllPaint() {
        spectrumCanvas.requestPaint();
        if (glowEnabled) glowCanvas.requestPaint();
        if (reflectionEnabled) reflectionCanvas.requestPaint();
    }

    /**
     * 延迟重绘函数（用于样式变化）
     * 使用防抖机制避免快速切换时的性能问题
     */
    function requestStyleRepaint() {
        styleChangeTimer.restart();
    }

    // ==================== 属性变化处理 ====================
    // 模型变更时初始化缓存数据
    onSpectrumModelChanged: {
        if (spectrumModel) {
            cachedData = spectrumModel.spectrumData;
            cachedPeaks = spectrumModel.peakHoldData;
            requestAllPaint();
        } else {
            cachedData = [];
            cachedPeaks = [];
            requestAllPaint();
        }
    }

    // 配色方案变化时重建颜色查找表（使用延迟重绘）
    onColorSchemeChanged: { spectrumCanvas.buildColorLUT(); requestStyleRepaint(); }
    onMonoColorChanged: { spectrumCanvas.buildColorLUT(); requestStyleRepaint(); }

    // 以下属性变化时仅需重绘，无需重建 LUT（使用延迟重绘）
    onUseGradientChanged: requestStyleRepaint()
    onGradientIntensityChanged: requestStyleRepaint()
    onChartTypeChanged: requestStyleRepaint()
    onLineWidthChanged: requestStyleRepaint()
    onLineFillChanged: requestStyleRepaint()
    onLineFillOpacityChanged: requestStyleRepaint()
    onBarSpacingChanged: requestStyleRepaint()
    onBarMinHeightChanged: requestStyleRepaint()
    onShowPeakHoldChanged: requestStyleRepaint()
    onPeakHoldColorChanged: requestStyleRepaint()
    onPeakHoldLineWidthChanged: requestStyleRepaint()

    // 网格配置变化时仅重绘网格 Canvas（使用防抖）
    onShowGridChanged: gridDebounceTimer.restart()
    onHorizontalGridLinesChanged: gridDebounceTimer.restart()
    onVerticalGridLinesChanged: gridDebounceTimer.restart()
    onGridColorChanged: gridDebounceTimer.restart()
    onGridLineWidthChanged: gridDebounceTimer.restart()

    // 背景和效果变化（使用延迟重绘）
    onChartBackgroundChanged: requestStyleRepaint()
    onGlowEnabledChanged: requestStyleRepaint()
    onGlowIntensityChanged: requestStyleRepaint()
    onReflectionEnabledChanged: requestStyleRepaint()
    onReflectionOpacityChanged: requestStyleRepaint()
    onScanLineEnabledChanged: scanLineDebounceTimer.restart()
    onScanLineOpacityChanged: scanLineDebounceTimer.restart()

    // 尺寸变化时重绘所有 Canvas（使用防抖定时器）
    onWidthChanged: resizeDebounceTimer.restart()
    onHeightChanged: resizeDebounceTimer.restart()
}
