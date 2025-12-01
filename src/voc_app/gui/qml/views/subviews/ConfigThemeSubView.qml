import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../components" as Components

Item {
    id: rootItem // Changed from parent Item to rootItem to avoid conflict and be more explicit
    anchors.fill: parent

    // 颜色角色数据模型（按功能分组）
    readonly property var colorRoleModel: [
        { key: "background", label: "背景", category: "基础色" },
        { key: "surface", label: "表面", category: "基础色" },
        { key: "panel", label: "面板", category: "基础色" },
        { key: "panelAlt", label: "面板(替代)", category: "基础色" },
        { key: "outline", label: "边框", category: "基础色" },
        { key: "outlineStrong", label: "边框(强)", category: "基础色" },
        { key: "buttonBase", label: "按钮基础", category: "按钮色" },
        { key: "buttonHover", label: "按钮悬停", category: "按钮色" },
        { key: "buttonDown", label: "按钮按下", category: "按钮色" },
        { key: "textPrimary", label: "文本主色", category: "文本色" },
        { key: "textSecondary", label: "文本次色", category: "文本色" },
        { key: "textOnLight", label: "亮底文本", category: "文本色" },
        { key: "textOnLightMuted", label: "亮底柔和", category: "文本色" },
        { key: "accentInfo", label: "信息", category: "强调色" },
        { key: "accentSuccess", label: "成功", category: "强调色" },
        { key: "accentWarning", label: "警告", category: "强调色" },
        { key: "accentAlarm", label: "报警", category: "强调色" }
    ]

    // 当前选择的颜色角色key
    property string currentRoleKey: ""

    // 更新调色板颜色的辅助函数（使用克隆机制触发属性绑定）
    function updatePaletteColor(roleKey, colorValue) {
        const next = JSON.parse(JSON.stringify(Components.UiTheme.palette))
        next[roleKey] = colorValue.toString()
        Components.UiTheme.palette = next
    }

    // 颜色选择对话框
    ColorDialog {
        id: colorDialog
        title: "选择颜色"
        onAccepted: {
            if (currentRoleKey !== "") {
                updatePaletteColor(currentRoleKey, selectedColor)
            }
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
            spacing: Components.UiTheme.spacing("md")

            // 标题区域
            RowLayout {
                Layout.fillWidth: true
                spacing: Components.UiTheme.spacing("lg")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Components.UiTheme.spacing("xs")

                    Text {
                        text: "主题调色板"
                        font.pixelSize: Components.UiTheme.fontSize("title")
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    Text {
                        text: "点击卡片实时调整UI组件颜色，修改立即生效"
                        color: Components.UiTheme.color("textSecondary")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }
                }
            }

            // 颜色卡片网格容器
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth

                GridLayout {
                    width: parent.width
                    columns: Math.floor(width / 300)
                    rowSpacing: Components.UiTheme.spacing("md")
                    columnSpacing: Components.UiTheme.spacing("md")

                    // 生成17个颜色卡片
                    Repeater {
                        model: colorRoleModel

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 80
                            Layout.minimumWidth: 280
                            Layout.maximumWidth: 400
                            radius: Components.UiTheme.radius("md")
                            color: Components.UiTheme.color("surface")
                            border.width: 1

                            // 鼠标悬停效果
                            property bool hovered: false

                            // 悬停时边框高亮
                            border.color: hovered ? Components.UiTheme.color("accentInfo") : Components.UiTheme.color("outline")

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onEntered: parent.hovered = true
                                onExited: parent.hovered = false
                                onClicked: {
                                    currentRoleKey = modelData.key
                                    colorDialog.selectedColor = Components.UiTheme.palette[modelData.key]
                                    colorDialog.open()
                                }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: Components.UiTheme.spacing("md")
                                spacing: Components.UiTheme.spacing("md")

                                // 左侧：颜色预览（更大更醒目）
                                Rectangle {
                                    Layout.preferredWidth: 70
                                    Layout.fillHeight: true
                                    radius: Components.UiTheme.radius("sm")
                                    color: Components.UiTheme.palette[modelData.key]
                                    border.color: Components.UiTheme.color("outline")
                                    border.width: 2

                                    // 内部边框效果
                                    Rectangle {
                                        anchors.fill: parent
                                        anchors.margins: 4
                                        radius: parent.radius - 2
                                        color: "transparent"
                                        border.color: Qt.rgba(1, 1, 1, 0.1)
                                        border.width: 1
                                    }
                                }

                                // 右侧：信息区域
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    spacing: Components.UiTheme.spacing("xxs")

                                    // 分类标签
                                    Text {
                                        text: modelData.category
                                        font.pixelSize: Components.UiTheme.fontSize("caption")
                                        color: Components.UiTheme.color("accentInfo")
                                        opacity: 0.8
                                    }

                                    // 颜色名称
                                    Text {
                                        text: modelData.label
                                        font.pixelSize: Components.UiTheme.fontSize("body")
                                        font.bold: true
                                        color: Components.UiTheme.color("textPrimary")
                                    }

                                    // 颜色值（带复制提示）
                                    RowLayout {
                                        spacing: Components.UiTheme.spacing("xs")

                                        Text {
                                            text: Components.UiTheme.palette[modelData.key].toString()
                                            font.pixelSize: Components.UiTheme.fontSize("label")
                                            font.family: "monospace"
                                            color: Components.UiTheme.color("textSecondary")
                                        }

                                        Text {
                                            text: "●"
                                            font.pixelSize: Components.UiTheme.fontSize("caption")
                                            color: Components.UiTheme.palette[modelData.key]
                                        }
                                    }

                                    // Key标识（开发用）
                                    Text {
                                        text: "key: " + modelData.key
                                        font.pixelSize: Components.UiTheme.fontSize("caption")
                                        font.family: "monospace"
                                        color: Components.UiTheme.color("textSecondary")
                                        opacity: 0.5
                                    }
                                }

                                // 右侧：选色图标
                                Rectangle {
                                    Layout.preferredWidth: 40
                                    Layout.preferredHeight: 40
                                    radius: 20
                                    color: parent.parent.hovered ? Components.UiTheme.color("buttonHover") : Components.UiTheme.color("buttonBase")
                                    border.color: Components.UiTheme.color("outline")

                                    Text {
                                        anchors.centerIn: parent
                                        text: "🎨"
                                        font.pixelSize: Components.UiTheme.fontSize("title")
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
