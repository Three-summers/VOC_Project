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

    // 原来的"数控控制 / 连接控制 / FTP 控制 / 启用自动 Docking"只打日志，
    // 没有任何实际动作，已删除；等后端接口就绪后再补回来。
    CommandPlaceholder {
        message: "FOUP 控制命令尚未接入后端"
    }
}
