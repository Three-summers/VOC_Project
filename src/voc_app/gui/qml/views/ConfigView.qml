import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components" as Components

Rectangle {
    id: configView
    color: Components.UiTheme.color("background")

    property string currentSubPage: "loadport"
    property real scaleFactor: Components.UiTheme.controlScale
    property var loadportInfo: ({
        ipAddress: "192.168.0.100",
        deviceTime: Qt.formatDateTime(new Date(), "yyyy-MM-dd hh:mm:ss")
    })
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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Components.UiTheme.spacing("xl")
        spacing: Components.UiTheme.spacing("lg")

        Text {
            text: "配置页面"
            font.bold: true
            font.pixelSize: Components.UiTheme.fontSize("title")
            color: Components.UiTheme.color("textPrimary")
        }

        Text {
            text: "通过子页面查看并设置 Loadport 与 FOUP 的基础运行参数。"
            wrapMode: Text.Wrap
            color: Components.UiTheme.color("textSecondary")
            font.pixelSize: Components.UiTheme.fontSize("body")
        }

        Loader {
            id: contentLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceComponent: currentSubPage === "foup" ? foupComponent : loadportComponent
        }
    }

    Component {
        id: loadportComponent

        Item {
            anchors.fill: parent

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
                        text: "Loadport 配置"
                        font.pixelSize: Components.UiTheme.fontSize("title")
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    Text {
                        text: "当前通信参数"
                        color: Components.UiTheme.color("textSecondary")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        rowSpacing: Components.UiTheme.spacing("md")
                        columnSpacing: Components.UiTheme.spacing("lg")

                        Text {
                            text: "IP 地址"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }

                        Text {
                            text: configView.displayValue(configView.loadportInfo.ipAddress)
                            font.pixelSize: Components.UiTheme.fontSize("subtitle")
                            font.bold: true
                            color: Components.UiTheme.color("textPrimary")
                        }

                        Text {
                            text: "设备时间"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }

                        Text {
                            text: configView.displayValue(configView.loadportInfo.deviceTime)
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
                            text: "待接入实时 loadport 数据"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }
                    }
                }
            }
        }
    }

    Component {
        id: foupComponent

        Item {
            anchors.fill: parent

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
                            text: configView.displayValue(configView.foupInfo.syncTime)
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
                                : configView.displayValue(configView.foupInfo.acquisitionStatus)
                                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                                font.bold: true
                                color: Components.UiTheme.color("textPrimary")
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Components.UiTheme.spacing("md")

                        Repeater {
                            model: [{ title: "FOUP", index: configView.foupChartIndex }]
                            delegate: Components.ChartCard {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.preferredHeight: Components.UiTheme.controlHeight(220)
                                radius: Components.UiTheme.radius(18)
                                color: Components.UiTheme.color("panel")
                                border.color: Components.UiTheme.color("outline")

                                // 使用 readonly property 缓存配置，确保稳定的属性绑定
                                readonly property var config: configView.chartEntry(modelData.index, modelData.title)
                                seriesModel: config.seriesModel
                                xColumn: config.xColumn
                                yColumn: config.yColumn

                                scaleFactor: configView.scaleFactor


                                Text {
                                    visible: !seriesModel
                                    anchors.centerIn: parent
                                    text: "点击开始采集后显示实时曲线"
                                    color: Components.UiTheme.color("textSecondary")
                                    font.pixelSize: Components.UiTheme.fontSize("body")
                                }
                            }
                        }

                        Text {
                            text: (typeof foupAcquisition !== "undefined" && foupAcquisition && !isNaN(foupAcquisition.lastValue))
                            ? "当前值：" + foupAcquisition.lastValue.toFixed(2)
                            : "当前值：--"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }
                    }
                }
            }
        }
    }
}