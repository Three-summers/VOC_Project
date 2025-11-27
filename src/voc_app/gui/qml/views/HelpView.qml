import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components" as Components

Rectangle {
    color: "#f6f8fb"

    ScrollView {
        id: scrollView
        anchors.fill: parent
        anchors.margins: Components.UiTheme.spacing("lg")
        clip: true

        ColumnLayout {
            width: scrollView.availableWidth 
            spacing: Components.UiTheme.spacing("lg")

            Text {
                text: "使用指南"
                font.pixelSize: Components.UiTheme.fontSize("title")
                font.bold: true
                color: Components.UiTheme.color("textOnLight")
                Layout.fillWidth: true // 确保标题区域占满宽度
            }

            Repeater {
                model: [
                    {
                        title: "导航与布局",
                        body: "\u2022 顶部标题栏显示当前视图、报警按钮和登录入口；报警弹窗与登录对话框在状态区顶部居中显示。\n\u2022 右侧命令面板随页面变化（Status/Config/Alarms/DataLog）。\n\u2022 底部导航切换主视图：Status、DataLog、Config、Alarms、Help。"
                    },
                    {
                        title: "状态页（Status）",
                        body: "\u2022 左侧展示 Loadport 模块概览，右侧命令面板提供启动/拍合/锁扣等操作。\n\u2022 中间 ChartCard 显示实时曲线（默认电压/温度示例）。\n\u2022 ALARMS 高亮时点击可查看当前报警列表。"
                    },
                    {
                        title: "配置页（Config）",
                        body: "\u2022 子页 Loadport / FOUP 通过上方子导航切换。\n\u2022 FOUP 区域显示采集状态与实时曲线；使用“开始采集/结束采集”控制，曲线窗口固定长度，二次采集会清空旧点并从新序号开始。\n\u2022 当前采样值显示在曲线下方。"
                    },
                    {
                        title: "数据日志（DataLog）",
                        body: "\u2022 左侧文件树浏览日志目录，选中文件后解析列。\n\u2022 “绘图设置”可勾选列并修改导出文件名；点击“绘图”展示多列曲线，点击单图进入放大视图，右上“退出全屏”返回。\n\u2022 “保存图表”导出当前图/放大图为 PNG/JPEG；切换文件会重置选中列与绘图状态。"
                    },
                    {
                        title: "报警与登录",
                        body: "\u2022 标题栏 ALARMS 按钮有未确认报警时高亮，点击展开列表，可关闭或清除。\n\u2022 右上登录按钮打开登录对话框，输入用户名/密码后登录；已登录状态下显示用户名，可再次点击登出。"
                    },
                    {
                        title: "快捷提示",
                        body: "\u2022 放大视图可快速查看单列细节；退出按钮在右上角。\n\u2022 采集类操作建议先停止再重新开始，界面会自动清空旧数据。\n\u2022 导出前先在绘图设置中调整文件名与列选择，避免空图。"
                    }
                ]

                delegate: Rectangle {
                    id: card
                    Layout.fillWidth: true 
                    
                    readonly property real padding: Components.UiTheme.spacing("lg")
                    color: "#ffffff"
                    radius: Components.UiTheme.radius("md")
                    border.color: "#dbe0ed"
                    border.width: 1
                    
                    // 自动适应内容高度
                    implicitHeight: cardContent.implicitHeight + padding * 2

                    ColumnLayout {
                        id: cardContent
                        anchors.fill: parent
                        anchors.margins: card.padding
                        spacing: Components.UiTheme.spacing("sm")

                        RowLayout {
                            spacing: Components.UiTheme.spacing("sm")
                            Layout.fillWidth: true 

                            Rectangle {
                                width: 6
                                height: Components.UiTheme.fontSize("subtitle")
                                radius: Components.UiTheme.radius("sm")
                                color: Components.UiTheme.color("accentInfo")
                            }
                            Text {
                                text: modelData.title
                                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                                font.bold: true
                                color: Components.UiTheme.color("textOnLight")
                                Layout.fillWidth: true
                            }
                        }

                        Text {
                            text: modelData.body
                            color: Components.UiTheme.color("textOnLightMuted")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                            wrapMode: Text.WordWrap // 自动换行
                            
                            // 必须设置 fillWidth，否则 WordWrap 不知道边界在哪里，
                            // 就会导致宽度塌缩或者不换行
                            Layout.fillWidth: true 
                        }
                    }
                }
            }
        }
    }
}
