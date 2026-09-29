import QtQuick
import "../components"
import "../components" as Components

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    // 内边距由 CommandPanel 统一提供（保证命令区可滚动到最后一个按钮）
    spacing: Components.UiTheme.spacing("md")

    Text {
        text: "Loadport 配置命令"
        font.bold: true
        font.pixelSize: Components.UiTheme.fontSize("subtitle")
        color: Components.UiTheme.color("textPrimary")
        horizontalAlignment: Text.AlignHCenter
        width: parent.width
    }

    // 原来的"设置 IP / 设置时间"只打日志，已删除
    CommandPlaceholder {
        message: "Loadport 参数配置尚未接入后端"
    }
}
