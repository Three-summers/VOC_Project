import QtQuick
import QtQuick.Controls
import QtQuick.Window
import "."
import "." as Components

Button {
    id: control

    // 1. 尺寸要求 (1.5cm ~= 60px at 96 DPI)
    implicitWidth: Math.max(contentItem.implicitWidth + Components.UiTheme.spacing("lg"), Components.UiTheme.controlWidth("button")) // 按钮宽度至少为120px
    implicitHeight: Math.max(contentItem.implicitHeight + Components.UiTheme.spacing("md"), Components.UiTheme.controlHeight("button")) // 按钮高度至少为56px

    // 2. 行为类型
    property bool twoState: false // false for momentary, true for two-state
    checkable: twoState

    // 3. 文本规范 (Title Case)
    text: "Button"
    property real baseFontPixelSize: Components.UiTheme.fontSize("body")
    // The actual capitalization should be handled when setting the text property.
    // QML doesn't have a built-in 'toTitleCase' function.

    // 4. 突出显示 (Saliences)
    property string status: "normal" // normal, alarm, warning, processing, attention, ready
    property real scaleFactor: (Window.window && Window.window.scaleFactor) ? Window.window.scaleFactor : Components.UiTheme.controlScale
    readonly property real resolvedScale: Math.min(1.4, Math.max(0.9, scaleFactor))
    property real fontScale: Components.UiTheme.fontScale

    function getStatusColor() {
        switch (status) {
            case "alarm":
                return "#FF0000"; // 鲜红色
            case "warning":
                return "#FFFF00"; // 鲜黄色
            case "processing":
                return "#0000FF"; // 中蓝色
            case "attention":
                return "#00FF00"; // 中绿色
            case "ready":
                return "#00FF00"; // 中绿色 (Jobs button special state)
            default:
                return "#808080"; // 默认边框颜色
        }
    }

    background: Rectangle {
        // 视觉反馈：按下状态通过阴影或颜色变化
        color: {
            if (control.status === "alarm") return "#FF0000";
            if (control.status === "warning") return "#FFFF00";
            if (control.status === "ready") return "#00FF00";
            if (control.checked && control.twoState) return "#0000FF"; // 双态按钮选中时为中蓝色
            if (control.down) return "#b0b0b0"; // 瞬时按钮按下时
            return "#c0c0c0"; // 默认颜色
        }
        
        // 突出显示区域环绕按钮边缘
        border.color: getStatusColor()
        border.width: status === "normal" ? Math.max(1, control.resolvedScale) : Math.max(2, 4 * control.resolvedScale) // 突出显示时边框更粗
        radius: 4 * control.resolvedScale
    }

    contentItem: Text {
        text: control.text
        font.family: control.font.family
        font.bold: control.font.bold
        font.italic: control.font.italic
        font.capitalization: control.font.capitalization
        font.pixelSize: Math.min(
            Components.UiTheme.fontSize("subtitle"),
            Math.max(
                Components.UiTheme.fontSize("label"),
                (control.font.pixelSize > 0 ? control.font.pixelSize : control.baseFontPixelSize) * control.fontScale
            )
        )
        color: {
            if (control.status === "alarm" || control.status === "warning" || control.status === "ready" || (control.checked && control.twoState)) {
                return "white"; // 突出显示时文本颜色变为白色
            } else {
                return "#000000";
            }
        }
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
