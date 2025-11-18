import QtQuick
import "../components"

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: 10
    spacing: 10

    CustomButton {
        text: "Start Job"
        width: parent.width
    }
    CustomButton {
        text: "Stop Job"
        width: parent.width
    }
    CustomButton {
        text: "Pause Job"
        width: parent.width
    }
}
