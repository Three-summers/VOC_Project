import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "./components"
import "./components" as Components

Rectangle {
    id: titlePanel
    color: "#333333"
    implicitHeight: Components.UiTheme.controlHeight("titleBar")  // 高度随缩放因子变化
    objectName: "title_message"

    property alias currentViewName: viewName.text
    property alias systemMessage: messageText.text
    property bool isLoggedIn: false
    property string loggedInUser: ""
    property real scaleFactor: Components.UiTheme.controlScale

    ColumnLayout {
        anchors.fill: parent
        spacing: Components.UiTheme.spacing("sm")

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: parent.height * 0.7
            spacing: Components.UiTheme.spacing("md")

            // 主机通信状态 (条件性) - 占位符
            Text {
                text: "[HOST: REMOTE • CONNECTED]" // Placeholder
                color: "#aaaaaa"
                font.pixelSize: Components.UiTheme.fontSize("caption")
                Layout.leftMargin: Components.UiTheme.spacing("md")
                Layout.alignment: Qt.AlignVCenter
                visible: false // 默认隐藏，未来根据实际通信状态显示
            }

            // 基础信息 - 日期/时间显示
            Frame {
                Text {
                    id: dateTime
                    color: "white"
                    font.pixelSize: Components.UiTheme.fontSize("title")
                    Layout.leftMargin: Components.UiTheme.spacing("lg")
                    Layout.alignment: Qt.AlignVCenter
                }
            }

            Timer {
                interval: 1000 // 1 秒
                running: true
                repeat: true
                onTriggered: {
                    dateTime.text = Qt.formatDateTime(new Date(), "yyyy-MM-dd hh:mm:ss");
                }
            }

            // 基础信息 - 当前视图名称
            Frame {
                Text {
                    id: viewName
                    text: "Default View"
                    color: "white"
                    font.bold: true
                    font.pixelSize: Components.UiTheme.fontSize("title")
                    Layout.leftMargin: Components.UiTheme.spacing("lg")
                    Layout.alignment: Qt.AlignVCenter
                }
            }

            // 占位符，推开登录按钮
            Item { Layout.fillWidth: true }

            // 登录/登出按钮 (条件性)
            CustomButton {
                id: loginButton
                text: titlePanel.isLoggedIn ? titlePanel.loggedInUser : "Login Here"
                Layout.preferredWidth: Components.UiTheme.controlWidth("button")
                Layout.preferredHeight: Components.UiTheme.controlHeight("buttonThin")
                Layout.rightMargin: Components.UiTheme.spacing("lg")
                Layout.alignment: Qt.AlignVCenter
                scaleFactor: titlePanel.scaleFactor
                onClicked: {
                    if (titlePanel.isLoggedIn) {
                        titlePanel.isLoggedIn = false;
                        titlePanel.loggedInUser = "";
                        console.log("Logged out");
                    } else {
                        loginDialog.open();
                    }
                }
            }
        }

        // 基础信息 - 消息显示区
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: parent.height * 0.5
            spacing: 0

            Rectangle {
                id: messageArea
                Layout.fillHeight: true
                color: "#222222"
                Text {
                    id: messageText
                    text: "System message area..."
                    color: "#aaaaaa"
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: Components.UiTheme.spacing("lg")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }
            }

            Item { Layout.fillWidth: true }

            // 预留退出按钮
            CustomButton {
                text: "Quit"
                Layout.fillHeight: true
                Layout.preferredWidth: Math.max(Components.UiTheme.controlWidth("button") * 0.6, 80 * Components.UiTheme.controlScale)
                Layout.rightMargin: Components.UiTheme.spacing("lg")
                Layout.alignment: Qt.AlignVCenter
                scaleFactor: titlePanel.scaleFactor
                onClicked: Qt.quit()
            }
        }
    }

    LoginDialog {
        id: loginDialog
        onLoggedIn: (username) => {
            titlePanel.isLoggedIn = true;
            titlePanel.loggedInUser = username;
        }
    }
}
