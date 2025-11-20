pragma Singleton
import QtQuick

QtObject {
    id: theme

    // Base scale mirrors ApplicationWindow.uiScale via binding from main.qml
    property real baseScale: 1.0

    readonly property real minScale: 0.85
    readonly property real maxScale: 1.8

    // Derived scales allow fonts, controls and spacing to grow at different rates
    property real fontScale: 1.0
    property real controlScale: 1.0
    property real spacingScale: 1.0

    Component.onCompleted: updateScales()
    onBaseScaleChanged: updateScales()

    function updateScales() {
        const clamped = Math.min(maxScale, Math.max(minScale, baseScale));
        fontScale = Math.min(1.4, Math.max(0.9, 1 + (clamped - 1) * 0.7));
        controlScale = Math.min(1.9, Math.max(0.85, 1 + (clamped - 1) * 1.15));
        spacingScale = Math.min(1.6, Math.max(0.9, 1 + (clamped - 1) * 0.9));
    }

    function fontSize(role) {
        switch (role) {
        case "display":
            return 28 * fontScale;
        case "title":
            return 22 * fontScale;
        case "subtitle":
            return 18 * fontScale;
        case "body":
            return 16 * fontScale;
        case "label":
            return 14 * fontScale;
        case "caption":
            return 12 * fontScale;
        default:
            if (typeof role === "number")
                return role * fontScale;
            return 16 * fontScale;
        }
    }

    function controlHeight(role) {
        switch (role) {
        case "titleBar":
            return 72 * controlScale;
        case "panelHeader":
            return 64 * controlScale;
        case "nav":
            return Math.max(72, 80 * controlScale);
        case "button":
            return 56 * controlScale;
        case "buttonThin":
            return 44 * controlScale;
        case "input":
            return 48 * controlScale;
        default:
            if (typeof role === "number")
                return role * controlScale;
            return 56 * controlScale;
        }
    }

    function controlWidth(role) {
        switch (role) {
        case "commandPanel":
            return 160 * controlScale;
        case "button":
            return 120 * controlScale;
        default:
            if (typeof role === "number")
                return role * controlScale;
            return 120 * controlScale;
        }
    }

    function spacing(level) {
        switch (level) {
        case "xxs":
            return 2 * spacingScale;
        case "xs":
            return 4 * spacingScale;
        case "sm":
            return 6 * spacingScale;
        case "md":
            return 10 * spacingScale;
        case "lg":
            return 14 * spacingScale;
        case "xl":
            return 20 * spacingScale;
        default:
            if (typeof level === "number")
                return level * spacingScale;
            return 10 * spacingScale;
        }
    }

    function radius(level) {
        switch (level) {
        case "sm":
            return 4 * controlScale;
        case "md":
            return 8 * controlScale;
        default:
            if (typeof level === "number")
                return level * controlScale;
            return 4 * controlScale;
        }
    }

    function px(value, target) {
        if (target === "font")
            return value * fontScale;
        if (target === "spacing")
            return value * spacingScale;
        return value * controlScale;
    }
}
