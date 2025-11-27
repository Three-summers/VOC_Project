import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components" as Components

Rectangle {
    id: alarmsView
    // Custom dark red background for alarm state to fit dark theme
    color: alarmStore && alarmStore.hasActiveAlarm ? "#3a0000" : Components.UiTheme.color("background")
    border.color: alarmStore && alarmStore.hasActiveAlarm ? Components.UiTheme.color("accentAlarm") : Components.UiTheme.color("outline")
    border.width: Math.max(1, Components.UiTheme.controlScale)
    radius: Components.UiTheme.radius("sm")

    property var alarmStore: null
    property real scaleFactor: Components.UiTheme.controlScale

    function closeAlarmVisuals() {
        if (alarmStore)
            alarmStore.closeAlarms();
    }

    function clearAlarms() {
        if (alarmStore)
            alarmStore.clearAlarms();
    }

    function addAlarm(timestamp, message) {
        if (alarmStore)
            alarmStore.addAlarm(timestamp, message);
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Components.UiTheme.spacing("xl")
        spacing: Components.UiTheme.spacing("lg")

        Text {
            text: alarmStore && alarmStore.hasActiveAlarm ? "当前有未确认报警" : "报警记录"
            font.bold: true
            font.pixelSize: Components.UiTheme.fontSize("title")
            color: alarmStore && alarmStore.hasActiveAlarm ? Components.UiTheme.color("accentAlarm") : Components.UiTheme.color("textPrimary")
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            border.color: Components.UiTheme.color("outline")
            color: Components.UiTheme.color("panel")
            radius: Components.UiTheme.radius("sm")

            Flickable {
                anchors.fill: parent
                contentWidth: width
                contentHeight: tableColumn.implicitHeight
                clip: true
                ScrollBar.vertical: ScrollBar {}

                Column {
                    id: tableColumn
                    width: parent.width
                    spacing: 0

                    Row {
                        width: parent.width
                        height: Components.UiTheme.controlHeight("input")
                        spacing: 0

                        Rectangle {
                            width: parent.width * 0.32
                            height: parent.height
                            color: Components.UiTheme.color("panelAlt")
                            border.color: Components.UiTheme.color("outline")
                            Text {
                                anchors.centerIn: parent
                                text: "时间"
                                font.bold: true
                                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                                color: Components.UiTheme.color("textPrimary")
                            }
                        }

                        Rectangle {
                            width: parent.width * 0.68
                            height: parent.height
                            color: Components.UiTheme.color("panelAlt")
                            border.color: Components.UiTheme.color("outline")
                            Text {
                                anchors.centerIn: parent
                                text: "报警信息"
                                font.bold: true
                                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                                color: Components.UiTheme.color("textPrimary")
                            }
                        }
                    }

                    Repeater {
                        id: alarmsRepeater
                        model: alarmStore ? alarmStore.alarmModel : null
                        delegate: Row {
                            width: parent.width
                            height: Components.UiTheme.controlHeight(54)
                            spacing: 0

                            Rectangle {
                                width: parent.width * 0.32
                                height: parent.height
                                color: index % 2 === 0 ? Components.UiTheme.color("surface") : Components.UiTheme.color("panel")
                                border.color: Components.UiTheme.color("outline")
                                Text {
                                    anchors.centerIn: parent
                                    text: model.timestamp
                                    font.pixelSize: Components.UiTheme.fontSize("body")
                                    color: Components.UiTheme.color("textPrimary")
                                }
                            }

                            Rectangle {
                                width: parent.width * 0.68
                                height: parent.height
                                color: index % 2 === 0 ? Components.UiTheme.color("surface") : Components.UiTheme.color("panel")
                                border.color: Components.UiTheme.color("outline")
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left: parent.left
                                    anchors.leftMargin: Components.UiTheme.spacing("md")
                                    width: parent.width - 2 * Components.UiTheme.spacing("md")
                                    text: model.message
                                    wrapMode: Text.WordWrap
                                    font.pixelSize: Components.UiTheme.fontSize("body")
                                    color: Components.UiTheme.color("textPrimary")
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}