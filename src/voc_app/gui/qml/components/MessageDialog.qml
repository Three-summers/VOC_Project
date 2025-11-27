import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import "." as Components
import "."

BaseDialog {
    id: dialog

    // 'information', 'progress', 'attention', 'error'
    property string type: "information"
    property string message: ""
    property bool isQuestion: false // Added for explicit control of Yes/No buttons

    // 信号
    signal yesClicked()
    signal noClicked()
    signal okClicked()
    signal cancelClicked()

    function getIcon() {
        switch (type) {
            case "information": return "ℹ️";
            case "progress": return "🔄";
            case "attention": return "⚠️";
            case "error": return "❌";
            default: return "";
        }
    }

    // 内容区：图标 + 消息
    contentData: Component {
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Components.UiTheme.spacing("lg")
            spacing: Components.UiTheme.spacing("md")

            Text {
                text: getIcon()
                font.pixelSize: Components.UiTheme.fontSize("display")
                Layout.alignment: Qt.AlignVCenter
                color: Components.UiTheme.color("textPrimary")
            }
            Text {
                id: messageText
                text: dialog.message
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                font.pixelSize: Components.UiTheme.fontSize("body")
                color: Components.UiTheme.color("textPrimary")
            }
        }
    }

    // 底部按钮区：根据类型显示不同按钮
    footerData: Component {
        RowLayout {
            anchors.fill: parent
            Item { Layout.fillWidth: true } // 弹簧

            // Information / Progress -> Close
            CustomButton {
                text: "Close"
                visible: type === 'information' || type === 'progress'
                onClicked: dialog.close()
            }

            // Attention / Error (Statement) -> OK or OK/Cancel
            CustomButton {
                text: "Cancel"
                visible: (dialog.type === 'attention' || dialog.type === 'error') && !dialog.isQuestion
                onClicked: { dialog.cancelClicked(); dialog.close(); }
            }
            CustomButton {
                text: "OK"
                visible: (dialog.type === 'attention' || dialog.type === 'error') && !dialog.isQuestion
                onClicked: { dialog.okClicked(); dialog.close(); }
            }

            // Attention / Error (Question) -> Yes/No/Cancel
            CustomButton {
                text: "No"
                visible: dialog.isQuestion
                onClicked: { dialog.noClicked(); dialog.close(); }
            }
            CustomButton {
                text: "Yes"
                visible: dialog.isQuestion
                onClicked: { dialog.yesClicked(); dialog.close(); }
            }

            Item { Layout.fillWidth: true } // 弹簧
        }
    }
}