import QtQuick
import "../components"

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    // 内边距由 CommandPanel 统一提供（保证命令区可滚动到最后一个按钮）
    spacing: 10

    // 该文件只作为"没有子页命令文件"时的兜底；
    // 原来的导入/导出配置按钮没有任何动作，已删除。
    CommandPlaceholder {
        message: "本页暂无可用操作"
    }
}
