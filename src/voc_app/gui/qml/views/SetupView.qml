import QtQuick
import "../components"
import "../components" as Components

Rectangle {
    color: "lightblue"
    Text {
        anchors.centerIn: parent
        text: "Setup View Content"
        font.pixelSize: Components.UiTheme.fontSize("display")
    }
}
