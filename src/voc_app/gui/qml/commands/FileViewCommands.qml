import QtQuick
import "../components"

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    // 内边距由 CommandPanel 统一提供（保证命令区可滚动到最后一个按钮）
    spacing: 10

    CustomButton {
        text: "Restart System"
        width: parent.width
    }
    CustomButton {
        text: "Shutdown System"
        width: parent.width
    }
}
