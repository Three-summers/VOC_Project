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
        text: "FOUP 采集命令"
        font.bold: true
        font.pixelSize: Components.UiTheme.fontSize("subtitle")
        color: "#222"
        horizontalAlignment: Text.AlignHCenter
        width: parent.width
    }

    CustomButton {
        text: "设置时间"
        width: parent.width
        onClicked: console.log("Config/FOUP: 设置时间")
    }

    CustomButton {
        text: "控制采集"
        width: parent.width
        onClicked: console.log("Config/FOUP: 控制采集")
    }
}
