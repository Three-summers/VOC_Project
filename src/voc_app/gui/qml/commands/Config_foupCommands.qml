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
    readonly property int channelCount: (acquisitionController && acquisitionController.channelCount) ? acquisitionController.channelCount : 1
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
        text: "配置通道参数"
        width: parent.width
        onClicked: limitDialog.openWithChannel(0)
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

    // 弹窗配置 OOC/OOS/Target（按通道）
    Components.DataInputDialog {
        id: limitDialog
        title: "配置通道参数"
        popupAnchorItem: informationPanelRef ? informationPanelRef : Qt.application.activeWindow
        property int selectedChannel: 0
        property real tempOOCUpper: 80
        property real tempOOCLower: 20
        property real tempOOSUpper: 90
        property real tempOOSLower: 10
        property real tempTarget: 50
        property var oosUpperFieldRef: null
        property var oosLowerFieldRef: null
        property var oocUpperFieldRef: null
        property var oocLowerFieldRef: null
        property var targetFieldRef: null

        function loadChannel(index) {
            selectedChannel = Math.max(0, index || 0);
            // 从后端获取配置
            if (acquisitionController) {
                tempOOCUpper = acquisitionController.getOocUpper(selectedChannel);
                tempOOCLower = acquisitionController.getOocLower(selectedChannel);
                tempOOSUpper = acquisitionController.getOosUpper(selectedChannel);
                tempOOSLower = acquisitionController.getOosLower(selectedChannel);
                tempTarget = acquisitionController.getTarget(selectedChannel);
            } else {
                tempOOCUpper = 80; tempOOCLower = 20; tempOOSUpper = 90; tempOOSLower = 10; tempTarget = 50;
            }
            setFieldTexts();
        }

        function openWithChannel(index) {
            loadChannel(index);
            limitDialog.open();
        }

        function setFieldTexts() {
            if (oosUpperFieldRef) oosUpperFieldRef.text = tempOOSUpper.toString();
            if (oosLowerFieldRef) oosLowerFieldRef.text = tempOOSLower.toString();
            if (oocUpperFieldRef) oocUpperFieldRef.text = tempOOCUpper.toString();
            if (oocLowerFieldRef) oocLowerFieldRef.text = tempOOCLower.toString();
            if (targetFieldRef) targetFieldRef.text = tempTarget.toString();
        }

        function parseOrKeep(currentValue, textValue) {
            if (textValue === "" || textValue === null || typeof textValue === "undefined")
                return currentValue;
            var parsed = parseFloat(textValue);
            return isNaN(parsed) ? currentValue : parsed;
        }

        contentData: Component {
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Components.UiTheme.spacing("md")
                spacing: Components.UiTheme.spacing("sm")

                Text {
                    text: "设置指定通道的 OOC/OOS 上下界与 Target"
                    color: Components.UiTheme.color("textPrimary")
                    font.pixelSize: Components.UiTheme.fontSize("body")
                    wrapMode: Text.WordWrap
                }

                // 统一的表单行，保持左对齐与统一高度
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Components.UiTheme.spacing("sm")

                    // 通道选择
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Components.UiTheme.spacing("md")
                        Label {
                            text: "通道"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                            Layout.preferredWidth: 72
                        }
                        ComboBox {
                            id: channelSelector
                            Layout.fillWidth: true
                            Layout.preferredHeight: Components.UiTheme.controlHeight("input")
                            model: Math.max(1, channelCount)
                            padding: Components.UiTheme.spacing("xs")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                            contentItem: Text {
                                text: channelSelector.displayText
                                verticalAlignment: Text.AlignVCenter
                                color: Components.UiTheme.color("textPrimary")
                                font.pixelSize: Components.UiTheme.fontSize("body")
                                leftPadding: Components.UiTheme.spacing("sm")
                            }
                            indicator: Rectangle {
                                width: Components.UiTheme.spacing("md")
                                height: Components.UiTheme.spacing("md")
                                radius: Components.UiTheme.radius("sm")
                                color: "transparent"
                                border.color: "transparent"
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.right: parent.right
                                anchors.rightMargin: Components.UiTheme.spacing("sm")
                                Canvas {
                                    anchors.fill: parent
                                    onPaint: {
                                        var ctx = getContext("2d");
                                        ctx.strokeStyle = Components.UiTheme.color("textSecondary");
                                        ctx.lineWidth = 1.5;
                                        ctx.beginPath();
                                        ctx.moveTo(width * 0.2, height * 0.4);
                                        ctx.lineTo(width * 0.5, height * 0.7);
                                        ctx.lineTo(width * 0.8, height * 0.4);
                                        ctx.stroke();
                                    }
                                }
                            }
                            background: Rectangle {
                                color: Components.UiTheme.color("surface")
                                border.color: Components.UiTheme.color("outline")
                                radius: Components.UiTheme.radius("sm")
                            }
                            delegate: ItemDelegate {
                                text: "通道 " + index
                                width: parent ? parent.width : undefined
                                font.pixelSize: Components.UiTheme.fontSize("body")
                                background: Rectangle {
                                    color: pressed ? Components.UiTheme.color("panelAlt") : Components.UiTheme.color("surface")
                                    border.color: Components.UiTheme.color("outline")
                                }
                                onClicked: function() {
                                    channelSelector.currentIndex = index;
                                    limitDialog.loadChannel(index);
                                    channelSelector.popup.close();
                                }
                            }
                            onActivated: function(i) { limitDialog.loadChannel(i); }
                        }
                    }

                    // OOS 上
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Components.UiTheme.spacing("md")
                        Label {
                            text: "OOS 上"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                            Layout.preferredWidth: 72
                        }
                    TextField {
                        id: oosUpperField
                        Layout.fillWidth: true
                        Layout.preferredHeight: Components.UiTheme.controlHeight("input")
                        validator: DoubleValidator { bottom: -999999; top: 999999 }
                            color: Components.UiTheme.color("textPrimary")
                            placeholderText: "例如 90"
                        placeholderTextColor: Components.UiTheme.color("textSecondary")
                        background: Rectangle { color: Components.UiTheme.color("surface"); border.color: Components.UiTheme.color("outline"); radius: Components.UiTheme.radius("sm") }
                        onEditingFinished: limitDialog.tempOOSUpper = limitDialog.parseOrKeep(limitDialog.tempOOSUpper, text)
                        Component.onCompleted: {
                            limitDialog.oosUpperFieldRef = oosUpperField;
                            limitDialog.setFieldTexts();
                        }
                    }
                    }

                    // OOS 下
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Components.UiTheme.spacing("md")
                        Label {
                            text: "OOS 下"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                            Layout.preferredWidth: 72
                        }
                        TextField {
                            id: oosLowerField
                            Layout.fillWidth: true
                            Layout.preferredHeight: Components.UiTheme.controlHeight("input")
                            validator: DoubleValidator { bottom: -999999; top: 999999 }
                            color: Components.UiTheme.color("textPrimary")
                        placeholderText: "例如 10"
                        placeholderTextColor: Components.UiTheme.color("textSecondary")
                        background: Rectangle { color: Components.UiTheme.color("surface"); border.color: Components.UiTheme.color("outline"); radius: Components.UiTheme.radius("sm") }
                        onEditingFinished: limitDialog.tempOOSLower = limitDialog.parseOrKeep(limitDialog.tempOOSLower, text)
                        Component.onCompleted: {
                            limitDialog.oosLowerFieldRef = oosLowerField;
                            limitDialog.setFieldTexts();
                        }
                    }
                    }

                    // OOC 上
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Components.UiTheme.spacing("md")
                        Label {
                            text: "OOC 上"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                            Layout.preferredWidth: 72
                        }
                        TextField {
                            id: oocUpperField
                            Layout.fillWidth: true
                            Layout.preferredHeight: Components.UiTheme.controlHeight("input")
                            validator: DoubleValidator { bottom: -999999; top: 999999 }
                            color: Components.UiTheme.color("textPrimary")
                        placeholderText: "例如 80"
                        placeholderTextColor: Components.UiTheme.color("textSecondary")
                        background: Rectangle { color: Components.UiTheme.color("surface"); border.color: Components.UiTheme.color("outline"); radius: Components.UiTheme.radius("sm") }
                        onEditingFinished: limitDialog.tempOOCUpper = limitDialog.parseOrKeep(limitDialog.tempOOCUpper, text)
                        Component.onCompleted: {
                            limitDialog.oocUpperFieldRef = oocUpperField;
                            limitDialog.setFieldTexts();
                        }
                    }
                    }

                    // OOC 下
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Components.UiTheme.spacing("md")
                        Label {
                            text: "OOC 下"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                            Layout.preferredWidth: 72
                        }
                        TextField {
                            id: oocLowerField
                            Layout.fillWidth: true
                            Layout.preferredHeight: Components.UiTheme.controlHeight("input")
                            validator: DoubleValidator { bottom: -999999; top: 999999 }
                            color: Components.UiTheme.color("textPrimary")
                        placeholderText: "例如 20"
                        placeholderTextColor: Components.UiTheme.color("textSecondary")
                        background: Rectangle { color: Components.UiTheme.color("surface"); border.color: Components.UiTheme.color("outline"); radius: Components.UiTheme.radius("sm") }
                        onEditingFinished: limitDialog.tempOOCLower = limitDialog.parseOrKeep(limitDialog.tempOOCLower, text)
                        Component.onCompleted: {
                            limitDialog.oocLowerFieldRef = oocLowerField;
                            limitDialog.setFieldTexts();
                        }
                    }
                    }

                    // Target
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Components.UiTheme.spacing("md")
                        Label {
                            text: "Target"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                            Layout.preferredWidth: 72
                        }
                        TextField {
                            id: targetField
                            Layout.fillWidth: true
                            Layout.preferredHeight: Components.UiTheme.controlHeight("input")
                            validator: DoubleValidator { bottom: -999999; top: 999999 }
                            color: Components.UiTheme.color("textPrimary")
                        placeholderText: "例如 50"
                        placeholderTextColor: Components.UiTheme.color("textSecondary")
                        background: Rectangle { color: Components.UiTheme.color("surface"); border.color: Components.UiTheme.color("outline"); radius: Components.UiTheme.radius("sm") }
                        onEditingFinished: limitDialog.tempTarget = limitDialog.parseOrKeep(limitDialog.tempTarget, text)
                        Component.onCompleted: {
                            limitDialog.targetFieldRef = targetField;
                            limitDialog.setFieldTexts();
                        }
                    }
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
                        // 保存到后端（持久化）
                        if (acquisitionController) {
                            acquisitionController.setChannelLimits(
                                limitDialog.selectedChannel,
                                !isNaN(limitDialog.tempOOCUpper) ? limitDialog.tempOOCUpper : 80,
                                !isNaN(limitDialog.tempOOCLower) ? limitDialog.tempOOCLower : 20,
                                !isNaN(limitDialog.tempOOSUpper) ? limitDialog.tempOOSUpper : 90,
                                !isNaN(limitDialog.tempOOSLower) ? limitDialog.tempOOSLower : 10,
                                !isNaN(limitDialog.tempTarget) ? limitDialog.tempTarget : 50
                            );
                        }
                        limitDialog.close();
                    }
                }
                Item { Layout.fillWidth: true }
            }
        }

        onOpened: {
            loadChannel(selectedChannel);
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
