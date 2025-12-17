import QtQuick
import QtQuick.Layouts
import "./components"
import "./components" as Components

Rectangle {
    id: commandPanel
    color: Components.UiTheme.color("panelAlt")

    property string currentView: "Jobs" // 由 main.qml 绑定
    property var informationPanelRef: null
    property var alarmStoreRef: null
    property string currentSubPage: ""
    property Component _activeComponent: null
    property Component _pendingComponent: null  // 追踪异步加载中的组件
    property real scaleFactor: Components.UiTheme.controlScale
    property var foupLimitRef: null

    // 清理待加载的组件，避免内存泄漏
    function _cleanupPendingComponent() {
        if (_pendingComponent) {
            _pendingComponent.destroy();
            _pendingComponent = null;
        }
    }

    Loader {
        id: commandLoader
        anchors.fill: parent
        onLoaded: {
            if (!commandLoader.item)
                return;
            if (commandLoader.item.hasOwnProperty("commandPanelRef"))
                commandLoader.item.commandPanelRef = commandPanel;
            if (commandLoader.item.hasOwnProperty("informationPanelRef"))
                commandLoader.item.informationPanelRef = commandPanel.informationPanelRef;
            if (commandLoader.item.hasOwnProperty("alarmStore"))
                commandLoader.item.alarmStore = commandPanel.alarmStoreRef;
            if (commandLoader.item.hasOwnProperty("subPageKey"))
                commandLoader.item.subPageKey = commandPanel.currentSubPage;
            if (commandLoader.item.hasOwnProperty("scaleFactor"))
                commandLoader.item.scaleFactor = commandPanel.scaleFactor;
            if (commandLoader.item.hasOwnProperty("foupLimitRef"))
                commandLoader.item.foupLimitRef = commandPanel.foupLimitRef;
        }
    }

    function loadCommandsFor(viewName, subKey) {
        const basePath = "commands/" + viewName + "Commands.qml";

        // 清理之前未完成的异步加载
        _cleanupPendingComponent();

        commandPanel._activeComponent = null;
        commandLoader.sourceComponent = null;
        commandLoader.source = "";
        const subCommandViews = ["Status", "Config"];
        const supportsSubCommands = subCommandViews.indexOf(viewName) !== -1;
        if (!subKey || !supportsSubCommands) {
            commandLoader.setSource(basePath);
            return;
        }

        const candidatePath = "commands/" + viewName + "_" + subKey + "Commands.qml";
        const component = Qt.createComponent(candidatePath);
        if (component.status === Component.Ready) {
            commandPanel._activeComponent = component;
            commandLoader.source = "";
            commandLoader.sourceComponent = component;
        } else if (component.status === Component.Error) {
            console.warn("子页面命令不存在, 回退:", candidatePath);
            component.destroy();
            commandPanel._activeComponent = null;
            commandLoader.sourceComponent = null;
            commandLoader.setSource(basePath);
        } else {
            // 异步加载：保存引用以便后续清理
            _pendingComponent = component;
            component.statusChanged.connect(function(status) {
                // 检查是否仍是当前待加载的组件（避免处理已被清理的旧组件）
                if (component !== _pendingComponent) {
                    return;
                }
                if (status === Component.Ready) {
                    _pendingComponent = null;
                    commandPanel._activeComponent = component;
                    commandLoader.source = "";
                    commandLoader.sourceComponent = component;
                } else if (status === Component.Error) {
                    console.warn("子页面命令加载失败, 回退:", candidatePath);
                    _pendingComponent = null;
                    component.destroy();
                    commandPanel._activeComponent = null;
                    commandLoader.sourceComponent = null;
                    commandLoader.setSource(basePath);
                }
            });
        }
    }

    onCurrentViewChanged: loadCommandsFor(currentView, currentSubPage)
    onCurrentSubPageChanged: loadCommandsFor(currentView, currentSubPage)
    Component.onCompleted: loadCommandsFor(currentView, currentSubPage)
    onScaleFactorChanged: {
        if (commandLoader.item && commandLoader.item.hasOwnProperty("scaleFactor"))
            commandLoader.item.scaleFactor = commandPanel.scaleFactor;
    }
}
