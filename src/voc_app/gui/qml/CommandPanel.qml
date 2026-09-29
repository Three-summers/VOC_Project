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

    // 登录门控：未登录时整块命令面板不可点击（状态由 Python 侧 authManager 持有）
    readonly property bool authenticated: (typeof authManager !== "undefined" && authManager)
        ? authManager.isAuthenticated
        : false

    // 清理待加载的组件，避免内存泄漏
    function _cleanupPendingComponent() {
        if (_pendingComponent) {
            _pendingComponent.destroy();
            _pendingComponent = null;
        }
    }

    // 命令区可滚动：按钮多于可视高度时（例如 Loadport 的 9 个按钮）仍能滚到
    // 最后一个，避免"故障复位"这类关键操作被底部导航挡住而不可点击（R09）。
    ScrollView {
        id: commandScroll
        objectName: "command_panel_scroll"
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth
        // 未登录时不渲染命令内容、也不接受输入：提示与命令二选一显示，
        // 这样提示文字不会浮在按钮文字上层造成重叠。
        visible: commandPanel.authenticated
        enabled: commandPanel.authenticated

        Loader {
            id: commandLoader
            objectName: "command_panel_loader"
            width: commandScroll.availableWidth
            enabled: commandPanel.authenticated
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

    // 未登录占位：整块面板居中提示（与命令内容互斥显示，不会重叠）
    Item {
        objectName: "command_panel_login_placeholder"
        anchors.fill: parent
        visible: !commandPanel.authenticated

        Column {
            objectName: "command_panel_login_placeholder_column"
            anchors.centerIn: parent
            width: parent.width - Components.UiTheme.spacing("lg") * 2
            spacing: Components.UiTheme.spacing("sm")

            Text {
                objectName: "command_panel_login_hint"
                width: parent.width
                text: "请先登录后再操作"
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                color: Components.UiTheme.color("textPrimary")
                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                font.bold: true
            }

            Text {
                width: parent.width
                text: "登录后可使用本页命令"
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                color: Components.UiTheme.color("textSecondary")
                font.pixelSize: Components.UiTheme.fontSize("body")
            }
        }
    }
}
