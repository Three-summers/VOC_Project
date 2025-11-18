import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components" as Components

Rectangle {
    id: configView
    color: "#f5f5f5"

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
            text: "此页面正在规划中，后续将用于展示和编辑系统配置。"
            wrapMode: Text.Wrap
            color: "#555555"
            font.pixelSize: Components.UiTheme.fontSize("body")
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Components.UiTheme.radius("sm")
            border.color: "#d0d0d0"
            color: "#ffffff"

            Text {
                anchors.centerIn: parent
                text: "暂无配置项"
                color: "#999999"
                font.pixelSize: Components.UiTheme.fontSize("body")
            }
        }
    }
}
