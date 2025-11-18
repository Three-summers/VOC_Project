import QtQuick
import "../components"

Column {
    id: alarmsCommands
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: 10
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
