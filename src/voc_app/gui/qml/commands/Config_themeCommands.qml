import QtQuick
import "../components"
import "../components" as Components

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Components.UiTheme.spacing("md")
    spacing: Components.UiTheme.spacing("md")

    // 通过命令面板快速操作调色板
    readonly property var defaultPalette: Components.UiTheme.createDefaultPalette()

    function clonePalette(source) {
        try {
            return JSON.parse(JSON.stringify(source || {}));
        } catch (e) {
            console.warn("调色板克隆失败:", e);
            return {};
        }
    }

    function resetPalette() {
        const next = clonePalette(defaultPalette);
        Components.UiTheme.palette = next;
    }

    Text {
        text: "调色命令"
        font.bold: true
        font.pixelSize: Components.UiTheme.fontSize("subtitle")
        color: Components.UiTheme.color("textPrimary")
        horizontalAlignment: Text.AlignHCenter
        width: parent.width
    }

    Components.CustomButton {
        text: "重置默认配色"
        width: parent.width
        onClicked: resetPalette()
    }

    Components.CustomButton {
        text: "导出当前配色到日志"
        width: parent.width
        onClicked: {
            const payload = JSON.stringify(Components.UiTheme.palette, null, 2);
            console.log("当前调色板:", payload);
        }
    }
}
