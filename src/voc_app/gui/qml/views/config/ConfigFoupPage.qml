import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components"
import "../../components" as Components

Item {
    id: root

    property real scaleFactor: Components.UiTheme.controlScale
    property var foupInfo: ({
        syncTime: Qt.formatDateTime(new Date(), "yyyy-MM-dd hh:mm:ss"),
        acquisitionStatus: "采集中"
    })
    readonly property int foupChartIndex: 2

    function chartEntry(rowIndex, fallbackTitle) {
        const fallback = {
            title: fallbackTitle || "",
            seriesModel: null,
            xColumn: 0,
            yColumn: 1
        };
        if (typeof chartListModel === "undefined" || !chartListModel || typeof chartListModel.get !== "function")
            return fallback;
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

    function displayValue(value) {
        if (value === null || typeof value === "undefined" || value === "")
            return "--";
        return value;
    }

    Rectangle {
        anchors.fill: parent
        radius: Components.UiTheme.radius(18)
        color: Components.UiTheme.color("panel")
        border.color: Components.UiTheme.color("outline")

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Components.UiTheme.spacing("xl")
            spacing: Components.UiTheme.spacing("lg")

            Text {
                text: "FOUP 配置"
                font.pixelSize: Components.UiTheme.fontSize("title")
                font.bold: true
                color: Components.UiTheme.color("textPrimary")
            }

            Text {
                text: "当前时间及采集通道状态"
                color: Components.UiTheme.color("textSecondary")
                font.pixelSize: Components.UiTheme.fontSize("body")
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: Components.UiTheme.spacing("md")
                columnSpacing: Components.UiTheme.spacing("lg")

                Text {
                    text: "同步时间"
                    color: Components.UiTheme.color("textSecondary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }

                Text {
                    text: root.displayValue(root.foupInfo.syncTime)
                    font.pixelSize: Components.UiTheme.fontSize("subtitle")
                    font.bold: true
                    color: Components.UiTheme.color("textPrimary")
                }

                Text {
                    text: "采集状态"
                    color: Components.UiTheme.color("textSecondary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }

                RowLayout {
                    spacing: Components.UiTheme.spacing("sm")

                    Rectangle {
                        width: Components.UiTheme.spacing("lg")
                        height: Components.UiTheme.spacing("lg")
                        radius: Components.UiTheme.radius("pill")
                        color: (typeof foupAcquisition !== "undefined" && foupAcquisition && foupAcquisition.running)
                            ? Components.UiTheme.color("accentSuccess")
                            : Components.UiTheme.color("accentAlarm")
                    }

                    Text {
                        text: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                            ? foupAcquisition.statusMessage
                            : root.displayValue(root.foupInfo.acquisitionStatus)
                        font.pixelSize: Components.UiTheme.fontSize("subtitle")
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }
                }
            }

            // 动态图表容器（固定两列布局）
            GridLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: 2
                rowSpacing: Components.UiTheme.spacing("md")
                columnSpacing: Components.UiTheme.spacing("md")

                // 动态生成图表
                Repeater {
                    id: chartRepeater
                    model: {
                        // 根据foupAcquisition.channelCount动态生成图表列表
                        // 至少显示1个图表，防止采集前布局空白
                        if (typeof foupAcquisition === "undefined" || !foupAcquisition) {
                            return [{ title: "FOUP 通道 1", index: root.foupChartIndex, channelIndex: 0 }]
                        }
                        const count = Math.max(1, foupAcquisition.channelCount)
                        const charts = []
                        for (let i = 0; i < count; i++) {
                            charts.push({
                                title: "FOUP 通道 " + (i + 1),
                                index: root.foupChartIndex + i,
                                channelIndex: i
                            })
                        }
                        return charts
                    }

                    delegate: Components.ChartCard {
                        id: chartCard
                        // 单通道时占满两列，多通道时每个占一列
                        Layout.columnSpan: (chartRepeater.count === 1) ? 2 : 1
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: Components.UiTheme.controlHeight(220)
                        Layout.minimumHeight: 180
                        radius: Components.UiTheme.radius(18)
                        color: Components.UiTheme.color("panel")
                        border.color: Components.UiTheme.color("outline")

                        readonly property var config: root.chartEntry(modelData.index, modelData.title)
                        readonly property int channelIdx: (typeof modelData.channelIndex === "number") ? modelData.channelIndex : 0

                        seriesModel: config.seriesModel
                        xColumn: config.xColumn
                        yColumn: config.yColumn
                        showLimits: true
                        scaleFactor: root.scaleFactor

                        // 从后端获取通道配置
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

                        Text {
                            visible: !seriesModel
                            anchors.centerIn: parent
                            text: "点击开始采集后显示实时曲线"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }

                        // 监听后端配置变更信号
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
                                }
                            }
                            function onChannelValuesChanged() {
                                chartCard.currentValue = foupAcquisition.getChannelValue(chartCard.channelIdx)
                            }
                        }
                    }
                }

                // 状态信息（跨两列显示）
                Text {
                    Layout.columnSpan: 2
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
