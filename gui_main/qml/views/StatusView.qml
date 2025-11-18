import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../components"
import "../components" as Components

Rectangle {
    id: statusRoot
    color: "#e8ebf2"

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
        { title: "电压", currentValue: "3.6 V", index: 2 },
        { title: "温度", currentValue: "25 ℃", index: 3 }
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
                color: "#ffffff"
                border.color: "#dae0ec"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Components.UiTheme.spacing("lg")
                    spacing: Components.UiTheme.spacing("md")

                    Text {
                        text: "Loadport 模块"
                        font.pixelSize: Components.UiTheme.fontSize(24)
                        font.bold: true
                        color: "#2f3645"
                    }

                    Text {
                        text: "状态：TODO"
                        color: "#6c738a"
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Components.UiTheme.radius(18)
                        color: "#f6f8fc"
                        border.color: "#e1e7f3"

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
                        color: "#ffffff"
                        border.color: "#dbe0ed"
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
                                color: "#2f3645"
                            }

                            Text {
                                text: "当前值：" + modelData.currentValue
                                font.pixelSize: Components.UiTheme.fontSize("body")
                                color: "#66708e"
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
                color: "#ffffff"
                border.color: "#dae0ec"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Components.UiTheme.spacing("lg")
                    spacing: Components.UiTheme.spacing("md")

                    Text {
                        text: "FOUP 模块"
                        font.pixelSize: Components.UiTheme.fontSize(24)
                        font.bold: true
                        color: "#2f3645"
                    }

                    Text {
                        text: "状态：TODO"
                        color: "#6c738a"
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Components.UiTheme.radius(18)
                        color: "#f6f8fc"
                        border.color: "#e1e7f3"

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
                    color: "#ffffff"
                    border.color: "#dbe0ed"

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
                                color: "#6c738a"
                            }

                            Text {
                                text: "TODO"
                                font.pixelSize: Components.UiTheme.fontSize(24)
                                font.bold: true
                                color: "#2f3645"
                            }
                        }

                        Rectangle {
                            width: 1
                            Layout.fillHeight: true
                            color: "#eef1f7"
                        }

                        ColumnLayout {
                            Layout.preferredWidth: Components.UiTheme.controlWidth(120)
                            spacing: Components.UiTheme.spacing("sm")

                            Text {
                                text: "电量"
                                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                                color: "#6c738a"
                            }

                            Text {
                                text: "64 %"
                                font.pixelSize: Components.UiTheme.fontSize("display")
                                font.bold: true
                                color: "#2f3645"
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
                        color: "#ffffff"
                        border.color: "#dbe0ed"
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
                                color: "#2f3645"
                            }

                            Text {
                                text: "当前值：" + modelData.currentValue
                                font.pixelSize: Components.UiTheme.fontSize("body")
                                color: "#66708e"
                            }
                        }
                    }
                }
            }
        }
    }
}
