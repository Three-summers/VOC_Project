import QtQuick
import "../components"

Column {
    id: alarmsCommands
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    // 内边距由 CommandPanel 统一提供（保证命令区可滚动到最后一个按钮）
    spacing: 10

    property var commandPanelRef: null
    property var alarmStore: null

    CustomButton {
        text: "关闭报警"
        width: parent.width
        onClicked: {
            if (alarmsCommands.alarmStore)
                alarmsCommands.alarmStore.closeAlarms();
        }
    }

    CustomButton {
        text: "清除报警"
        width: parent.width
        onClicked: {
            if (alarmsCommands.alarmStore)
                alarmsCommands.alarmStore.clearAlarms();
        }
    }
}
