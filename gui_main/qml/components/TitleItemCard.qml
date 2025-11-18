import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects

Item {
    id: root

    default property alias contentData: contentArea.data
    property int padding: 16
    property color backgroundColor: "#ffffff"
    property color borderColor: "#e0e0e0"
    property int borderWidth: 1
    property int radius: 8
    property bool showShadow: true

    property Component header
    property Component footer

    signal clicked()

    implicitWidth: background.width
    implicitHeight: background.height

    // 使用 DropShadow 来实现现代化的卡片阴影效果
    DropShadow {
        anchors.fill: background
        source: background
        horizontalOffset: 2
        verticalOffset: 2
        radius: 8.0
        samples: 16
        color: "#80000000" // 50% 透明度的黑色
        visible: root.showShadow
    }

    // 卡片的背景和边框
    Rectangle {
        id: background
        width: parent.width
        color: root.backgroundColor
        border.color: root.borderColor
        border.width: root.borderWidth
        radius: root.radius

        // 使用 ColumnLayout 来垂直组织 header, content, footer
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.padding
            spacing: 12

            Loader {
                id: headerLoader
                sourceComponent: root.header
                visible: sourceComponent !== undefined
                Layout.fillWidth: true
            }

            Item {
                id: contentArea
                Layout.fillWidth: true
                Layout.fillHeight: true
            }

            Loader {
                id: footerLoader
                sourceComponent: root.footer
                visible: sourceComponent !== undefined
                Layout.fillWidth: true
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked() // 当点击时，发出 clicked 信号
    }
}

