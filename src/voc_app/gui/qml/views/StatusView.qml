import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../components"
import "../components" as Components

Rectangle {
    id: statusRoot
    color: Components.UiTheme.color("background")

    // 外部写入当前子页面标识（Loadport / FOUP）
    property string currentSubPage: "loadport"
    property real scaleFactor: Components.UiTheme.controlScale
    property url loadportImageSource: Qt.resolvedUrl("../../resources/loadport_.png")
    property url foupImageSource: Qt.resolvedUrl("../../resources/foup_.png")

    // 频谱模型引用（避免与组件属性命名冲突）
    readonly property var globalSpectrumModel: (typeof spectrumModel !== "undefined") ? spectrumModel : null
    readonly property var globalSpectrumSimulator: (typeof spectrumSimulator !== "undefined") ? spectrumSimulator : null

    // Loadport 子页面使用的实时曲线配置
    readonly property var loadportCharts: [
        { title: "电压", currentValue: "3.8 V", index: 0 },
        { title: "温度", currentValue: "26 ℃", index: 1 }
    ]

    // FOUP 子页面实时曲线配置
    // FOUP 曲线起始索引（chartListModel 中预分配）
    readonly property int foupChartIndex: 2

    // 便捷函数，按索引读取曲线对象，缺省时返回占位配置
    function chartEntry(rowIndex, fallbackTitle) {
        const fallback = {
            title: fallbackTitle || "",
            seriesModel: null,
            xColumn: 0,
            yColumn: 1
        };
        if (typeof chartListModel === "undefined" || !chartListModel || typeof chartListModel.get !== "function")
            return fallback;
        // 获取指定行的曲线配置
        const entry = chartListModel.get(rowIndex);
        if (!entry || Object.keys(entry).length === 0)
            return fallback;
        return {
            title: entry.title || fallback.title,
            seriesModel: entry.seriesModel || null,
            xColumn: typeof entry.xColumn === "number" ? entry.xColumn : 0,
            yColumn: typeof entry.yColumn === "number" ? entry.yColumn : 1
        };
    }

    Loader {
        anchors.fill: parent
        sourceComponent: {
            if (currentSubPage === "foup") return foupComponent
            if (currentSubPage === "spectrum") return spectrumComponent
            return loadportComponent
        }
    }

    Component {
        id: loadportComponent

        RowLayout {
            anchors.fill: parent
            anchors.margins: Components.UiTheme.spacing("xl")
            spacing: Components.UiTheme.spacing("xl")

            Rectangle {
                Layout.preferredWidth: Components.UiTheme.controlWidth(320)
                Layout.maximumWidth: Components.UiTheme.controlWidth(360)
                Layout.minimumWidth: Components.UiTheme.controlWidth(260)
                Layout.fillHeight: true
                radius: Components.UiTheme.radius(20)
                color: Components.UiTheme.color("panel")
                border.color: Components.UiTheme.color("outline")

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Components.UiTheme.spacing("lg")
                    spacing: Components.UiTheme.spacing("md")

                    Text {
                        text: "Loadport 模块"
                        font.pixelSize: Components.UiTheme.fontSize(24)
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    Text {
                        text: "状态：TODO"
                        color: Components.UiTheme.color("textSecondary")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Components.UiTheme.radius(18)
                        color: Components.UiTheme.color("surface")
                        border.color: Components.UiTheme.color("outlineStrong")

                        Item {
                            anchors.fill: parent
                            anchors.margins: Components.UiTheme.spacing("md")

                            Image {
                                id: loadportImage
                                anchors.centerIn: parent
                                source: statusRoot.loadportImageSource
                                smooth: true
                                asynchronous: true
                                fillMode: Image.PreserveAspectFit
                                property real aspectRatio: implicitHeight > 0 ? implicitWidth / implicitHeight : 1
                                width: {
                                    const availW = parent.width;
                                    const availH = parent.height;
                                    const ratio = aspectRatio > 0 ? aspectRatio : 1;
                                    return Math.min(availW, availH * ratio);
                                }
                                height: width / Math.max(0.0001, aspectRatio)
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Components.UiTheme.spacing("xl")

                Repeater {
                    model: statusRoot.loadportCharts

                    delegate: ChartCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: Components.UiTheme.controlHeight(220)
                        radius: Components.UiTheme.radius(18)
                        color: Components.UiTheme.color("panel")
                        border.color: Components.UiTheme.color("outline")
                        chartTitle: ""
                        readonly property var config: statusRoot.chartEntry(modelData.index, modelData.title)
                        seriesModel: config.seriesModel
                        xColumn: config.xColumn
                        yColumn: config.yColumn
                        scaleFactor: statusRoot.scaleFactor

                        Column {
                            z: 2
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.margins: Components.UiTheme.spacing("lg")
                            spacing: Components.UiTheme.spacing("sm")

                            Text {
                                text: modelData.title + "实时曲线"
                                font.pixelSize: Components.UiTheme.fontSize("title")
                                font.bold: true
                                color: Components.UiTheme.color("textPrimary")
                            }

                            // Text {
                            //     text: "当前值：" + modelData.currentValue
                            //     font.pixelSize: Components.UiTheme.fontSize("body")
                            //     color: Components.UiTheme.color("textSecondary")
                            // }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: foupComponent

        RowLayout {
            anchors.fill: parent
            anchors.margins: Components.UiTheme.spacing("xl")
            spacing: Components.UiTheme.spacing("xl")

            Rectangle {
                Layout.preferredWidth: Components.UiTheme.controlWidth(320)
                Layout.maximumWidth: Components.UiTheme.controlWidth(360)
                Layout.minimumWidth: Components.UiTheme.controlWidth(260)
                Layout.fillHeight: true
                radius: Components.UiTheme.radius(20)
                color: Components.UiTheme.color("panel")
                border.color: Components.UiTheme.color("outline")

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Components.UiTheme.spacing("lg")
                    spacing: Components.UiTheme.spacing("md")

                    Text {
                        text: "FOUP 模块"
                        font.pixelSize: Components.UiTheme.fontSize(24)
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    Text {
                        text: "保持稳定的采集状态"
                        color: Components.UiTheme.color("textSecondary")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Components.UiTheme.radius(18)
                        color: Components.UiTheme.color("surface")
                        border.color: Components.UiTheme.color("outlineStrong")

                        Item {
                            anchors.fill: parent
                            anchors.margins: Components.UiTheme.spacing("md")

                            Image {
                                id: foupImage
                                anchors.centerIn: parent
                                source: statusRoot.foupImageSource
                                smooth: true
                                asynchronous: true
                                fillMode: Image.PreserveAspectFit
                                property real aspectRatio: implicitHeight > 0 ? implicitWidth / implicitHeight : 1
                                width: {
                                    const availW = parent.width;
                                    const availH = parent.height;
                                    const ratio = aspectRatio > 0 ? aspectRatio : 1;
                                    return Math.min(availW, availH * ratio);
                                }
                                height: width / Math.max(0.0001, aspectRatio)
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Components.UiTheme.spacing("lg")

                Text {
                    text: "FOUP 实时曲线"
                    font.pixelSize: Components.UiTheme.fontSize("title")
                    font.bold: true
                    color: Components.UiTheme.color("textPrimary")
                }

                ScrollView {
                    id: chartScrollView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: availableWidth

                    ColumnLayout {
                        id: chartContainer
                        width: parent.width
                        spacing: Components.UiTheme.spacing("lg")

                        property var charts: {
                            if (typeof foupAcquisition === "undefined" || !foupAcquisition) {
                                return [{ title: "FOUP 通道 1", index: statusRoot.foupChartIndex, channelIndex: 0 }]
                            }
                            const count = Math.max(1, foupAcquisition.channelCount)
                            const list = []
                            for (let i = 0; i < count; i++) {
                                list.push({
                                    title: "FOUP 通道 " + (i + 1),
                                    index: statusRoot.foupChartIndex + i,
                                    channelIndex: i
                                })
                            }
                            return list
                        }
                        readonly property int chartCount: charts.length
                        readonly property real baseHeight: Math.max(Components.UiTheme.controlHeight(480), chartScrollView.height)

                        function isWideCard(idx) {
                            if (chartCount === 1)
                                return true
                            return (chartCount % 2 === 1) && idx === 0
                        }

                        function cardHeight(idx) {
                            const base = baseHeight
                            if (chartCount === 1)
                                return base
                            if (chartCount === 2)
                                return base
                            return base * 0.5
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            rowSpacing: Components.UiTheme.spacing("md")
                            columnSpacing: Components.UiTheme.spacing("md")

                        Repeater {
                            model: chartContainer.charts
                            delegate: Components.ChartCard {
                                id: chartCard
                                readonly property bool spanTwoColumns: chartContainer.isWideCard(index)
                                readonly property real preferredCardHeight: chartContainer.cardHeight(index)

                                Layout.fillWidth: true
                                Layout.columnSpan: spanTwoColumns ? 2 : 1
                                    Layout.preferredHeight: preferredCardHeight
                                    Layout.minimumHeight: preferredCardHeight * 0.8
                                    radius: Components.UiTheme.radius(18)
                                    color: Components.UiTheme.color("panel")
                                    border.color: Components.UiTheme.color("outline")

                                    readonly property var config: statusRoot.chartEntry(modelData.index, modelData.title)
                                    readonly property int channelIdx: (typeof modelData.channelIndex === "number") ? modelData.channelIndex : 0

                                    seriesModel: config.seriesModel
                                    xColumn: config.xColumn
                                    yColumn: config.yColumn
                                    showLimits: true
                                    scaleFactor: statusRoot.scaleFactor

                                    chartTitle: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getChannelTitle(channelIdx)
                                        : modelData.title
                                    yAxisUnit: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getUnit(channelIdx)
                                        : ""
                                    currentValue: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getChannelValue(channelIdx)
                                        : Number.NaN
                                    oocLimitValue: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getOocUpper(channelIdx)
                                        : 80
                                    oocLowerLimitValue: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getOocLower(channelIdx)
                                        : 20
                                    oosLimitValue: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getOosUpper(channelIdx)
                                        : 90
                                    oosLowerLimitValue: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getOosLower(channelIdx)
                                        : 10
                                    targetValue: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getTarget(channelIdx)
                                        : 50
                                    showOocUpper: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getShowOocUpper(channelIdx)
                                        : true
                                    showOocLower: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getShowOocLower(channelIdx)
                                        : true
                                    showOosUpper: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getShowOosUpper(channelIdx)
                                        : true
                                    showOosLower: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getShowOosLower(channelIdx)
                                        : true
                                    showTarget: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                        ? foupAcquisition.getShowTarget(channelIdx)
                                        : true

                                    Text {
                                        visible: !seriesModel
                                        anchors.centerIn: parent
                                        text: "点击开始采集后显示实时曲线"
                                        color: Components.UiTheme.color("textSecondary")
                                        font.pixelSize: Components.UiTheme.fontSize("body")
                                    }

                                    Connections {
                                        target: (typeof foupAcquisition !== "undefined") ? foupAcquisition : null
                                        enabled: typeof foupAcquisition !== "undefined" && foupAcquisition
                                        function onChannelConfigChanged(idx) {
                                            if (idx === chartCard.channelIdx) {
                                                chartCard.chartTitle = foupAcquisition.getChannelTitle(chartCard.channelIdx)
                                                chartCard.yAxisUnit = foupAcquisition.getUnit(chartCard.channelIdx)
                                                chartCard.oocLimitValue = foupAcquisition.getOocUpper(chartCard.channelIdx)
                                                chartCard.oocLowerLimitValue = foupAcquisition.getOocLower(chartCard.channelIdx)
                                                chartCard.oosLimitValue = foupAcquisition.getOosUpper(chartCard.channelIdx)
                                                chartCard.oosLowerLimitValue = foupAcquisition.getOosLower(chartCard.channelIdx)
                                                chartCard.targetValue = foupAcquisition.getTarget(chartCard.channelIdx)
                                                chartCard.showOocUpper = foupAcquisition.getShowOocUpper(chartCard.channelIdx)
                                                chartCard.showOocLower = foupAcquisition.getShowOocLower(chartCard.channelIdx)
                                                chartCard.showOosUpper = foupAcquisition.getShowOosUpper(chartCard.channelIdx)
                                                chartCard.showOosLower = foupAcquisition.getShowOosLower(chartCard.channelIdx)
                                                chartCard.showTarget = foupAcquisition.getShowTarget(chartCard.channelIdx)
                                            }
                                        }
                                        function onChannelValuesChanged() {
                                            chartCard.currentValue = foupAcquisition.getChannelValue(chartCard.channelIdx)
                                        }
                                    }
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: {
                                if (typeof foupAcquisition === "undefined" || !foupAcquisition) {
                                    return "通道数量: 1"
                                }
                                var serverInfo = foupAcquisition.serverTypeDisplayName || "未知"
                                var channelInfo = "通道: " + foupAcquisition.channelCount
                                return serverInfo + " | " + channelInfo
                            }
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }
                    }
                }
            }
        }
    }

    Component {
        id: spectrumComponent

        RowLayout {
            anchors.fill: parent
            anchors.margins: Components.UiTheme.spacing("xl")
            spacing: Components.UiTheme.spacing("xl")

            // 左侧控制面板
            Rectangle {
                Layout.preferredWidth: Components.UiTheme.controlWidth(280)
                Layout.maximumWidth: Components.UiTheme.controlWidth(320)
                Layout.minimumWidth: Components.UiTheme.controlWidth(240)
                Layout.fillHeight: true
                radius: Components.UiTheme.radius(20)
                color: Components.UiTheme.color("panel")
                border.color: Components.UiTheme.color("outline")

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Components.UiTheme.spacing("lg")
                    spacing: Components.UiTheme.spacing("md")

                    Text {
                        text: "频谱分析"
                        font.pixelSize: Components.UiTheme.fontSize(24)
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    Text {
                        text: "实时频谱可视化"
                        color: Components.UiTheme.color("textSecondary")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Components.UiTheme.color("outline")
                    }

                    // 模拟器控制
                    Text {
                        text: "模拟器控制"
                        font.pixelSize: Components.UiTheme.fontSize("subtitle")
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Components.UiTheme.spacing("sm")

                        Button {
                            text: (statusRoot.globalSpectrumSimulator && statusRoot.globalSpectrumSimulator.running) ? "停止" : "启动"
                            Layout.fillWidth: true
                            onClicked: {
                                if (statusRoot.globalSpectrumSimulator) {
                                    if (statusRoot.globalSpectrumSimulator.running) {
                                        statusRoot.globalSpectrumSimulator.stop()
                                    } else {
                                        statusRoot.globalSpectrumSimulator.start()
                                    }
                                }
                            }
                        }

                        Button {
                            text: "清空"
                            Layout.fillWidth: true
                            onClicked: {
                                if (statusRoot.globalSpectrumModel) {
                                    statusRoot.globalSpectrumModel.clear()
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Components.UiTheme.color("outline")
                    }

                    // 图表类型选择
                    Text {
                        text: "图表类型"
                        font.pixelSize: Components.UiTheme.fontSize("subtitle")
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Components.UiTheme.spacing("sm")

                        Button {
                            text: "柱状图"
                            Layout.fillWidth: true
                            highlighted: spectrumChartView.chartType === "bar"
                            onClicked: spectrumChartView.chartType = "bar"
                        }

                        Button {
                            text: "折线图"
                            Layout.fillWidth: true
                            highlighted: spectrumChartView.chartType === "line"
                            onClicked: spectrumChartView.chartType = "line"
                        }
                    }

                    // 配色方案选择
                    Text {
                        text: "配色方案"
                        font.pixelSize: Components.UiTheme.fontSize("subtitle")
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3
                        rowSpacing: Components.UiTheme.spacing("xs")
                        columnSpacing: Components.UiTheme.spacing("xs")

                        Repeater {
                            model: ["spectrum", "green", "blue", "fire", "purple", "ocean"]
                            delegate: Button {
                                text: modelData
                                Layout.fillWidth: true
                                highlighted: spectrumChartView.colorScheme === modelData
                                onClicked: spectrumChartView.colorScheme = modelData
                            }
                        }
                    }

                    // 视觉效果开关
                    Text {
                        text: "视觉效果"
                        font.pixelSize: Components.UiTheme.fontSize("subtitle")
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: Components.UiTheme.spacing("xs")

                        CheckBox {
                            text: "发光效果"
                            checked: spectrumChartView.glowEnabled
                            onCheckedChanged: spectrumChartView.glowEnabled = checked
                        }

                        CheckBox {
                            text: "倒影效果"
                            checked: spectrumChartView.reflectionEnabled
                            onCheckedChanged: spectrumChartView.reflectionEnabled = checked
                        }

                        CheckBox {
                            text: "扫描线"
                            checked: spectrumChartView.scanLineEnabled
                            onCheckedChanged: spectrumChartView.scanLineEnabled = checked
                        }

                        CheckBox {
                            text: "峰值保持"
                            checked: spectrumChartView.showPeakHold
                            onCheckedChanged: spectrumChartView.showPeakHold = checked
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // 右侧频谱图
            Components.SpectrumChart {
                id: spectrumChartView
                Layout.fillWidth: true
                Layout.fillHeight: true
                spectrumModel: statusRoot.globalSpectrumModel
                chartTitle: "实时频谱分析"
                showTitle: true
                chartType: "bar"
                colorScheme: "spectrum"
                glowEnabled: true
                reflectionEnabled: true
                scanLineEnabled: false
                showPeakHold: true
                minDb: -80
                maxDb: 0
                minFreq: 0
                maxFreq: 22
                xAxisUnit: "kHz"
            }
        }
    }
}
