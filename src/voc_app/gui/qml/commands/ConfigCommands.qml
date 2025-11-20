import QtQuick
import "../components"

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: 10
    spacing: 10

    CustomButton {
        text: "导入配置"
        width: parent.width
    }

    CustomButton {
        text: "导出配置"
        width: parent.width
    }
}
