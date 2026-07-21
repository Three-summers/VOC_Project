import QtQuick
import "../components" as Components

Column {
    id: root

    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Components.UiTheme.spacing("md")
    spacing: Components.UiTheme.spacing("md")

    readonly property var standbyController: (
        typeof standbyMediaController !== "undefined" && standbyMediaController
    ) ? standbyMediaController : null

    Text {
        width: parent.width
        text: "待机动画"
        horizontalAlignment: Text.AlignHCenter
        font.bold: true
        font.pixelSize: Components.UiTheme.fontSize("subtitle")
        color: Components.UiTheme.color("textPrimary")
    }

    Text {
        width: parent.width
        text: "在中央面板选择媒体目录和待机秒数。"
        wrapMode: Text.WordWrap
        font.pixelSize: Components.UiTheme.fontSize("body")
        color: Components.UiTheme.color("textSecondary")
    }

    Components.CustomButton {
        width: parent.width
        text: "刷新媒体"
        enabled: root.standbyController !== null
        onClicked: root.standbyController.refreshMedia()
    }
}
