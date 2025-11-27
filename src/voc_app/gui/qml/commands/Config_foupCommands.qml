import QtQuick
import "../components"
import "../components" as Components

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Components.UiTheme.spacing("md")
    spacing: Components.UiTheme.spacing("md")

    readonly property var acquisitionController: (typeof foupAcquisition !== "undefined") ? foupAcquisition : null

    Text {
        text: "FOUP 采集命令"
        font.bold: true
        font.pixelSize: Components.UiTheme.fontSize("subtitle")
        color: Components.UiTheme.color("textPrimary")
        horizontalAlignment: Text.AlignHCenter
        width: parent.width
    }

    CustomButton {
        text: "设置时间"
        width: parent.width
        onClicked: console.log("Config/FOUP: 设置时间")
    }

    CustomButton {
        text: acquisitionController && acquisitionController.running ? "采集中" : "开始采集"
        width: parent.width
        enabled: acquisitionController && !acquisitionController.running
        status: acquisitionController && acquisitionController.running ? "processing" : "normal"
        onClicked: {
            if (!acquisitionController) {
                console.warn("foupAcquisition 未注入");
                return;
            }
            acquisitionController.startAcquisition();
        }
    }

    CustomButton {
        text: "停止采集"
        width: parent.width
        enabled: acquisitionController && acquisitionController.running
        onClicked: {
            if (!acquisitionController) {
                console.warn("foupAcquisition 未注入");
                return;
            }
            acquisitionController.stopAcquisition();
        }
    }

    Text {
        text: acquisitionController ? acquisitionController.statusMessage : "采集控制器不可用"
        color: Components.UiTheme.color("textSecondary")
        font.pixelSize: Components.UiTheme.fontSize("body")
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        width: parent.width
    }
}
