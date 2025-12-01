import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components" as Components

Item {
    id: rootItem
    anchors.fill: parent

    // Properties and functions inherited from ConfigView
    property var foupInfo: ({
        syncTime: Qt.formatDateTime(new Date(), "yyyy-MM-dd hh:mm:ss"),
        acquisitionStatus: "采集中"
    })
    property real scaleFactor: Components.UiTheme.controlScale
    property int foupChartIndex: 2

    // This function and chartListModel are likely part of ConfigView's context
    // and need to be passed down.
    // For now, I will assume `chartListModel` is available in the context of the calling `ConfigView`
    // and `chartEntry` also needs to be passed down from `ConfigView`.
    property var chartListModel // To be passed from ConfigView
    property var chartEntry // To be passed from ConfigView
    property var foupAcquisition // To be passed from ConfigView

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
                    text: displayValue(foupInfo.syncTime) // Use local property
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
                        : displayValue(foupInfo.acquisitionStatus) // Use local property
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
                        if (typeof foupAcquisition === "undefined" || !foupAcquisition) {
                            return [{ title: "FOUP 通道 1", index: rootItem.foupChartIndex }] // Use rootItem
                        }
                        const count = foupAcquisition.channelCount
                        const charts = []
                        for (let i = 0; i < count; i++) {
                            charts.push({
                                title: "FOUP 通道 " + (i + 1),
                                index: rootItem.foupChartIndex + i, // Use rootItem
                                channelIndex: i
                            })
                        }
                        return charts
                    }

                    delegate: Components.ChartCard {
                        // 单通道时占满两列，多通道时每个占一列
                        Layout.columnSpan: (chartRepeater.count === 1) ? 2 : 1
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: Components.UiTheme.controlHeight(220)
                        Layout.minimumHeight: 180
                        radius: Components.UiTheme.radius(18)
                        color: Components.UiTheme.color("panel")
                        border.color: Components.UiTheme.color("outline")

                        // 使用 readonly property 缓存配置，确保稳定的属性绑定
                        readonly property var config: rootItem.chartEntry(modelData.index, modelData.title) // Use rootItem and passed chartEntry
                        seriesModel: config.seriesModel
                        xColumn: config.xColumn
                        yColumn: config.yColumn

                        scaleFactor: rootItem.scaleFactor // Use rootItem

                        Text {
                            visible: !seriesModel
                            anchors.centerIn: parent
                            text: "点击开始采集后显示实时曲线"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }
                    }
                }

                // 状态信息（跨两列显示）
                Text {
                    Layout.columnSpan: 2
                    text: (typeof foupAcquisition !== "undefined" && foupAcquisition && !isNaN(foupAcquisition.lastValue))
                    ? "通道数量: " + foupAcquisition.channelCount + " | 当前值: " + foupAcquisition.lastValue.toFixed(2)
                    : "通道数量: " + ((typeof foupAcquisition !== "undefined" && foupAcquisition) ? foupAcquisition.channelCount : 1) + " | 当前值: --"
                    color: Components.UiTheme.color("textSecondary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }
            }
        }
    }
}
