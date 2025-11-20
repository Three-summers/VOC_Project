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
        text: "Loadport"
        font.bold: true
        font.pixelSize: Components.UiTheme.fontSize("subtitle")
        color: "#222"
        horizontalAlignment: Text.AlignHCenter
        width: parent.width
    }

    CustomButton {
        text: "开始对接"
        width: parent.width
        onClicked: console.log("Loadport: 开始对接")
    }

    CustomButton {
        text: "抬升台面"
        width: parent.width
        onClicked: console.log("Loadport: 抬升台面")
    }

    CustomButton {
        text: "锁扣/解锁"
        width: parent.width
        onClicked: console.log("Loadport: 锁扣操作")
    }
}
