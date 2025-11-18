import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: popup

    width: 500
    height: 300
    modal: true
    focus: true
    closePolicy: Popup.NoAutoClose

    x: (parent.width - width) / 2
    y: (parent.height - height) / 2

    background: Rectangle {
        color: "#ffffff"
        border.color: "#cccccc"
        border.width: 1
        radius: 5
    }

    property alias title: titleText.text
    property alias contentData: contentLoader.sourceComponent
    property alias footerData: footerLoader.sourceComponent
    property alias internalContentLoader: contentLoader

    contentItem: ColumnLayout {
        spacing: 0

        // 1. 标题栏
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            color: "#f0f0f0"

            Text {
                id: titleText
                anchors.centerIn: parent
                font.bold: true
                text: "Dialog Title"
            }

            // 自定义关闭按钮
            Text {
                text: "X"
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 15
                font.bold: true
                MouseArea {
                    anchors.fill: parent
                    onClicked: popup.close()
                }
            }
        }

        // 2. 内容区
        Loader {
            id: contentLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 20
        }

        // 3. 底部按钮区
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 50
            color: "#f0f0f0"
            Loader {
                id: footerLoader
                anchors.fill: parent
            }
        }
    }
}
