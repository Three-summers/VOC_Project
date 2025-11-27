import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "./components"
import "./components" as Components

Rectangle {
    id: titlePanel
    color: Components.UiTheme.color("surface")
    implicitHeight: Components.UiTheme.controlHeight("titleBar")  // 高度随缩放因子变化
    objectName: "title_message"

    property alias currentViewName: viewName.text
    property alias systemMessage: messageText.text
    property bool isLoggedIn: false
    property string loggedInUser: ""
    property real scaleFactor: Components.UiTheme.controlScale
    property var alarmStoreRef: null
    property var alarmPopupAnchorItem: null
    readonly property bool hasActiveAlarm: alarmStoreRef && alarmStoreRef.hasActiveAlarm
    readonly property int alarmItemCount: (alarmStoreRef && alarmStoreRef.alarmModel && alarmStoreRef.alarmModel.count !== undefined)
        ? alarmStoreRef.alarmModel.count
        : 0

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
                color: Components.UiTheme.color("textSecondary")
                font.pixelSize: Components.UiTheme.fontSize("caption")
                Layout.leftMargin: Components.UiTheme.spacing("md")
                Layout.alignment: Qt.AlignVCenter
                visible: false // 默认隐藏，未来根据实际通信状态显示
            }

            // 基础信息 - 日期/时间显示
            Frame {
                background: Rectangle {
                    color: Components.UiTheme.color("panel")
                    radius: Components.UiTheme.radius("md")
                    border.color: Components.UiTheme.color("outline")
                }
                padding: Components.UiTheme.spacing("md")
                Text {
                    id: dateTime
                    color: Components.UiTheme.color("textPrimary")
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
                background: Rectangle {
                    color: Components.UiTheme.color("panel")
                    radius: Components.UiTheme.radius("md")
                    border.color: Components.UiTheme.color("outline")
                }
                padding: Components.UiTheme.spacing("md")
                Text {
                    id: viewName
                    text: "Default View"
                    color: Components.UiTheme.color("textPrimary")
                    font.bold: true
                    font.pixelSize: Components.UiTheme.fontSize("title")
                    Layout.leftMargin: Components.UiTheme.spacing("lg")
                    Layout.alignment: Qt.AlignVCenter
                }
            }

            CustomButton {
                id: alarmButton
                text: titlePanel.hasActiveAlarm ? qsTr("ALARMS") : qsTr("Alarms")
                Layout.preferredWidth: Components.UiTheme.controlWidth("button")
                Layout.preferredHeight: Components.UiTheme.controlHeight("buttonThin")
                Layout.alignment: Qt.AlignVCenter
                status: titlePanel.hasActiveAlarm ? "alarm" : "normal"
                scaleFactor: titlePanel.scaleFactor
                enabled: !!titlePanel.alarmStoreRef
                onClicked: alarmPopup.open()
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
                Layout.fillWidth: true
                Layout.minimumWidth: 360 * Components.UiTheme.controlScale
                color: titlePanel.hasActiveAlarm ? Components.UiTheme.color("panelAlt") : Components.UiTheme.color("panel")
                border.color: titlePanel.hasActiveAlarm ? Components.UiTheme.color("accentAlarm") : Components.UiTheme.color("outline")
                border.width: 1
                radius: Components.UiTheme.radius("md")
                Behavior on color { ColorAnimation { duration: 200 } }
                Behavior on border.color { ColorAnimation { duration: 200 } }
                Text {
                    id: messageText
                    text: "System message area..."
                    color: titlePanel.hasActiveAlarm ? Components.UiTheme.color("accentAlarm") : Components.UiTheme.color("textSecondary")
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: Components.UiTheme.spacing("lg")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                    elide: Text.ElideRight
                    wrapMode: Text.NoWrap
                    width: parent.width - Components.UiTheme.spacing("xl")
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredWidth: Components.UiTheme.spacing("xl")
            }

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

    Popup {
        id: alarmPopup
        parent: titlePanel.alarmPopupAnchorItem ? titlePanel.alarmPopupAnchorItem : titlePanel
        modal: false
        focus: true
        y: titlePanel.alarmPopupAnchorItem ? Components.UiTheme.spacing("lg") : titlePanel.height - Components.UiTheme.spacing("sm")
        x: titlePanel.alarmPopupAnchorItem
            ? Math.max(Components.UiTheme.spacing("lg"), (parent.width - width) / 2)
            : titlePanel.width - width - Components.UiTheme.spacing("lg")
        implicitWidth: titlePanel.alarmPopupAnchorItem
            ? Math.min(parent.width * 0.9, 420 * Components.UiTheme.controlScale)
            : Math.min(titlePanel.width * 0.45, 420 * Components.UiTheme.controlScale)
        padding: Components.UiTheme.spacing("md")
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle {
            color: Components.UiTheme.color("panel")
            radius: Components.UiTheme.radius("md")
            border.color: Components.UiTheme.color("outline")
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: Components.UiTheme.spacing("md")
            Text {
                text: titlePanel.hasActiveAlarm ? qsTr("活动警报") : qsTr("没有活动警报")
                color: titlePanel.hasActiveAlarm ? Components.UiTheme.color("accentAlarm") : Components.UiTheme.color("textSecondary")
                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                font.bold: true
            }

            ListView {
                id: alarmList
                implicitHeight: Math.min(280 * Components.UiTheme.controlScale, contentHeight)
                Layout.fillWidth: true
                clip: true
                model: titlePanel.alarmStoreRef ? titlePanel.alarmStoreRef.alarmModel : null
                visible: titlePanel.hasActiveAlarm && titlePanel.alarmItemCount > 0
                delegate: Rectangle {
                    width: alarmList.width
                    height: implicitHeight
                    color: index % 2 === 0 ? Components.UiTheme.color("surface") : Components.UiTheme.color("panel")
                    implicitHeight: timestampText.implicitHeight + messageItem.implicitHeight + Components.UiTheme.spacing("md") * 2
                    Column {
                        anchors.fill: parent
                        anchors.margins: Components.UiTheme.spacing("md")
                        spacing: Components.UiTheme.spacing("xs")
                        Text {
                            id: timestampText
                            text: timestamp
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("caption")
                        }
                        Text {
                            id: messageItem
                            text: message
                            color: Components.UiTheme.color("textPrimary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            Text {
                visible: !titlePanel.hasActiveAlarm || titlePanel.alarmItemCount === 0
                text: titlePanel.hasActiveAlarm ? qsTr("暂无报警记录") : qsTr("暂无报警记录")
                color: Components.UiTheme.color("textSecondary")
                font.pixelSize: Components.UiTheme.fontSize("body")
            }

            CustomButton {
                text: qsTr("关闭")
                Layout.alignment: Qt.AlignRight
                Layout.preferredWidth: Components.UiTheme.controlWidth("button") * 0.8
                Layout.preferredHeight: Components.UiTheme.controlHeight("buttonThin")
                scaleFactor: titlePanel.scaleFactor
                onClicked: alarmPopup.close()
            }
        }
    }

    LoginDialog {
        id: loginDialog
        popupAnchorItem: titlePanel.alarmPopupAnchorItem ? titlePanel.alarmPopupAnchorItem : null
        onLoggedIn: (username) => {
            titlePanel.isLoggedIn = true;
            titlePanel.loggedInUser = username;
        }
    }
}
