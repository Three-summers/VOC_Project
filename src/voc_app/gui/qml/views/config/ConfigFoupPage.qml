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

                Text {
                    text: "采集模式"
                    color: Components.UiTheme.color("textSecondary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }

                Text {
                    text: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                          ? (foupAcquisition.operationMode === "normal" ? "正常模式（下载）" : "测试模式（实时）")
                          : "--"
                    font.pixelSize: Components.UiTheme.fontSize("subtitle")
                    font.bold: true
                    color: Components.UiTheme.color("textPrimary")
                }

                Text {
                    text: "服务器类型"
                    color: Components.UiTheme.color("textSecondary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }

                Text {
                    text: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                          ? foupAcquisition.serverTypeDisplayName
                          : "未知"
                    font.pixelSize: Components.UiTheme.fontSize("subtitle")
                    font.bold: true
                    color: Components.UiTheme.color("textPrimary")
                }

                Text {
                    text: "版本号"
                    color: Components.UiTheme.color("textSecondary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }

                Text {
                    text: (typeof foupAcquisition !== "undefined" && foupAcquisition && foupAcquisition.serverVersion.length > 0)
                          ? foupAcquisition.serverVersion
                          : "--"
                    font.pixelSize: Components.UiTheme.fontSize("subtitle")
                    font.bold: true
                    color: Components.UiTheme.color("textPrimary")
                }
            }

            // 动态图表容器：根据数量自适应两列，超出部分滚动展示
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
                            return [{ title: "FOUP 通道 1", index: root.foupChartIndex, channelIndex: 0 }]
                        }
                        const count = Math.max(1, foupAcquisition.channelCount)
                        const list = []
                        for (let i = 0; i < count; i++) {
                            list.push({
                                title: "FOUP 通道 " + (i + 1),
                                index: root.foupChartIndex + i,
                                channelIndex: i
                            })
                        }
                        return list
                    }
                    readonly property int chartCount: charts.length
                    readonly property real baseHeight: Math.max(Components.UiTheme.controlHeight(480), chartScrollView.height)

                    // 奇数数量时首张跨两列，其余按两列排布
                    function isWideCard(idx) {
                        if (chartCount === 1)
                            return true
                        return (chartCount % 2 === 1) && idx === 0
                    }

                    // 高度规则：单张全高；两张并列全高；三张及以上采用半高行，奇数首张仅跨两列占一行高度
                    function cardHeight(idx) {
                        const base = baseHeight
                        if (chartCount === 1)
                            return base
                        if (chartCount === 2)
                            return base
                        // 3 张及以上：每行半高，首张虽跨两列但仅占一行高度
                        return base * 0.5
                    }

                    GridLayout {
                        id: chartGrid
                        Layout.fillWidth: true
                        columns: 2
                        rowSpacing: Components.UiTheme.spacing("md")
                        columnSpacing: Components.UiTheme.spacing("md")

                        Repeater {
                            model: chartContainer.charts
                            delegate: Components.ChartCard {
                                id: chartCard
                                readonly property int totalCount: chartContainer.chartCount
                                readonly property bool spanTwoColumns: chartContainer.isWideCard(index)
                                readonly property real preferredCardHeight: chartContainer.cardHeight(index)

                                Layout.fillWidth: true
                                Layout.columnSpan: spanTwoColumns ? 2 : 1
                                Layout.preferredHeight: preferredCardHeight
                                Layout.minimumHeight: preferredCardHeight * 0.8
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

                    // 状态信息（单列展示）
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
