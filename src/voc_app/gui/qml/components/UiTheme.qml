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

    // 工业风调色板 - 高对比度版
    property var palette: ({
        background: "#050505",
        surface: "#121212",
        panel: "#1e1e1e",
        panelAlt: "#2d2d2d",
        outline: "#666666",
        outlineStrong: "#999999",
        buttonBase: "#333333",
        buttonHover: "#444444",
        buttonDown: "#555555",
        textPrimary: "#ffffff",
        textSecondary: "#e0e0e0",
        textOnLight: "#000000",
        textOnLightMuted: "#333333",
        accentInfo: "#2979ff",
        accentSuccess: "#00e676",
        accentWarning: "#ffab00",
        accentAlarm: "#ff1744"
    })

    // 创建默认调色板对象（用于重置功能）
    function createDefaultPalette() {
        return {
            background: "#050505",
            surface: "#121212",
            panel: "#1e1e1e",
            panelAlt: "#2d2d2d",
            outline: "#666666",
            outlineStrong: "#999999",
            buttonBase: "#333333",
            buttonHover: "#444444",
            buttonDown: "#555555",
            textPrimary: "#ffffff",
            textSecondary: "#e0e0e0",
            textOnLight: "#000000",
            textOnLightMuted: "#333333",
            accentInfo: "#2979ff",
            accentSuccess: "#00e676",
            accentWarning: "#ffab00",
            accentAlarm: "#ff1744"
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

    function color(role, fallback) {
        if (palette && role in palette)
            return palette[role];
        return fallback !== undefined ? fallback : "#ffffff";
    }
}
