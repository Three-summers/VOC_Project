import QtQuick
import "../components"
import "../components" as Components

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Components.UiTheme.spacing("md")
    spacing: Components.UiTheme.spacing("md")

    Text {
        text: "Loadport 配置命令"
        font.bold: true
        font.pixelSize: Components.UiTheme.fontSize("subtitle")
        color: "#222"
        horizontalAlignment: Text.AlignHCenter
        width: parent.width
    }

    CustomButton {
        text: "设置 IP"
        width: parent.width
        onClicked: console.log("Config/Loadport: 设置 IP")
    }

    CustomButton {
        text: "设置时间"
        width: parent.width
        onClicked: console.log("Config/Loadport: 设置时间")
    }
}
