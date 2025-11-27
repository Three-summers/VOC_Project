import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components" as Components

Rectangle {
    id: fileView
    color: Components.UiTheme.color("background")

    property var csvFileManagerRef: null
    property real scaleFactor: Components.UiTheme.controlScale

    function triggerAutomaticSelection() {
        if (!fileView.csvFileManagerRef)
            return;
        const hasFiles = fileView.csvFileManagerRef.csvFiles && fileView.csvFileManagerRef.csvFiles.length > 0;
        const fallbackFile = hasFiles ? fileView.csvFileManagerRef.csvFiles[0] : "";
        const fileToSelect = fileView.csvFileManagerRef.activeFile || fallbackFile;
        if (fileToSelect)
            fileView.csvFileManagerRef.parse_csv_file(fileToSelect);
    }

    RowLayout {
        anchors.fill: parent
        spacing: Components.UiTheme.spacing("lg")

        // 左侧：CSV 文件列表
        Rectangle {
            Layout.preferredWidth: Components.UiTheme.controlWidth("commandPanel")
            Layout.fillHeight: true
            color: Components.UiTheme.color("panelAlt")
            border.color: Components.UiTheme.color("outline")
            border.width: 1

            ListView {
                id: fileListView
                anchors.fill: parent
                model: fileView.csvFileManagerRef ? fileView.csvFileManagerRef.csvFiles : []
                clip: true

                delegate: Rectangle {
                    width: fileListView.width
                    height: Components.UiTheme.controlHeight("input")
                    color: fileView.csvFileManagerRef && fileView.csvFileManagerRef.activeFile === model.modelData 
                        ? Components.UiTheme.color("accentInfo") // Selection Color
                        : "transparent"

                    Text {
                        text: model.modelData
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: Components.UiTheme.spacing("md")
                        color: fileView.csvFileManagerRef && fileView.csvFileManagerRef.activeFile === model.modelData 
                            ? Components.UiTheme.color("textPrimary") 
                            : Components.UiTheme.color("textSecondary")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (fileView.csvFileManagerRef) {
                                fileView.csvFileManagerRef.parse_csv_file(model.modelData);
                            }
                        }
                    }
                }
            }
        }

        // 右侧：曲线图区域
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Components.UiTheme.color("background")

            GridLayout {
                anchors.fill: parent
                anchors.margins: Components.UiTheme.spacing("lg")
                columns: 2
                rows: 2
                rowSpacing: Components.UiTheme.spacing("lg")
                columnSpacing: Components.UiTheme.spacing("lg")

                Repeater {
                    model: fileView.csvFileManagerRef ? fileView.csvFileManagerRef.dataModel : null
                    delegate: ChartCard {
                        chartTitle: model.columnName
                        dataPoints: model.dataPoints
                        scaleFactor: fileView.scaleFactor
                    }
                }
            }
        }
    }
}