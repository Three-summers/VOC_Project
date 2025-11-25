pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "./" as Components

DataInputDialog {
    id: loginDialog
    title: "User Login"

    property bool showError: false

    // 覆盖 contentData 以包含用户名和密码字段
    contentData: Component {
        ColumnLayout {
            // 将输入字段的文本暴露为属性
            property alias username: usernameInput.text
            property alias password: passwordInput.text

            anchors.fill: parent
            anchors.margins: 20
            spacing: 10

            Label { text: "Username:" }
            TextField {
                id: usernameInput
                Layout.fillWidth: true
                placeholderText: "Enter username"
                onTextChanged: loginDialog.showError = false
            }

            Label { text: "Password:" }
            TextField {
                id: passwordInput
                Layout.fillWidth: true
                echoMode: TextInput.Password
                placeholderText: "Enter password"
                onTextChanged: loginDialog.showError = false
            }

            Text {
                text: "Invalid username or password."
                color: "red"
                visible: loginDialog.showError // Bind to root property
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    footerData: Component {
        RowLayout {
            anchors.fill: parent
            anchors.margins: Components.UiTheme.spacing("md")
            spacing: Components.UiTheme.spacing("md")
            Item { Layout.fillWidth: true } // Spacer
            CustomButton {
                text: "Cancel"
                Layout.preferredWidth: Components.UiTheme.controlWidth("button")
                Layout.preferredHeight: Components.UiTheme.controlHeight("button")
                onClicked: loginDialog.close()
            }
            CustomButton {
                text: "OK"
                Layout.preferredWidth: Components.UiTheme.controlWidth("button")
                Layout.preferredHeight: Components.UiTheme.controlHeight("button")
                // 这里之所以不直接访问 usernameInput 和 passwordInput
                // 是因为 contentData 被封装在 loginDialog 内部
                // 通过 internalContentLoader.item 访问，确保解耦
                enabled: loginDialog.internalContentLoader.item &&
                loginDialog.internalContentLoader.item.username.length > 0 &&
                loginDialog.internalContentLoader.item.password.length > 0
                onClicked: {
                    var success = authManager.login(loginDialog.internalContentLoader.item.username, loginDialog.internalContentLoader.item.password);
                    if (success) {
                        loginDialog.accepted();
                        loginDialog.close();
                    } else {
                        loginDialog.showError = true;
                    }
                }
            }
            Item { Layout.fillWidth: true } // Spacer
        }
    }

    signal loggedIn(string username)

    onAccepted: {
        loggedIn(loginDialog.internalContentLoader.item.username);
    }

    onClosed: {
        loginDialog.showError = false;
    }
}
