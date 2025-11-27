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
        text: "FOUP 控制"
        font.bold: true
        font.pixelSize: Components.UiTheme.fontSize("subtitle")
        color: Components.UiTheme.color("textPrimary")
        horizontalAlignment: Text.AlignHCenter
        width: parent.width
    }

    Repeater {
        model: [
            { text: "数控控制" },
            { text: "连接控制" },
            { text: "FTP 控制" }
        ]

        delegate: CustomButton {
            width: parent.width
            text: modelData.text
            onClicked: console.log("FOUP 命令:", modelData.text)
        }
    }

    CustomButton {
        text: "启用自动 Docking"
        width: parent.width
        onClicked: console.log("FOUP: 自动 Docking")
    }
}
