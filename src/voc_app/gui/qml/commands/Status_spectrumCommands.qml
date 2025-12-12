import QtQuick
import "../components"
import "../components" as Components

Column {
    id: spectrumCommandsRoot
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Components.UiTheme.spacing("md")
    spacing: Components.UiTheme.spacing("md")

    // 缓存全局引用，避免重复检查
    readonly property var simulator: (typeof spectrumSimulator !== "undefined") ? spectrumSimulator : null
    readonly property var model: (typeof spectrumModel !== "undefined") ? spectrumModel : null

    Text {
        text: "频谱控制"
        font.bold: true
        font.pixelSize: Components.UiTheme.fontSize("subtitle")
        color: Components.UiTheme.color("textPrimary")
        horizontalAlignment: Text.AlignHCenter
        width: parent.width
    }

    CustomButton {
        text: (spectrumCommandsRoot.simulator && spectrumCommandsRoot.simulator.running) ? "停止模拟" : "启动模拟"
        width: parent.width
        onClicked: {
            if (spectrumCommandsRoot.simulator) {
                if (spectrumCommandsRoot.simulator.running) {
                    spectrumCommandsRoot.simulator.stop()
                } else {
                    spectrumCommandsRoot.simulator.start()
                }
            }
        }
    }

    CustomButton {
        text: "清空数据"
        width: parent.width
        onClicked: {
            if (spectrumCommandsRoot.model) {
                spectrumCommandsRoot.model.clear()
            }
        }
    }
}
