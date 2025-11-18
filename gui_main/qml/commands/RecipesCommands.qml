import QtQuick
import "../components"

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: 10
    spacing: 10

    CustomButton {
        text: "Load Recipe"
        width: parent.width
    }
    CustomButton {
        text: "Save Recipe"
        width: parent.width
    }
}
