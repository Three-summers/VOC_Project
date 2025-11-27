import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: popup

    property var popupAnchorItem: null
    property int anchorMargin: 24
    property int footerPadding: 12

    implicitWidth: popupAnchorItem && parent ? Math.min(parent.width * 0.8, 500) : 500
    width: implicitWidth
    implicitHeight: contentColumn.implicitHeight
    height: Math.max(implicitHeight, 240)
    modal: true
    focus: true
    closePolicy: Popup.NoAutoClose

    parent: popupAnchorItem ? popupAnchorItem : parent

    x: parent ? Math.max(anchorMargin, (parent.width - width) / 2) : 0
    y: parent
        ? (popupAnchorItem ? anchorMargin : (parent.height - height) / 2)
        : 0

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
        id: contentColumn
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
            Layout.margins: 20
            Layout.preferredHeight: (item && item.implicitHeight ? item.implicitHeight : 160) + Layout.margins * 2
        }

        // 3. 底部按钮区
        Rectangle {
            id: footerSection
            Layout.fillWidth: true
            implicitHeight: Math.max(
                (footerLoader.implicitHeight > 0 ? footerLoader.implicitHeight : 0) + popup.footerPadding * 2,
                60
            )
            Layout.preferredHeight: implicitHeight
            color: "#f0f0f0"
            Loader {
                id: footerLoader
                anchors.fill: parent
                anchors.margins: popup.footerPadding
            }
        }
    }
}
