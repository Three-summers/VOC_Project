import QtQuick
import "../components"
import "../components" as Components

Rectangle {
    color: "lightgray"
    Text {
        anchors.centerIn: parent
        text: "Help View Content"
        font.pixelSize: Components.UiTheme.fontSize("display")
    }
}
