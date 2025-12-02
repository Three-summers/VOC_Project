import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components" as Components

Rectangle {
    id: configView
    color: Components.UiTheme.color("background")

    property string currentSubPage: "loadport"
    property real scaleFactor: Components.UiTheme.controlScale
    property var foupLimitRef: null

    function resolveSubPageSource(key) {
        switch (key) {
            case "foup": return "config/ConfigFoupPage.qml"
            case "theme": return "config/ConfigThemePage.qml"
            default: return "config/ConfigLoadportPage.qml"
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Components.UiTheme.spacing("xl")
        spacing: Components.UiTheme.spacing("lg")

        Loader {
            id: contentLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            source: resolveSubPageSource(currentSubPage)

            onLoaded: {
                if (item && item.hasOwnProperty("scaleFactor")) {
                    item.scaleFactor = configView.scaleFactor
                }
            }
        }
    }

    onScaleFactorChanged: {
        if (contentLoader.item && contentLoader.item.hasOwnProperty("scaleFactor")) {
            contentLoader.item.scaleFactor = configView.scaleFactor
        }
    }
}
