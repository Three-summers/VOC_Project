import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components" as Components

Column {
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Components.UiTheme.spacing("md")
    spacing: Components.UiTheme.spacing("md")

    // 由 CommandPanel 注入，用于对话框定位
    property var commandPanelRef: null
    property var informationPanelRef: null
    property var foupLimitRef: null
    readonly property var acquisitionController: (typeof foupAcquisition !== "undefined") ? foupAcquisition : null
    property string ipText: (acquisitionController && acquisitionController.host) ? acquisitionController.host : ""

    Connections {
        target: acquisitionController
        function onHostChanged() {
            ipText = acquisitionController.host
        }
    }

    Text {
        text: "FOUP 采集命令"
        font.bold: true
        font.pixelSize: Components.UiTheme.fontSize("subtitle")
        color: Components.UiTheme.color("textPrimary")
        horizontalAlignment: Text.AlignHCenter
        width: parent.width
    }

    CustomButton {
        text: "配置采集 IP"
        width: parent.width
        onClicked: {
            if (!acquisitionController) {
                console.warn("foupAcquisition 未注入");
                return;
            }
            ipDialog.tempIp = acquisitionController.host || "";
            ipDialog.open();
        }
    }

    Text {
        visible: acquisitionController && acquisitionController.running
        text: "采集中，修改 IP 前请先停止采集"
        color: Components.UiTheme.color("accentWarning")
        font.pixelSize: Components.UiTheme.fontSize("caption")
        width: parent.width
        wrapMode: Text.WordWrap
    }

    CustomButton {
        text: "配置 OOC/OOS"
        width: parent.width
        onClicked: {
            const ref = foupLimitRef;
            limitDialog.tempOOC = (ref && !isNaN(ref.ooc)) ? ref.ooc : 80;
            limitDialog.tempOOS = (ref && !isNaN(ref.oos)) ? ref.oos : 90;
            limitDialog.open();
        }
    }

    CustomButton {
        text: acquisitionController && acquisitionController.running ? "采集中" : "开始采集"
        width: parent.width
        enabled: acquisitionController && !acquisitionController.running
        status: acquisitionController && acquisitionController.running ? "processing" : "normal"
        onClicked: {
            if (!acquisitionController) {
                console.warn("foupAcquisition 未注入");
                return;
            }
            acquisitionController.startAcquisition();
        }
    }

    CustomButton {
        text: "停止采集"
        width: parent.width
        enabled: acquisitionController && acquisitionController.running
        onClicked: {
            if (!acquisitionController) {
                console.warn("foupAcquisition 未注入");
                return;
            }
            acquisitionController.stopAcquisition();
        }
    }

    Text {
        text: acquisitionController ? acquisitionController.statusMessage : "采集控制器不可用"
        color: Components.UiTheme.color("textSecondary")
        font.pixelSize: Components.UiTheme.fontSize("body")
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        width: parent.width
    }

    // 弹窗配置 OOC/OOS
    Components.DataInputDialog {
        id: limitDialog
        title: "配置 FOUP OOC / OOS"
        popupAnchorItem: informationPanelRef ? informationPanelRef : Qt.application.activeWindow
        property real tempOOC: 80
        property real tempOOS: 90

        contentData: Component {
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Components.UiTheme.spacing("md")
                spacing: Components.UiTheme.spacing("md")

                Text {
                    text: "设置 FOUP 采集通道的控制/规格界限（OOC/OOS）。"
                    color: Components.UiTheme.color("textPrimary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                    wrapMode: Text.WordWrap
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Components.UiTheme.spacing("md")
                    Label {
                        text: "OOC"
                        color: Components.UiTheme.color("textSecondary")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }
                    TextField {
                        id: oocField
                        Layout.fillWidth: true
                        text: limitDialog.tempOOC.toString()
                        validator: DoubleValidator { bottom: -999999; top: 999999 }
                        color: Components.UiTheme.color("textPrimary")
                        placeholderText: "例如 80"
                        placeholderTextColor: Components.UiTheme.color("textSecondary")
                        background: Rectangle {
                            color: Components.UiTheme.color("surface")
                            border.color: Components.UiTheme.color("outline")
                            radius: Components.UiTheme.radius("sm")
                        }
                        onTextChanged: limitDialog.tempOOC = parseFloat(text)
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Components.UiTheme.spacing("md")
                    Label {
                        text: "OOS"
                        color: Components.UiTheme.color("textSecondary")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }
                    TextField {
                        id: oosField
                        Layout.fillWidth: true
                        text: limitDialog.tempOOS.toString()
                        validator: DoubleValidator { bottom: -999999; top: 999999 }
                        color: Components.UiTheme.color("textPrimary")
                        placeholderText: "例如 90"
                        placeholderTextColor: Components.UiTheme.color("textSecondary")
                        background: Rectangle {
                            color: Components.UiTheme.color("surface")
                            border.color: Components.UiTheme.color("outline")
                            radius: Components.UiTheme.radius("sm")
                        }
                        onTextChanged: limitDialog.tempOOS = parseFloat(text)
                    }
                }
            }
        }

        footerData: Component {
            RowLayout {
                anchors.fill: parent
                anchors.margins: Components.UiTheme.spacing("md")
                spacing: Components.UiTheme.spacing("md")
                Item { Layout.fillWidth: true }
                Components.CustomButton {
                    text: "取消"
                    Layout.preferredWidth: Components.UiTheme.controlWidth("button")
                    Layout.preferredHeight: Components.UiTheme.controlHeight("button")
                    onClicked: limitDialog.close()
                }
                Components.CustomButton {
                    text: "确定"
                    Layout.preferredWidth: Components.UiTheme.controlWidth("button")
                    Layout.preferredHeight: Components.UiTheme.controlHeight("button")
                    onClicked: {
                        if (foupLimitRef) {
                            const next = {
                                ooc: !isNaN(limitDialog.tempOOC) ? limitDialog.tempOOC : 80,
                                oos: !isNaN(limitDialog.tempOOS) ? limitDialog.tempOOS : 90
                            };
                            foupLimitRef.ooc = next.ooc;
                            foupLimitRef.oos = next.oos;
                        }
                        limitDialog.close();
                    }
                }
                Item { Layout.fillWidth: true }
            }
        }

        onOpened: {
            tempOOC = (foupLimitRef && !isNaN(foupLimitRef.ooc)) ? foupLimitRef.ooc : 80;
            tempOOS = (foupLimitRef && !isNaN(foupLimitRef.oos)) ? foupLimitRef.oos : 90;
        }
    }

    // 弹窗设置 IP，带确定/取消
    Components.DataInputDialog {
        id: ipDialog
        title: "设置 FOUP 采集 IP"
        // 与登录弹窗一致，优先锚定信息面板，否则退回主窗口居中
        popupAnchorItem: informationPanelRef ? informationPanelRef : Qt.application.activeWindow
        property string tempIp: ""
        property bool canEdit: acquisitionController && !acquisitionController.running

        contentData: Component {
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Components.UiTheme.spacing("md")
                spacing: Components.UiTheme.spacing("md")

                Text {
                    text: "请输入采集服务器 IP 地址"
                    color: Components.UiTheme.color("textPrimary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                    wrapMode: Text.WordWrap
                }

                TextField {
                    id: ipField
                    Layout.fillWidth: true
                    text: ipDialog.tempIp
                    placeholderText: "例如 192.168.1.8"
                    color: Components.UiTheme.color("textPrimary")
                    placeholderTextColor: Components.UiTheme.color("textSecondary")
                    background: Rectangle {
                        color: Components.UiTheme.color("surface")
                        border.color: Components.UiTheme.color("outline")
                        radius: Components.UiTheme.radius("sm")
                    }
                    onTextChanged: ipDialog.tempIp = text
                }

                Text {
                    visible: acquisitionController && acquisitionController.running
                    text: "采集中无法保存新 IP，请先停止采集再修改。"
                    color: Components.UiTheme.color("accentWarning")
                    font.pixelSize: Components.UiTheme.fontSize("caption")
                    wrapMode: Text.WordWrap
                }
            }
        }

        footerData: Component {
            RowLayout {
                anchors.fill: parent
                anchors.margins: Components.UiTheme.spacing("md")
                spacing: Components.UiTheme.spacing("md")
                Item { Layout.fillWidth: true }
                Components.CustomButton {
                    text: "取消"
                    Layout.preferredWidth: Components.UiTheme.controlWidth("button")
                    Layout.preferredHeight: Components.UiTheme.controlHeight("button")
                    onClicked: ipDialog.close()
                }
                Components.CustomButton {
                    text: "确定"
                    Layout.preferredWidth: Components.UiTheme.controlWidth("button")
                    Layout.preferredHeight: Components.UiTheme.controlHeight("button")
                    enabled: ipDialog.canEdit && ipDialog.tempIp.trim().length > 0
                    onClicked: {
                        if (!acquisitionController)
                            return;
                        const next = ipDialog.tempIp.trim();
                        if (next.length === 0)
                            return;
                        acquisitionController.host = next;
                        ipText = acquisitionController.host;
                        ipDialog.close();
                    }
                }
                Item { Layout.fillWidth: true }
            }
        }

        onOpened: tempIp = (acquisitionController && acquisitionController.host) ? acquisitionController.host : "";
    }
}
