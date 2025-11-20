import QtQuick
import "../components"

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: 10
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
