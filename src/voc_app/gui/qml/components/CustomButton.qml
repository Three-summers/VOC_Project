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

    readonly property var palette: Components.UiTheme.palette

    function statusFillColor() {
        switch (status) {
        case "alarm":
            return palette.accentAlarm;
        case "warning":
            return palette.accentWarning;
        case "processing":
            return palette.accentInfo;
        case "attention":
        case "ready":
            return palette.accentSuccess;
        default:
            if (control.checked && control.twoState)
                return palette.accentInfo;
            if (control.down)
                return palette.buttonDown;
            return palette.buttonBase;
        }
    }

    function statusBorderColor() {
        switch (status) {
        case "alarm":
            return palette.accentAlarm;
        case "warning":
            return palette.accentWarning;
        case "processing":
            return palette.accentInfo;
        case "attention":
        case "ready":
            return palette.accentSuccess;
        default:
            if (control.checked && control.twoState)
                return palette.accentInfo;
            return palette.outline;
        }
    }

    function statusTextColor() {
        switch (status) {
        case "alarm":
        case "warning":
        case "processing":
        case "attention":
        case "ready":
            return palette.textPrimary;
        default:
            if (control.checked && control.twoState)
                return palette.textPrimary;
            return palette.textPrimary;
        }
    }

    background: Rectangle {
        // 视觉反馈：按下、双态选中或报警时均切换为相应强调色
        color: control.status === "warning" ? Qt.darker(statusFillColor(), 1.08) : statusFillColor()
        border.color: statusBorderColor()
        border.width: status === "normal" ? Math.max(1, control.resolvedScale) : Math.max(2, 4 * control.resolvedScale)
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
        color: statusTextColor()
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
