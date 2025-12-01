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

    // 工业风调色板 - 浅色高对比版
    property var palette: ({
        background: "#f6f8fb",
        surface: "#ffffff",
        panel: "#f1f4f8",
        panelAlt: "#e6ebf2",
        outline: "#cdd4de",
        outlineStrong: "#9aa5b5",
        buttonBase: "#e4ebf7",
        buttonHover: "#d6e3f5",
        buttonDown: "#c7d7ef",
        textPrimary: "#1f2933",
        textSecondary: "#4b5563",
        textOnLight: "#1f2933",
        textOnLightMuted: "#52606d",
        accentInfo: "#2563eb",
        accentSuccess: "#16a34a",
        accentWarning: "#f59e0b",
        accentAlarm: "#e11d48"
    })

    // 创建默认调色板对象（用于重置功能）
    function createDefaultPalette() {
        return {
            background: "#f6f8fb",
            surface: "#ffffff",
            panel: "#f1f4f8",
            panelAlt: "#e6ebf2",
            outline: "#cdd4de",
            outlineStrong: "#9aa5b5",
            buttonBase: "#e4ebf7",
            buttonHover: "#d6e3f5",
            buttonDown: "#c7d7ef",
            textPrimary: "#1f2933",
            textSecondary: "#4b5563",
            textOnLight: "#1f2933",
            textOnLightMuted: "#52606d",
            accentInfo: "#2563eb",
            accentSuccess: "#16a34a",
            accentWarning: "#f59e0b",
            accentAlarm: "#e11d48"
        }
    }

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
            return 120 * controlScale;
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

    function color(role, fallback) {
        if (palette && role in palette)
            return palette[role];
        return fallback !== undefined ? fallback : "#ffffff";
    }
}
