import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"
import "../components" as Components

Rectangle {
    id: configView
    color: Components.UiTheme.color("background")

    property string currentSubPage: "loadport"
    property real scaleFactor: Components.UiTheme.controlScale
    property var loadportInfo: ({
        ipAddress: "192.168.0.100",
        deviceTime: Qt.formatDateTime(new Date(), "yyyy-MM-dd hh:mm:ss")
    })
    property var foupInfo: ({
        syncTime: Qt.formatDateTime(new Date(), "yyyy-MM-dd hh:mm:ss"),
        acquisitionStatus: "采集中"
    })
    readonly property int foupChartIndex: 2
    property var foupLimitRef: null

    function chartEntry(rowIndex, fallbackTitle) {
        const fallback = {
            title: fallbackTitle || "",
            seriesModel: null,
            xColumn: 0,
            yColumn: 1
        };
        if (typeof chartListModel === "undefined" || !chartListModel || typeof chartListModel.get !== "function")
        return fallback;
        const entry = chartListModel.get(rowIndex);
        if (!entry || Object.keys(entry).length === 0)
        return fallback;
        return {
            title: entry.title || fallback.title,
            seriesModel: entry.seriesModel || null,
            xColumn: typeof entry.xColumn === "number" ? entry.xColumn : 0,
            yColumn: typeof entry.yColumn === "number" ? entry.yColumn : 1
        };
    }

    function displayValue(value) {
        if (value === null || typeof value === "undefined" || value === "")
        return "--";
        return value;
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Components.UiTheme.spacing("xl")
        spacing: Components.UiTheme.spacing("lg")

        Loader {
            id: contentLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceComponent: {
                if (currentSubPage === "theme") return themeComponent
                if (currentSubPage === "foup") return foupComponent
                return loadportComponent
            }
        }
    }

    Component {
        id: loadportComponent

        Item {
            anchors.fill: parent

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
                        text: "Loadport 配置"
                        font.pixelSize: Components.UiTheme.fontSize("title")
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    Text {
                        text: "当前通信参数"
                        color: Components.UiTheme.color("textSecondary")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        rowSpacing: Components.UiTheme.spacing("md")
                        columnSpacing: Components.UiTheme.spacing("lg")

                        Text {
                            text: "IP 地址"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }

                        Text {
                            text: configView.displayValue(configView.loadportInfo.ipAddress)
                            font.pixelSize: Components.UiTheme.fontSize("subtitle")
                            font.bold: true
                            color: Components.UiTheme.color("textPrimary")
                        }

                        Text {
                            text: "设备时间"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }

                        Text {
                            text: configView.displayValue(configView.loadportInfo.deviceTime)
                            font.pixelSize: Components.UiTheme.fontSize("subtitle")
                            font.bold: true
                            color: Components.UiTheme.color("textPrimary")
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Components.UiTheme.radius(14)
                        color: Components.UiTheme.color("surface")
                        border.color: Components.UiTheme.color("outlineStrong")

                        Text {
                            anchors.centerIn: parent
                            text: "待接入实时 loadport 数据"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }
                    }
                }
            }
        }
    }

    Component {
        id: foupComponent

        Item {
            anchors.fill: parent

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
                        text: "FOUP 配置"
                        font.pixelSize: Components.UiTheme.fontSize("title")
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    Text {
                        text: "当前时间及采集通道状态"
                        color: Components.UiTheme.color("textSecondary")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        rowSpacing: Components.UiTheme.spacing("md")
                        columnSpacing: Components.UiTheme.spacing("lg")

                        Text {
                            text: "同步时间"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }

                        Text {
                            text: configView.displayValue(configView.foupInfo.syncTime)
                            font.pixelSize: Components.UiTheme.fontSize("subtitle")
                            font.bold: true
                            color: Components.UiTheme.color("textPrimary")
                        }

                        Text {
                            text: "采集状态"
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }

                        RowLayout {
                            spacing: Components.UiTheme.spacing("sm")

                            Rectangle {
                                width: Components.UiTheme.spacing("lg")
                                height: Components.UiTheme.spacing("lg")
                                radius: Components.UiTheme.radius("pill")
                                color: (typeof foupAcquisition !== "undefined" && foupAcquisition && foupAcquisition.running)
                                ? Components.UiTheme.color("accentSuccess")
                                : Components.UiTheme.color("accentAlarm")
                            }

                            Text {
                                text: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                ? foupAcquisition.statusMessage
                                : configView.displayValue(configView.foupInfo.acquisitionStatus)
                                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                                font.bold: true
                                color: Components.UiTheme.color("textPrimary")
                            }
                        }
                    }

                    // 动态图表容器（固定两列布局）
                    GridLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columns: 2
                        rowSpacing: Components.UiTheme.spacing("md")
                        columnSpacing: Components.UiTheme.spacing("md")

                        // 动态生成图表
                        Repeater {
                            id: chartRepeater
                            model: {
                                // 根据foupAcquisition.channelCount动态生成图表列表
                                // 至少显示1个图表，防止采集前布局空白
                                if (typeof foupAcquisition === "undefined" || !foupAcquisition) {
                                    return [{ title: "FOUP 通道 1", index: configView.foupChartIndex, channelIndex: 0 }]
                                }
                                const count = Math.max(1, foupAcquisition.channelCount)
                                const charts = []
                                for (let i = 0; i < count; i++) {
                                    charts.push({
                                        title: "FOUP 通道 " + (i + 1),
                                        index: configView.foupChartIndex + i,
                                        channelIndex: i
                                    })
                                }
                                return charts
                            }

                            delegate: Components.ChartCard {
                                id: chartCard
                                // 单通道时占满两列，多通道时每个占一列
                                Layout.columnSpan: (chartRepeater.count === 1) ? 2 : 1
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.preferredHeight: Components.UiTheme.controlHeight(220)
                                Layout.minimumHeight: 180
                                radius: Components.UiTheme.radius(18)
                                color: Components.UiTheme.color("panel")
                                border.color: Components.UiTheme.color("outline")

                                readonly property var config: configView.chartEntry(modelData.index, modelData.title)
                                readonly property int channelIdx: (typeof modelData.channelIndex === "number") ? modelData.channelIndex : 0

                                seriesModel: config.seriesModel
                                xColumn: config.xColumn
                                yColumn: config.yColumn
                                showLimits: true
                                scaleFactor: configView.scaleFactor

                                // 从后端获取通道配置
                                chartTitle: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                    ? foupAcquisition.getChannelTitle(channelIdx)
                                    : modelData.title
                                yAxisUnit: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                    ? foupAcquisition.getUnit(channelIdx)
                                    : ""
                                currentValue: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                    ? foupAcquisition.getChannelValue(channelIdx)
                                    : Number.NaN
                                oocLimitValue: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                    ? foupAcquisition.getOocUpper(channelIdx)
                                    : 80
                                oocLowerLimitValue: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                    ? foupAcquisition.getOocLower(channelIdx)
                                    : 20
                                oosLimitValue: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                    ? foupAcquisition.getOosUpper(channelIdx)
                                    : 90
                                oosLowerLimitValue: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                    ? foupAcquisition.getOosLower(channelIdx)
                                    : 10
                                targetValue: (typeof foupAcquisition !== "undefined" && foupAcquisition)
                                    ? foupAcquisition.getTarget(channelIdx)
                                    : 50

                                Text {
                                    visible: !seriesModel
                                    anchors.centerIn: parent
                                    text: "点击开始采集后显示实时曲线"
                                    color: Components.UiTheme.color("textSecondary")
                                    font.pixelSize: Components.UiTheme.fontSize("body")
                                }

                                // 监听后端配置变更信号
                                Connections {
                                    target: (typeof foupAcquisition !== "undefined") ? foupAcquisition : null
                                    enabled: typeof foupAcquisition !== "undefined" && foupAcquisition
                                    function onChannelConfigChanged(idx) {
                                        if (idx === chartCard.channelIdx) {
                                            chartCard.chartTitle = foupAcquisition.getChannelTitle(chartCard.channelIdx)
                                            chartCard.yAxisUnit = foupAcquisition.getUnit(chartCard.channelIdx)
                                            chartCard.oocLimitValue = foupAcquisition.getOocUpper(chartCard.channelIdx)
                                            chartCard.oocLowerLimitValue = foupAcquisition.getOocLower(chartCard.channelIdx)
                                            chartCard.oosLimitValue = foupAcquisition.getOosUpper(chartCard.channelIdx)
                                            chartCard.oosLowerLimitValue = foupAcquisition.getOosLower(chartCard.channelIdx)
                                            chartCard.targetValue = foupAcquisition.getTarget(chartCard.channelIdx)
                                        }
                                    }
                                    function onChannelValuesChanged() {
                                        chartCard.currentValue = foupAcquisition.getChannelValue(chartCard.channelIdx)
                                    }
                                }
                            }
                        }

                        // 状态信息（跨两列显示）
                        Text {
                            Layout.columnSpan: 2
                            text: {
                                if (typeof foupAcquisition === "undefined" || !foupAcquisition) {
                                    return "通道数量: 1"
                                }
                                var serverInfo = foupAcquisition.serverTypeDisplayName || "未知"
                                var channelInfo = "通道: " + foupAcquisition.channelCount
                                return serverInfo + " | " + channelInfo
                            }
                            color: Components.UiTheme.color("textSecondary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }
                    }
                }
            }
        }
    }

    Component {
        id: themeComponent

        Item {
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
    }
}
