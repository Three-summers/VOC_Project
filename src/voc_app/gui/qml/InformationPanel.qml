import QtQuick
import QtQuick.Layouts
import "./components"
import "./components" as Components

Rectangle {
    id: informationPanel
    color: Components.UiTheme.color("background")

    property string currentView: "Status"
    property var csvFileManagerRef: null
    property var alarmStoreRef: null
    property alias currentViewItem: viewLoader.item
    property alias currentSubPage: subNavBar.currentKey
    property real scaleFactor: Components.UiTheme.controlScale
    property var foupLimitRef: null
    property var subNavigationConfig: ({
        "Status": [
            { key: "loadport", title: "Loadport" },
            { key: "foup", title: "FOUP" },
            { key: "spectrum", title: "频谱" }
        ],
        "Config": [
            { key: "loadport", title: "Loadport" },
            { key: "foup", title: "FOUP" },
            // { key: "theme", title: "调色" }
        ]
    })
    // 记住每个主页面的子页面选择
    property var subPageMemory: ({})

    function resolveViewSource(name) {
        const fileBase = name.endsWith("View") ? name : name + "View";
        return "views/" + fileBase + ".qml";
    }

    function propagateSubPage() {
        if (!viewLoader.item)
        return;
        if (subNavBar.currentKey && typeof viewLoader.item.currentSubPage !== "undefined")
        viewLoader.item.currentSubPage = subNavBar.currentKey;
        if (typeof viewLoader.item.onSubPageChanged === "function")
        viewLoader.item.onSubPageChanged(subNavBar.currentKey);
    }

    function updateSubNavigation() {
        const items = subNavigationConfig[currentView] || [];
        subNavBar.items = items;
        subNavBar.visible = items.length > 0;
        if (items.length > 0) {
            // 优先使用记忆的子页面，否则使用第一个
            const rememberedKey = subPageMemory[currentView];
            const defaultKey = items[0].key || items[0].title || ("tab0");
            const targetKey = rememberedKey || defaultKey;
            subNavBar.setCurrentKey(targetKey, false);
            propagateSubPage();
        } else {
            subNavBar.currentKey = "";
            propagateSubPage();
        }
    }

    function saveSubPageMemory(key) {
        if (currentView && key) {
            var newMemory = Object.assign({}, subPageMemory);
            newMemory[currentView] = key;
            subPageMemory = newMemory;
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Components.UiTheme.spacing("sm")
        spacing: Components.UiTheme.spacing("md")

        SubNavigationBar {
            id: subNavBar
            Layout.fillWidth: true
            visible: false
            scaleFactor: informationPanel.scaleFactor
            onSubPageSelected: function(key) {
                informationPanel.saveSubPageMemory(key);
                informationPanel.propagateSubPage();
            }
        }

        Loader {
            id: viewLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            source: resolveViewSource(informationPanel.currentView)

            onLoaded: {
                const needsCsvBinding = informationPanel.currentView === "FileView" || informationPanel.currentView === "DataLog";
                if (viewLoader.item && needsCsvBinding && informationPanel.csvFileManagerRef) {
                    viewLoader.item.csvFileManagerRef = informationPanel.csvFileManagerRef;
                    if (typeof viewLoader.item.triggerAutomaticSelection === "function")
                    viewLoader.item.triggerAutomaticSelection();
                }

                if (viewLoader.item && informationPanel.currentView === "Alarms" && informationPanel.alarmStoreRef) {
                    if (viewLoader.item.hasOwnProperty("alarmStore"))
                    viewLoader.item.alarmStore = informationPanel.alarmStoreRef;
                }

                if (viewLoader.item && informationPanel.scaleFactor && viewLoader.item.hasOwnProperty("scaleFactor"))
                    viewLoader.item.scaleFactor = informationPanel.scaleFactor;

                if (viewLoader.item && informationPanel.foupLimitRef && viewLoader.item.hasOwnProperty("foupLimitRef"))
                    viewLoader.item.foupLimitRef = informationPanel.foupLimitRef;

                informationPanel.propagateSubPage();
            }
        }
    }

    onCurrentViewChanged: updateSubNavigation()

    Component.onCompleted: updateSubNavigation()
    onScaleFactorChanged: {
        if (viewLoader.item && viewLoader.item.hasOwnProperty("scaleFactor"))
            viewLoader.item.scaleFactor = informationPanel.scaleFactor;
    }


}
