import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "."
import "." as Components

Rectangle {
    id: subNav
    implicitHeight: Components.UiTheme.controlHeight("panelHeader")
    color: Components.UiTheme.color("panel")
    border.color: Components.UiTheme.color("outline")
    border.width: Math.max(1, Components.UiTheme.controlScale)
    radius: Components.UiTheme.radius("sm")

    property var items: []
    property string currentKey: ""
    property int _currentIndex: 0
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
        if (currentKey === actualKey && _currentIndex === actualIndex)
            return;
        _currentIndex = actualIndex;
        currentKey = actualKey;
        if (emitSignal && actualKey)
            subPageSelected(actualKey);
    }

    function resetSelection() {
        if (items && items.length > 0)
            setCurrentKey(keyForIndex(0), false);
        else
            currentKey = "";
    }

    Row {
        id: buttonRow
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        anchors.margins: Components.UiTheme.spacing("sm")
        spacing: Components.UiTheme.spacing("md")
        visible: subNav.items && subNav.items.length > 0

        Repeater {
            model: subNav.items

            delegate: Components.CustomButton {
                property string key: modelData.key || modelData.title || modelData.text || ("tab" + index)
                text: modelData.title || modelData.text || modelData.key || ("Tab " + (index + 1))
                twoState: true
                checked: subNav._currentIndex === index
                status: subNav._currentIndex === index ? "processing" : "normal"
                scaleFactor: subNav.scaleFactor
                implicitHeight: subNav.availableButtonHeight
                onClicked: subNav.setCurrentKey(key, true)
            }
        }
    }

    onItemsChanged: Qt.callLater(resetSelection)
}
