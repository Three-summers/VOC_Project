import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../../components" as Components

Item {
    id: root

    FolderDialog {
        id: folderDialog

        title: "选择待机媒体目录"
        onAccepted: standbyMediaController.setMediaDirectory(selectedFolder.toString())
    }

    Connections {
        target: standbyMediaController

        function onSettingsChanged() {
            timeoutField.text = String(standbyMediaController.idleTimeoutSeconds)
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
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Components.UiTheme.spacing("md")

                Text {
                    text: "媒体目录"
                    color: Components.UiTheme.color("textPrimary")
                }

                Text {
                    Layout.fillWidth: true
                    text: standbyMediaController.mediaDirectory || "尚未选择"
                    elide: Text.ElideMiddle
                    color: Components.UiTheme.color("textSecondary")
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
                }

                TextField {
                    id: timeoutField

                    Layout.preferredWidth: 180
                    text: String(standbyMediaController.idleTimeoutSeconds)
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: IntValidator {
                        bottom: 1
                        top: 2147483647
                    }
                    onEditingFinished: {
                        if (acceptableInput)
                            standbyMediaController.setIdleTimeoutSeconds(Number(text))
                        else
                            text = String(standbyMediaController.idleTimeoutSeconds)
                    }
                }

                Text {
                    text: "秒"
                    color: Components.UiTheme.color("textSecondary")
                }
            }

            Text {
                Layout.fillWidth: true
                text: standbyMediaController.statusMessage
                wrapMode: Text.WordWrap
                color: standbyMediaController.mediaCount > 0
                    ? Components.UiTheme.color("accentSuccess")
                    : Components.UiTheme.color("accentWarning")
            }

            Item {
                Layout.fillHeight: true
            }
        }
    }
}
