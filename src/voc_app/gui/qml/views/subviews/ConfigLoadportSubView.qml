import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components" as Components

Item {
    id: rootItem
    anchors.fill: parent

    // Properties inherited from ConfigView
    property var loadportInfo: ({
        ipAddress: "192.168.0.100",
        deviceTime: Qt.formatDateTime(new Date(), "yyyy-MM-dd hh:mm:ss")
    })

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
                    text: displayValue(loadportInfo.ipAddress) // Use local property
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
                    text: displayValue(loadportInfo.deviceTime) // Use local property
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
