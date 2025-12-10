import QtQuick
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components" as Components

Column {
    id: dataLogCommands
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: 10
    spacing: 10

    property var commandPanelRef: null
    property var informationPanelRef: null
    readonly property var acquisitionController: (typeof foupAcquisition !== "undefined") ? foupAcquisition : null
    property string normalPathText: (acquisitionController && acquisitionController.normalModeRemotePath) ? acquisitionController.normalModeRemotePath : "Log"

    Connections {
        target: acquisitionController
        function onNormalModeRemotePathChanged() {
            normalPathText = acquisitionController.normalModeRemotePath
            if (remotePathField)
                remotePathField.text = normalPathText
        }
    }

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

    CustomButton {
        text: acquisitionController && acquisitionController.running ? "采集中" : "下载日志（正常模式）"
        width: parent.width
        enabled: acquisitionController && !acquisitionController.running
        status: acquisitionController && acquisitionController.running ? "processing" : "normal"
        onClicked: {
            if (!acquisitionController) {
                console.warn("foupAcquisition 未注入");
                return;
            }
            normalPathText = acquisitionController.normalModeRemotePath || "Log";
            acquisitionController.operationMode = "normal";
            acquisitionController.startAcquisition();
        }
    }
}
