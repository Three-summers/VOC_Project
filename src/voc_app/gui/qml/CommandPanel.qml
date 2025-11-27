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
    property real scaleFactor: Components.UiTheme.controlScale

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
        }
    }

    function loadCommandsFor(viewName, subKey) {
        const basePath = "commands/" + viewName + "Commands.qml";
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
            component.statusChanged.connect(function(status) {
                if (status === Component.Ready) {
                    commandPanel._activeComponent = component;
                    commandLoader.source = "";
                    commandLoader.sourceComponent = component;
                } else if (status === Component.Error) {
                    console.warn("子页面命令加载失败, 回退:", candidatePath);
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