pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

BaseDialog {
    id: dialog

    // 信号：当用户点击 OK 时发出
    signal accepted()

    // 内容区：可以加载任何输入控件
    // 当前只是占位符
    contentData: Component {
        Text {
            text: "Data input area..."
            anchors.centerIn: parent
        }
    }

    // 底部按钮区：OK 和 Cancel
    footerData: Component {
        RowLayout {
            anchors.fill: parent
            Item { Layout.fillWidth: true } // 弹簧
            CustomButton {
                text: "Cancel"
                onClicked: dialog.close()
            }
            CustomButton {
                id: okButton
                text: "OK"
                // 根据指南，若有必填项未完成，必须禁用
                enabled: false
                onClicked: {
                    dialog.accepted()
                    dialog.close()
                }
            }
            Item { Layout.fillWidth: true } // 弹簧
        }
    }
}
