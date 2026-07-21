import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../../components" as Components

Item {
    id: root
    readonly property var _standbyMediaController: (
        typeof standbyMediaController !== "undefined" && standbyMediaController
    ) ? standbyMediaController : null
    readonly property bool _hasStandbyMediaController: _standbyMediaController !== null

    FolderDialog {
        id: folderDialog

        title: "选择待机媒体目录"
        onAccepted: {
            if (root._hasStandbyMediaController)
                root._standbyMediaController.setMediaDirectory(selectedFolder.toString())
        }
    }

    Connections {
        target: root._standbyMediaController
        enabled: root._hasStandbyMediaController

        function onSettingsChanged() {
            timeoutField.text = String(root._standbyMediaController.idleTimeoutSeconds)
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: Components.UiTheme.radius(18)
        color: Components.UiTheme.color("panel")
        border.color: Components.UiTheme.color("outline")

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Components.UiTheme.spacing("xl")
            spacing: Components.UiTheme.spacing("lg")

            Text {
                text: "待机动画"
                font.pixelSize: Components.UiTheme.fontSize("title")
                font.bold: true
                color: Components.UiTheme.color("textPrimary")
            }

            Text {
                Layout.fillWidth: true
                text: "无操作达到设定秒数后，按文件名顺序静音循环播放此目录中的图片和视频。"
                wrapMode: Text.WordWrap
                color: Components.UiTheme.color("textSecondary")
                font.pixelSize: Components.UiTheme.fontSize("body")
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Components.UiTheme.spacing("md")

                Text {
                    text: "媒体目录"
                    color: Components.UiTheme.color("textPrimary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }

                Text {
                    Layout.fillWidth: true
                    text: root._hasStandbyMediaController
                        ? (root._standbyMediaController.mediaDirectory || "尚未选择")
                        : "待机媒体服务未连接"
                    elide: Text.ElideMiddle
                    color: Components.UiTheme.color("textSecondary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }

                Components.CustomButton {
                    text: "选择目录"
                    onClicked: folderDialog.open()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Components.UiTheme.spacing("md")

                Text {
                    text: "待机秒数"
                    color: Components.UiTheme.color("textPrimary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }

                TextField {
                    id: timeoutField

                    Layout.preferredWidth: 180
                    Layout.preferredHeight: Components.UiTheme.controlHeight("input")
                    text: String(root._hasStandbyMediaController
                        ? root._standbyMediaController.idleTimeoutSeconds
                        : 60)
                    inputMethodHints: Qt.ImhDigitsOnly
                    font.pixelSize: Components.UiTheme.fontSize("body")
                    validator: IntValidator {
                        bottom: 1
                        top: 2147483647
                    }
                    onEditingFinished: {
                        if (acceptableInput && root._hasStandbyMediaController)
                            root._standbyMediaController.setIdleTimeoutSeconds(Number(text))
                        else
                            text = String(root._hasStandbyMediaController
                                ? root._standbyMediaController.idleTimeoutSeconds
                                : 60)
                    }
                }

                Text {
                    text: "秒"
                    color: Components.UiTheme.color("textSecondary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }
            }

            Text {
                    Layout.fillWidth: true
                text: root._hasStandbyMediaController
                    ? root._standbyMediaController.statusMessage
                    : "待机媒体服务未连接"
                wrapMode: Text.WordWrap
                font.pixelSize: Components.UiTheme.fontSize("body")
                color: root._hasStandbyMediaController
                    && root._standbyMediaController.mediaCount > 0
                    ? Components.UiTheme.color("accentSuccess")
                    : Components.UiTheme.color("accentWarning")
            }

            Item {
                Layout.fillHeight: true
            }
        }
    }
}
