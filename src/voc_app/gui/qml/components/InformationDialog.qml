import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

BaseDialog {
    id: dialog

    property string message: ""

    // 内容区：只包含消息文本
    contentData: Component {
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 20 // Add margins to the content area
            Text {
                id: messageText
                text: dialog.message // Bind to the dialog's message property
                color: Components.UiTheme.color("textPrimary")
                wrapMode: Text.WordWrap
                anchors.centerIn: parent
            }
        }
    }

    // 底部按钮区：居中的 Close 按钮
    footerData: Component {
        RowLayout {
            anchors.fill: parent
            Item { Layout.fillWidth: true } // 弹簧
            CustomButton {
                text: "Close"
                onClicked: dialog.close()
            }
            Item { Layout.fillWidth: true } // 弹簧
        }
    }
}