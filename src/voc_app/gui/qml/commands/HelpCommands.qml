import QtQuick
import "../components"

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: 10
    spacing: 10

    // 原来的"View Manual / Contact Support"只打日志，已删除
    CommandPlaceholder {
        message: "帮助内容见中间面板"
    }
}
