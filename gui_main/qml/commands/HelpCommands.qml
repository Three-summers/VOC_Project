import QtQuick
import "../components"

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: 10
    spacing: 10

    CustomButton {
        text: "View Manual"
        width: parent.width
    }
    CustomButton {
        text: "Contact Support"
        width: parent.width
    }
}
