import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtQml
import "./components" as Components

ApplicationWindow {
    id: root
    width: 1024
    height: 768
    visible: true
    title: "SESI E95 UI"

    // 根据指南，主显示窗口禁止显示操作系统边框
    flags: Qt.FramelessWindowHint

    // 全局属性，用于在面板间通信
    property alias currentView: navigationPanel.currentView

    readonly property real baseWidth: 1024
    readonly property real baseHeight: 768
    readonly property real scaleFactor: Math.min(width / baseWidth, height / baseHeight)
    readonly property real uiScale: Math.min(Math.max(0.9, 1 + (scaleFactor - 1) * 0.6), 1.6)
    font.pixelSize: Components.UiTheme.fontSize("body")

    // 使用透明度来避免初始化时的闪烁
    opacity: 0

    // 延迟显示窗口内容，避免初始化时的闪烁
    Timer {
        id: showWindowTimer
        interval: 100  // 等待 100ms 让内容初始化完成
        running: true
        repeat: false
        onTriggered: {
            root.opacity = 1
            root.showFullScreen()
        }
    }

    QtObject {
        id: foupLimits
        property var limitsMap: ({})
        signal limitsChanged()

        function defaultLimits() {
            return Components.UiConstants.defaultLimits()
        }

        function getLimits(channelIndex) {
            const key = channelIndex || 0;
            const current = limitsMap[key];
            if (current)
                return current;
            return defaultLimits();
        }

        function setLimits(channelIndex, limits) {
            const key = channelIndex || 0;
            const next = Object.assign(defaultLimits(), limits || {});
            const cloned = Object.assign({}, limitsMap);
            cloned[key] = next;
            limitsMap = cloned;
            limitsChanged();
        }
    }

    Binding {
        target: Components.UiTheme
        property: "baseScale"
        value: root.uiScale
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. 标题面板 (Top)
        TitlePanel {
            id: titlePanel
            Layout.fillWidth: true
            Layout.preferredHeight: Components.UiTheme.controlHeight("titleBar")
            scaleFactor: Components.UiTheme.controlScale
            currentViewName: root.currentView
            alarmStoreRef: typeof alarmStore !== "undefined" ? alarmStore : null
            alarmPopupAnchorItem: informationPanel
        }

        // 中间区域，包含信息面板和命令面板
        // 可以添加 SplitView 来实现可调节大小的面板
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // 2. 信息面板 (Center)
            InformationPanel {
                id: informationPanel
                Layout.fillWidth: true
                Layout.fillHeight: true
                scaleFactor: Components.UiTheme.controlScale
                currentView: root.currentView
                csvFileManagerRef: csvFileManager
                alarmStoreRef: typeof alarmStore !== "undefined" ? alarmStore : null
                foupLimitRef: foupLimits
            }

            // 3. 命令面板 (Right)
            CommandPanel {
                id: commandPanel
                Layout.fillHeight: true
                Layout.preferredWidth: Components.UiTheme.controlWidth("commandPanel")
                Layout.minimumWidth: Components.UiTheme.controlWidth("commandPanel")
                scaleFactor: Components.UiTheme.controlScale
                currentView: root.currentView
                informationPanelRef: informationPanel
                alarmStoreRef: typeof alarmStore !== "undefined" ? alarmStore : null
                currentSubPage: informationPanel.currentSubPage
                foupLimitRef: foupLimits
            }
        }

        // 4. 导航面板 (Bottom)
        NavigationPanel {
            id: navigationPanel
            Layout.fillWidth: true
            Layout.preferredHeight: Components.UiTheme.controlHeight("nav")
            scaleFactor: Components.UiTheme.controlScale
            hasNewAlarms: (typeof alarmStore !== "undefined" && alarmStore) ? alarmStore.hasActiveAlarm : false
        }
    }


}
