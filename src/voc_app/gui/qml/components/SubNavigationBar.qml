import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "."
import "." as Components

Rectangle {
    id: subNav
    implicitHeight: Components.UiTheme.controlHeight("panelHeader")
    color: "#f6f6f6"
    border.color: "#d5d5d5"
    border.width: Math.max(1, Components.UiTheme.controlScale)
    radius: Components.UiTheme.radius("sm")

    property var items: []
    property string currentKey: ""
    // 充当互斥锁的角色，当索引更改时调用 setCurrentKey，但是在 setCurrentKey 代码中也修改了索引，避免递归调用
    property bool _blockTabSignal: false
    property real scaleFactor: Components.UiTheme.controlScale
    readonly property real verticalPadding: Components.UiTheme.spacing("sm")
    readonly property real layoutHeight: height > 0 ? height : implicitHeight
    readonly property real availableButtonHeight: Math.max(
        Components.UiTheme.controlHeight("buttonThin"),
        Math.min(Components.UiTheme.controlHeight("button"), layoutHeight - 2 * verticalPadding)
    )
    signal subPageSelected(string key)

    function keyForIndex(idx) {
        if (!items || idx < 0 || idx >= items.length)
            return "";
        const item = items[idx];
        return item.key || item.title || item.text || ("tab" + idx);
    }

    function indexOfKey(key) {
        if (!items)
            return -1;
        for (let i = 0; i < items.length; ++i) {
            if (keyForIndex(i) === key)
                return i;
        }
        return -1;
    }

    function setCurrentKey(key, emitSignal) {
        const idx = key ? indexOfKey(key) : 0;
        const actualIndex = idx >= 0 ? idx : 0;
        const actualKey = items && items.length > 0 ? keyForIndex(actualIndex) : "";
        if (currentKey === actualKey && tabBar.currentIndex === actualIndex)
            return;
        _blockTabSignal = true;
        tabBar.currentIndex = actualIndex;
        _blockTabSignal = false;
        currentKey = actualKey;
        if (emitSignal && actualKey)
            subPageSelected(actualKey);
        if (!emitSignal && actualKey)
            Qt.callLater(function() { tabBar.currentIndex = actualIndex; });
    }

    function resetSelection() {
        if (items && items.length > 0)
            setCurrentKey(keyForIndex(0), false);
        else
            currentKey = "";
    }

    TabBar {
        id: tabBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.margins: Components.UiTheme.spacing("xs")
        height: subNav.availableButtonHeight
        spacing: Components.UiTheme.spacing("xs")
        // 只有当 items 不为空时显示
        visible: subNav.items && subNav.items.length > 0
        background: Rectangle { color: "transparent" }

        Repeater {
            model: subNav.items
            // 动态生成按钮
            delegate: TabButton {
                property string key: modelData.key || modelData.title || modelData.text || ("tab" + index)
                text: modelData.title || modelData.text || modelData.key || ("Tab " + (index + 1))
                checkable: true
                width: Math.max(120 * Components.UiTheme.controlScale, text.length * Components.UiTheme.spacing("md"))
                implicitHeight: subNav.availableButtonHeight - Components.UiTheme.spacing("xs")
                font.pixelSize: Components.UiTheme.fontSize("label")
                onClicked: subNav.setCurrentKey(key, true)
            }
        }

        onCurrentIndexChanged: {
            // 这里是防止递归调用的真正逻辑
            if (subNav._blockTabSignal)
                return;
            const key = subNav.keyForIndex(currentIndex);
            if (key)
                subNav.setCurrentKey(key, true);
        }
    }

    onItemsChanged: Qt.callLater(resetSelection)
}
