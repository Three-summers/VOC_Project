import QtQuick
import "../components"

Column {
    id: dataLogCommands
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: 10
    spacing: 10

    property var commandPanelRef: null
    property var informationPanelRef: null

    function dataLogView() {
        if (!commandPanelRef || commandPanelRef.currentView !== "DataLog")
            return null;
        const infoPanel = commandPanelRef.informationPanelRef || informationPanelRef;
        if (!infoPanel || !infoPanel.currentViewItem)
            return null;
        return infoPanel.currentViewItem;
    }

    CustomButton {
        text: "绘图设置"
        width: parent.width
        onClicked: {
            const view = dataLogCommands.dataLogView();
            if (view && view.openPlotSettingsDialog)
                view.openPlotSettingsDialog();
        }
    }

    CustomButton {
        text: "绘图"
        width: parent.width
        onClicked: {
            const view = dataLogCommands.dataLogView();
            if (view && view.plotSelectedColumns)
                view.plotSelectedColumns();
        }
    }

    CustomButton {
        text: "关闭绘图"
        width: parent.width
        onClicked: {
            const view = dataLogCommands.dataLogView();
            if (view && view.closeCharts)
                view.closeCharts();
        }
    }

    CustomButton {
        text: "保存图片"
        width: parent.width
        onClicked: {
            const view = dataLogCommands.dataLogView();
            if (view && view.openSaveDialog)
                view.openSaveDialog();
        }
    }
}
