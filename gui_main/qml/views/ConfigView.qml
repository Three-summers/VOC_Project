import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components" as Components

Rectangle {
    id: configView
    color: "#f5f5f5"

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
            color: "#333333"
        }

        Text {
            text: "通过子页面查看并设置 Loadport 与 FOUP 的基础运行参数。"
            wrapMode: Text.Wrap
            color: "#555555"
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
                color: "#ffffff"
                border.color: "#dbe0ed"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Components.UiTheme.spacing("xl")
                    spacing: Components.UiTheme.spacing("lg")

                    Text {
                        text: "Loadport 配置"
                        font.pixelSize: Components.UiTheme.fontSize("title")
                        font.bold: true
                        color: "#2f3645"
                    }

                    Text {
                        text: "当前通信参数"
                        color: "#6c738a"
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        rowSpacing: Components.UiTheme.spacing("md")
                        columnSpacing: Components.UiTheme.spacing("lg")

                        Text {
                            text: "IP 地址"
                            color: "#6c738a"
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }

                        Text {
                            text: configView.displayValue(configView.loadportInfo.ipAddress)
                            font.pixelSize: Components.UiTheme.fontSize("subtitle")
                            font.bold: true
                            color: "#2f3645"
                        }

                        Text {
                            text: "设备时间"
                            color: "#6c738a"
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }

                        Text {
                            text: configView.displayValue(configView.loadportInfo.deviceTime)
                            font.pixelSize: Components.UiTheme.fontSize("subtitle")
                            font.bold: true
                            color: "#2f3645"
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Components.UiTheme.radius(14)
                        color: "#f6f8fc"
                        border.color: "#e1e7f3"

                        Text {
                            anchors.centerIn: parent
                            text: "待接入实时 loadport 数据"
                            color: "#9aa5be"
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
                color: "#ffffff"
                border.color: "#dbe0ed"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Components.UiTheme.spacing("xl")
                    spacing: Components.UiTheme.spacing("lg")

                    Text {
                        text: "FOUP 配置"
                        font.pixelSize: Components.UiTheme.fontSize("title")
                        font.bold: true
                        color: "#2f3645"
                    }

                    Text {
                        text: "当前时间及采集通道状态"
                        color: "#6c738a"
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        rowSpacing: Components.UiTheme.spacing("md")
                        columnSpacing: Components.UiTheme.spacing("lg")

                        Text {
                            text: "同步时间"
                            color: "#6c738a"
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }

                        Text {
                            text: configView.displayValue(configView.foupInfo.syncTime)
                            font.pixelSize: Components.UiTheme.fontSize("subtitle")
                            font.bold: true
                            color: "#2f3645"
                        }

                        Text {
                            text: "采集状态"
                            color: "#6c738a"
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }

                        RowLayout {
                            spacing: Components.UiTheme.spacing("sm")

                            Rectangle {
                                width: Components.UiTheme.spacing("lg")
                                height: Components.UiTheme.spacing("lg")
                                radius: Components.UiTheme.radius("pill")
                                color: configView.foupInfo.acquisitionStatus === "采集中" ? "#4caf50" : "#f44336"
                            }

                            Text {
                                text: configView.displayValue(configView.foupInfo.acquisitionStatus)
                                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                                font.bold: true
                                color: "#2f3645"
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Components.UiTheme.radius(14)
                        color: "#f6f8fc"
                        border.color: "#e1e7f3"

                        Text {
                            anchors.centerIn: parent
                            text: "采集通道示意(稍后接入)"
                            color: "#9aa5be"
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }
                    }
                }
            }
        }
    }
}
