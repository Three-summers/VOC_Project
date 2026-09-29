import QtQuick
import "../components"

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: 10
    spacing: 10

    // 该文件只作为"没有子页命令文件"时的兜底；
    // 原来的 Start/Stop/Pause Job 按钮没有任何动作，已删除。
    CommandPlaceholder {
        message: "本页暂无可用操作"
    }
}
