import QtQuick
import "../components"
import "../components" as Components

Column {
    id: loadportCommands
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Components.UiTheme.spacing("md")
    spacing: Components.UiTheme.spacing("md")

    property var alarmStore: null
    readonly property var actuatorController: (typeof loadportActuatorController !== "undefined") ? loadportActuatorController : null
    property string actionStatus: "待命"

    function nowString() {
        return Qt.formatDateTime(new Date(), "yyyy-MM-dd hh:mm:ss")
    }

    function reportAction(success, successText, failText) {
        actionStatus = success ? successText : failText
        if (!success && alarmStore && alarmStore.addAlarm)
            alarmStore.addAlarm(nowString(), "[ERROR] " + failText)
    }

    Connections {
        target: loadportCommands.actuatorController
        function onActionSucceeded(message) {
            loadportCommands.actionStatus = message
        }
        function onActionFailed(message) {
            loadportCommands.actionStatus = message
            if (loadportCommands.alarmStore && loadportCommands.alarmStore.addAlarm)
                loadportCommands.alarmStore.addAlarm(loadportCommands.nowString(), "[ERROR] " + message)
        }
    }

    Text {
        text: "Loadport 控制"
        font.bold: true
        font.pixelSize: Components.UiTheme.fontSize("subtitle")
        color: Components.UiTheme.color("textPrimary")
        horizontalAlignment: Text.AlignHCenter
        width: parent.width
    }

    CustomButton {
        text: "锁定"
        width: parent.width
        enabled: loadportCommands.actuatorController !== null
        onClicked: {
            const ok = loadportCommands.actuatorController.lockOnly()
            loadportCommands.reportAction(ok, "锁定完成", "锁定失败")
        }
    }

    CustomButton {
        text: "解锁"
        width: parent.width
        enabled: loadportCommands.actuatorController !== null
        onClicked: {
            const ok = loadportCommands.actuatorController.unlockOnly()
            loadportCommands.reportAction(ok, "解锁完成", "解锁失败")
        }
    }

    CustomButton {
        text: "锁机构复位"
        width: parent.width
        enabled: loadportCommands.actuatorController !== null
        onClicked: {
            const ok = loadportCommands.actuatorController.lockReset()
            loadportCommands.reportAction(ok, "锁机构复位完成", "锁机构复位失败")
        }
    }

    CustomButton {
        text: "对插机构复位"
        width: parent.width
        enabled: loadportCommands.actuatorController !== null
        onClicked: {
            const ok = loadportCommands.actuatorController.insertReset()
            loadportCommands.reportAction(ok, "对插机构复位完成", "对插机构复位失败")
        }
    }

    CustomButton {
        text: "对插"
        width: parent.width
        enabled: loadportCommands.actuatorController !== null
        onClicked: {
            const ok = loadportCommands.actuatorController.insertForLoad()
            loadportCommands.reportAction(ok, "对插完成 step4", "对插失败")
        }
    }

    CustomButton {
        text: "取消对插"
        width: parent.width
        enabled: loadportCommands.actuatorController !== null
        onClicked: {
            const ok = loadportCommands.actuatorController.insertForUnload()
            loadportCommands.reportAction(ok, "取消对插完成 step8", "取消对插失败")
        }
    }

    CustomButton {
        text: "Load"
        width: parent.width
        enabled: loadportCommands.actuatorController !== null
        onClicked: {
            const ok = loadportCommands.actuatorController.lockForLoad()
            loadportCommands.reportAction(ok, "Load 组合动作完成", "Load 组合动作失败")
        }
    }

    CustomButton {
        text: "Unload"
        width: parent.width
        enabled: loadportCommands.actuatorController !== null
        onClicked: {
            const ok = loadportCommands.actuatorController.unlockForUnload()
            loadportCommands.reportAction(ok, "Unload 组合动作完成", "Unload 组合动作失败")
        }
    }

    CustomButton {
        text: "故障复位"
        width: parent.width
        enabled: loadportCommands.actuatorController !== null
        onClicked: {
            const ok = loadportCommands.actuatorController.recoverE84FromError()
            loadportCommands.reportAction(ok, "已发送故障复位请求", "故障复位请求失败")
        }
    }
}
