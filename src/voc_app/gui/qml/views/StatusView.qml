import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../components"
import "../components" as Components

Rectangle {
    id: statusRoot
    color: Components.UiTheme.color("background")

    // 外部写入当前子页面标识（Loadport / FOUP）
    property string currentSubPage: "loadport"
    property real scaleFactor: Components.UiTheme.controlScale
    property url loadportImageSource: Qt.resolvedUrl("../../resources/loadport_.png")
    property url foupImageSource: Qt.resolvedUrl("../../resources/foup_.png")

    // Loadport 子页面使用的实时曲线配置
    readonly property var loadportCharts: [
        { title: "电压", currentValue: "3.8 V", index: 0 },
        { title: "温度", currentValue: "26 ℃", index: 1 }
    ]

    // FOUP 子页面实时曲线配置
    readonly property var foupCharts: [
        { title: "数据", currentValue: "3.6 V", index: 2 }
    ]

    // 便捷函数，按索引读取曲线对象，缺省时返回占位配置
    function chartEntry(rowIndex, fallbackTitle) {
        const fallback = {
            title: fallbackTitle || "",
            seriesModel: null,
            xColumn: 0,
            yColumn: 1
        };
        if (typeof chartListModel === "undefined" || !chartListModel || typeof chartListModel.get !== "function")
            return fallback;
        // 获取指定行的曲线配置
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

    Loader {
        anchors.fill: parent
        sourceComponent: currentSubPage === "foup" ? foupComponent : loadportComponent
    }

    Component {
        id: loadportComponent

        RowLayout {
            anchors.fill: parent
            anchors.margins: Components.UiTheme.spacing("xl")
            spacing: Components.UiTheme.spacing("xl")

            Rectangle {
                Layout.preferredWidth: Components.UiTheme.controlWidth(320)
                Layout.maximumWidth: Components.UiTheme.controlWidth(360)
                Layout.minimumWidth: Components.UiTheme.controlWidth(260)
                Layout.fillHeight: true
                radius: Components.UiTheme.radius(20)
                color: Components.UiTheme.color("panel")
                border.color: Components.UiTheme.color("outline")

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Components.UiTheme.spacing("lg")
                    spacing: Components.UiTheme.spacing("md")

                    Text {
                        text: "Loadport 模块"
                        font.pixelSize: Components.UiTheme.fontSize(24)
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    Text {
                        text: "状态：TODO"
                        color: Components.UiTheme.color("textSecondary")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Components.UiTheme.radius(18)
                        color: Components.UiTheme.color("surface")
                        border.color: Components.UiTheme.color("outlineStrong")

                        Item {
                            anchors.fill: parent
                            anchors.margins: Components.UiTheme.spacing("md")

                            Image {
                                id: loadportImage
                                anchors.centerIn: parent
                                source: statusRoot.loadportImageSource
                                smooth: true
                                asynchronous: true
                                fillMode: Image.PreserveAspectFit
                                property real aspectRatio: implicitHeight > 0 ? implicitWidth / implicitHeight : 1
                                width: {
                                    const availW = parent.width;
                                    const availH = parent.height;
                                    const ratio = aspectRatio > 0 ? aspectRatio : 1;
                                    return Math.min(availW, availH * ratio);
                                }
                                height: width / Math.max(0.0001, aspectRatio)
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Components.UiTheme.spacing("xl")

                Repeater {
                    model: statusRoot.loadportCharts

                    delegate: ChartCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: Components.UiTheme.controlHeight(220)
                        radius: Components.UiTheme.radius(18)
                        color: Components.UiTheme.color("panel")
                        border.color: Components.UiTheme.color("outline")
                        chartTitle: ""
                        readonly property var config: statusRoot.chartEntry(modelData.index, modelData.title)
                        seriesModel: config.seriesModel
                        xColumn: config.xColumn
                        yColumn: config.yColumn
                        scaleFactor: statusRoot.scaleFactor

                        Column {
                            z: 2
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.margins: Components.UiTheme.spacing("lg")
                            spacing: Components.UiTheme.spacing("sm")

                            Text {
                                text: modelData.title + "实时曲线"
                                font.pixelSize: Components.UiTheme.fontSize("title")
                                font.bold: true
                                color: Components.UiTheme.color("textPrimary")
                            }

                            Text {
                                text: "当前值：" + modelData.currentValue
                                font.pixelSize: Components.UiTheme.fontSize("body")
                                color: Components.UiTheme.color("textSecondary")
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: foupComponent

        RowLayout {
            anchors.fill: parent
            anchors.margins: Components.UiTheme.spacing("xl")
            spacing: Components.UiTheme.spacing("xl")

            Rectangle {
                Layout.preferredWidth: Components.UiTheme.controlWidth(320)
                Layout.maximumWidth: Components.UiTheme.controlWidth(360)
                Layout.minimumWidth: Components.UiTheme.controlWidth(260)
                Layout.fillHeight: true
                radius: Components.UiTheme.radius(20)
                color: Components.UiTheme.color("panel")
                border.color: Components.UiTheme.color("outline")

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Components.UiTheme.spacing("lg")
                    spacing: Components.UiTheme.spacing("md")

                    Text {
                        text: "FOUP 模块"
                        font.pixelSize: Components.UiTheme.fontSize(24)
                        font.bold: true
                        color: Components.UiTheme.color("textPrimary")
                    }

                    Text {
                        text: "状态：TODO"
                        color: Components.UiTheme.color("textSecondary")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Components.UiTheme.radius(18)
                        color: Components.UiTheme.color("surface")
                        border.color: Components.UiTheme.color("outlineStrong")

                        Item {
                            anchors.fill: parent
                            anchors.margins: Components.UiTheme.spacing("md")

                            Image {
                                id: foupImage
                                anchors.centerIn: parent
                                source: statusRoot.foupImageSource
                                smooth: true
                                asynchronous: true
                                fillMode: Image.PreserveAspectFit
                                property real aspectRatio: implicitHeight > 0 ? implicitWidth / implicitHeight : 1
                                width: {
                                    const availW = parent.width;
                                    const availH = parent.height;
                                    const ratio = aspectRatio > 0 ? aspectRatio : 1;
                                    return Math.min(availW, availH * ratio);
                                }
                                height: width / Math.max(0.0001, aspectRatio)
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Components.UiTheme.spacing("xl")

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Components.UiTheme.controlHeight(120)
                    radius: Components.UiTheme.radius(18)
                    color: Components.UiTheme.color("panel")
                    border.color: Components.UiTheme.color("outline")

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: Components.UiTheme.spacing("lg")
                        spacing: Components.UiTheme.spacing("xl")

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Components.UiTheme.spacing("sm")

                            Text {
                                text: "功能模式"
                                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                                color: Components.UiTheme.color("textSecondary")
                            }

                            Text {
                                text: "TODO"
                                font.pixelSize: Components.UiTheme.fontSize(24)
                                font.bold: true
                                color: Components.UiTheme.color("textPrimary")
                            }
                        }

                        Rectangle {
                            width: 1
                            Layout.fillHeight: true
                            color: Components.UiTheme.color("outline")
                        }

                        ColumnLayout {
                            Layout.preferredWidth: Components.UiTheme.controlWidth(120)
                            spacing: Components.UiTheme.spacing("sm")

                            Text {
                                text: "电量"
                                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                                color: Components.UiTheme.color("textSecondary")
                            }

                            Text {
                                text: "64 %"
                                font.pixelSize: Components.UiTheme.fontSize("display")
                                font.bold: true
                                color: Components.UiTheme.color("textPrimary")
                            }
                        }
                    }
                }

                Repeater {
                    model: statusRoot.foupCharts

                    delegate: ChartCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: Components.UiTheme.controlHeight(220)
                        radius: Components.UiTheme.radius(18)
                        color: Components.UiTheme.color("panel")
                        border.color: Components.UiTheme.color("outline")
                        chartTitle: ""
                        readonly property var config: statusRoot.chartEntry(modelData.index, modelData.title)
                        seriesModel: config.seriesModel
                        xColumn: config.xColumn
                        yColumn: config.yColumn
                        scaleFactor: statusRoot.scaleFactor

                        Column {
                            z: 2
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.margins: Components.UiTheme.spacing("lg")
                            spacing: Components.UiTheme.spacing("sm")

                            Text {
                                text: modelData.title + "实时曲线"
                                font.pixelSize: Components.UiTheme.fontSize("title")
                                font.bold: true
                                color: Components.UiTheme.color("textPrimary")
                            }

                            Text {
                                text: "当前值：" + modelData.currentValue
                                font.pixelSize: Components.UiTheme.fontSize("body")
                                color: Components.UiTheme.color("textSecondary")
                            }
                        }
                    }
                }
            }
        }
    }
}
