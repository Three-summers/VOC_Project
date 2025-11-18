import QtQuick
import "./components"
import "./components" as Components

Rectangle {
    id: navRectangle
    color: "#333333"
    implicitHeight: Components.UiTheme.controlHeight("nav")

    property string currentView: "Status"
    property bool hasNewAlarms: false
    property bool hasNewWarnings: false
    property real scaleFactor: Components.UiTheme.controlScale

    signal navigationButtonClicked(string viewName)

    onNavigationButtonClicked: (viewName) => {
        if (viewName) {
            currentView = viewName
        }
    }

    ListModel {
        id: leftNavModel
        ListElement { text: "Status"; viewName: "Status" }
        ListElement { text: "DataLog"; viewName: "DataLog" }
        // ListElement { text: "FileView"; viewName: "FileView" }
        // ListElement { text: "Recipes"; viewName: "Recipes" }
        // ListElement { text: "Setup"; viewName: "Setup" }
        ListElement { text: "Config"; viewName: "Config" }
        // ListElement { text: "(Future)"; viewName: "" }
        // ListElement { text: "(Future)"; viewName: "" }
        // ListElement { text: "(Future)"; viewName: "" }
    }

    ListModel {
        id: rightNavModel
        ListElement { text: "Alarms"; viewName: "Alarms" }
        ListElement { text: "Help"; viewName: "Help" }
    }

    Item {
        anchors.fill: parent

        Row {
            id: navRow
            spacing: Components.UiTheme.spacing("lg")
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter

            Repeater {
                model: leftNavModel
                delegate: CustomButton {
                    text: model.text
                    enabled: model.viewName !== ""
                    twoState: true
                    checked: navRectangle.currentView === model.viewName
                    status: navRectangle.currentView === model.viewName ? "processing" : "normal"
                    scaleFactor: navRectangle.scaleFactor
                    onClicked: navRectangle.navigationButtonClicked(model.viewName)
                }
            }

            Item {
                width: Components.UiTheme.spacing("xl")
                height: 1
            }

            Repeater {
                model: rightNavModel
                delegate: CustomButton {
                    text: model.text
                    enabled: model.viewName !== ""
                    twoState: true
                    checked: navRectangle.currentView === model.viewName
                    scaleFactor: navRectangle.scaleFactor
                    status: {
                        if (model.text === "Alarms") {
                            if (navRectangle.hasNewAlarms) return "alarm";
                            if (navRectangle.hasNewWarnings) return "warning";
                        }
                        if (navRectangle.currentView === model.viewName) return "processing";
                        return "normal";
                    }
                    onClicked: navRectangle.navigationButtonClicked(model.viewName)
                }
            }
        }
    }
}
