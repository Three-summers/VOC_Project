import QtQuick
import "../components"
import "../components" as Components

Rectangle {
    color: "lightcoral"
    Text {
        anchors.centerIn: parent
        text: "Recipes View Content"
        font.pixelSize: Components.UiTheme.fontSize("display")
    }
}
