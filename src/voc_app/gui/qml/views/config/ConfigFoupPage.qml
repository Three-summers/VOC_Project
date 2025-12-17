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

    // 缓存 foupAcquisition 全局对象引用，避免重复 typeof 检查
    readonly property var _foupAcq: (typeof foupAcquisition !== "undefined") ? foupAcquisition : null
    readonly property bool _hasFoupAcq: _foupAcq !== null

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
                        color: (root._hasFoupAcq && root._foupAcq.running)
                            ? Components.UiTheme.color("accentSuccess")
                            : Components.UiTheme.color("accentAlarm")
                    }

                    Text {
                        text: root._hasFoupAcq
                            ? root._foupAcq.statusMessage
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
                    text: root._hasFoupAcq
                          ? (root._foupAcq.operationMode === "normal" ? "正常模式（下载）" : "测试模式（实时）")
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
                    text: root._hasFoupAcq
                          ? root._foupAcq.serverTypeDisplayName
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
                    text: (root._hasFoupAcq && root._foupAcq.serverVersion.length > 0)
                          ? root._foupAcq.serverVersion
                          : "--"
                    font.pixelSize: Components.UiTheme.fontSize("subtitle")
                    font.bold: true
                    color: Components.UiTheme.color("textPrimary")
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Components.UiTheme.radius(14)
                color: Components.UiTheme.color("surface")
                border.color: Components.UiTheme.color("outlineStrong")

                Text {
                    anchors.centerIn: parent
                    text: "实时图表请在“状态 - FOUP”页查看"
                    color: Components.UiTheme.color("textSecondary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }
            }
        }
    }
}
