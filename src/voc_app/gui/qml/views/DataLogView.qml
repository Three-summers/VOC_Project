import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtCore
import "../components"
import "../components" as Components

Rectangle {
    id: dataLogView
    color: Components.UiTheme.color("background")

    property var csvFileManagerRef: null
    property real scaleFactor: Components.UiTheme.controlScale
    property string logRootPath: (typeof fileRootPath !== "undefined" && fileRootPath) ? fileRootPath : ""
    property bool chartsVisible: false
    property var selectionMap: ({})
    // 存储最后一次点击绘图按钮时所选的列名
    property var lastPlottedColumns: []
    property string lastSettingsSummary: "尚未选择列"
    property string chartFileName: "datalog_chart.png"

    property bool zoomActive: false
    property string zoomColumnName: ""
    property var zoomDataPoints: null

    // 初次加载或切换视图时自动定位并载入首个文件
    function triggerAutomaticSelection() {
        if (!csvFileManagerRef)
        return;
        const hasFiles = csvFileManagerRef.csvFiles && csvFileManagerRef.csvFiles.length > 0;
        const fallbackFile = hasFiles ? csvFileManagerRef.csvFiles[0] : "";
        // 优先选择当前活动的文件
        const fileToSelect = csvFileManagerRef.activeFile || fallbackFile;
        if (fileToSelect) {
            csvFileManagerRef.parse_csv_file(fileToSelect);
            // 更新左侧文件树视图，使其高亮显示当前正在加载的文件，并将其转换为绝对路径
            browser.selectedPath = absolutePathFor(fileToSelect);
        }
        // 异步调度，当 syncSelectionsWithModel 推迟到所有同步代码执行完毕后执行
        Qt.callLater(syncSelectionsWithModel);
    }

    // 将相对路径转换为绝对路径
    function absolutePathFor(relativePath) {
        if (!relativePath || !logRootPath)
        return "";
        const normalizedBase = logRootPath.endsWith("/") ? logRootPath : logRootPath + "/";
        return normalizedBase + relativePath;
    }

    // 将绝对路径转换为相对路径
    function relativePath(path) {
        if (!path || !logRootPath)
        return "";
        const normalizedBase = logRootPath.replace(/\\/g, "/");
        let normalized = path.replace(/\\/g, "/");
        if (normalized.indexOf(normalizedBase) === 0) {
            normalized = normalized.slice(normalizedBase.length);
            if (normalized.startsWith("/"))
            normalized = normalized.slice(1);
        }
        return normalized;
    }

    // 当在文件树中点击一个文件，该函数将会被调用
    function handleSelection(path) {
        if (!csvFileManagerRef)
        return;
        browser.selectedPath = path || "";
        const relative = relativePath(path);
        if (relative)
        csvFileManagerRef.parse_csv_file(relative);
        Qt.callLater(syncSelectionsWithModel);
    }

    // 从数据模型中提取所有列的名称，以数组返回
    function columnNameList() {
        const model = csvFileManagerRef ? csvFileManagerRef.dataModel : null;
        if (!model)
        return [];
        // 先尝试直接使用 columnNames 属性
        if (model.columnNames && model.columnNames.length !== undefined)
        return model.columnNames;
        const fallback = [];
        // 检查 model 是否有 get() 方法和 count 属性
        if (typeof model.get === "function" && model.count) {
            for (let i = 0; i < model.count; i++) {
                const item = model.get(i);
                if (item && item.columnName)
                fallback.push(item.columnName);
            }
        }
        return fallback;
    }

    // 同步 UI 的选择状态与当前数据模型中的实际列
    function syncSelectionsWithModel() {
        // 获取当前数据模型中的所有列名
        const names = columnNameList();
        const newMap = {};
        for (let i = 0; i < names.length; i++) {
            const name = names[i];
            // 保留之前的选择状态，若无则默认选中
            newMap[name] = selectionMap.hasOwnProperty(name)
            ? selectionMap[name]
            : true; // 默认选中
        }
        selectionMap = newMap;
        updateSettingsSummary();
    }

    // 返回所有被选中的列名数组
    function selectedColumns() {
        const names = columnNameList();
        if (!names || names.length === 0)
        return [];
        const result = [];
        for (let i = 0; i < names.length; i++) {
            const name = names[i];
            if (isColumnSelected(name))
            result.push(name);
        }
        return result;
    }

    // 检查指定列名是否被选中
    function isColumnSelected(name) {
        if (!selectionMap || !selectionMap.hasOwnProperty(name))
        return true;
        return selectionMap[name];
    }

    // 当点击 CheckBox 时调用，更新指定列的选择状态
    function setColumnSelected(name, checked) {
        // 第三个参数是一个动态键，并将其中指定 name 的值替换，并与原有的 selectionMap 合并
        selectionMap = Object.assign({}, selectionMap, { [name]: checked });
        updateSettingsSummary();
    }

    // 接收数据点数组，计算并返回统计信息，包括点数、最小值和最大值
    function computeStats(points) {
        if (!points || points.length === 0)
        return { count: 0, min: 0, max: 0 };
        let minVal = points[0].y;
        let maxVal = points[0].y;
        for (let i = 1; i < points.length; i++) {
            const y = points[i].y;
            if (y < minVal) minVal = y;
            if (y > maxVal) maxVal = y;
        }
        return { count: points.length, min: minVal, max: maxVal };
    }

    // 更新设置摘要文本，显示当前选中的列
    function updateSettingsSummary() {
        const cols = selectedColumns();
        lastSettingsSummary = cols.length > 0 ? "已选择列：" + cols.join(", ") : "未选择任何列";
    }

    // 打开绘图设置对话框
    function openPlotSettingsDialog() {
        plotSettingsDialog.open();
    }

    // 根据当前选择的列绘制图表，响应用户点击绘图按钮
    function plotSelectedColumns() {
        lastPlottedColumns = selectedColumns();
        if (lastPlottedColumns.length === 0) {
            chartsVisible = false;
            lastSettingsSummary = "未选择任何列，无法绘图";
            return;
        }
        chartsVisible = true;
        zoomActive = false;
        lastSettingsSummary = "当前绘制列：" + lastPlottedColumns.join(", ");
    }

    // 关闭图表视图，返回列信息视图
    function closeCharts() {
        chartsVisible = false;
        zoomActive = false;
        updateSettingsSummary();
    }

    // 打开保存图表的文件对话框
    function openSaveDialog() {
        if (!chartsVisible || lastPlottedColumns.length === 0) {
            return;
        }
        if (!saveDialog.currentFolder || saveDialog.currentFolder.length === 0) {
            var basePath = dataLogView.logRootPath && dataLogView.logRootPath.length > 0
            ? dataLogView.logRootPath
            : StandardPaths.writableLocation(StandardPaths.PicturesLocation);
            if (!basePath || basePath.length === 0)
            basePath = StandardPaths.writableLocation(StandardPaths.DocumentsLocation);
            saveDialog.currentFolder = "file://" + basePath;
        }
        const suggestedName = dataLogView.zoomActive && dataLogView.zoomColumnName
        ? (dataLogView.zoomColumnName + ".png")
        : dataLogView.chartFileName;
        saveDialog.currentFile = saveDialog.currentFolder + "/" + suggestedName;
        saveDialog.open();
    }

    // 执行实际的图表保存操作，接收 FileDialog 返回的路径
    function saveChartsTo(path) {
        if (!chartsVisible || lastPlottedColumns.length === 0) {
            console.log("[DataLog] saveChartsTo: 无图可存 chartsVisible?", chartsVisible, " lastPlottedColumns:", lastPlottedColumns);
            return;
        }
        if (!path) {
            console.log("[DataLog] saveChartsTo: 未选择路径");
            return;
        }
        var normalizedPath = path.toString ? path.toString() : path;
        if (normalizedPath.startsWith("file://"))
        normalizedPath = decodeURIComponent(normalizedPath.substring(7));
        if (!normalizedPath.match(/\.[a-zA-Z0-9]+$/))
        normalizedPath = normalizedPath + "." + saveDialog.defaultSuffix;
        console.log("[DataLog] saveChartsTo: 即将保存路径 ->", normalizedPath);
        // 决定要抓取的 QML Item，如果处于放大模式则抓取 zoomChartCard，否则抓取 chartsGrid
        const targetItem = zoomActive && zoomChartCard ? zoomChartCard : chartsGrid;
        if (!targetItem || !targetItem.grabToImage) {
            console.log("[DataLog] saveChartsTo: 没有可用的抓取对象");
            return;
        }
        // 使用 grabToImage 方法异步抓取图像并保存到文件
        // 返回一个 GrabResult 对象，通过回调函数处理结果
        targetItem.grabToImage(function(result) {
            if (!result) {
                console.log("[DataLog] saveChartsTo: grabToImage 返回空");
                return;
            }
            console.log("[DataLog] saveChartsTo: grab 完成, size =", result.image.width, "x", result.image.height);
            // 将图像保存到指定路径
            if (!result.saveToFile(normalizedPath))
            console.log("[DataLog] saveChartsTo: 保存失败 ->", normalizedPath);
            else
            console.log("[DataLog] saveChartsTo: 成功保存 ->", normalizedPath);
        });
    }

    // 当用户点击某个图标时，进入放大模式
    function enterZoom(rowIndex) {
        const model = dataLogView.csvFileManagerRef ? dataLogView.csvFileManagerRef.dataModel : null;
        if (!model || typeof model.get !== "function") {
            console.warn("[DataLog] enterZoom: data model 不可用");
            return;
        }
        const rowData = model.get(rowIndex);
        if (!rowData) {
            console.warn("[DataLog] enterZoom: row 数据为空 ->", rowIndex);
            return;
        }
        zoomColumnName = rowData.columnName || "";
        zoomDataPoints = rowData.dataPoints || [];
        zoomActive = true;
    }

    // 退出放大模式
    function exitZoom() {
        zoomActive = false;
        zoomColumnName = "";
        zoomDataPoints = null;
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: Components.UiTheme.spacing("lg")
        spacing: Components.UiTheme.spacing("lg")

        Rectangle {
            Layout.preferredWidth: Components.UiTheme.controlWidth(260)
            Layout.fillHeight: true
            color: Components.UiTheme.color("panelAlt")
            border.color: Components.UiTheme.color("outline")
            border.width: 1

            // 文件树组件
            FileTreeBrowserView {
                id: browser
                anchors.fill: parent
                anchors.margins: Components.UiTheme.spacing("sm")
                basePath: dataLogView.logRootPath
                fileControllerRef: fileController
                scaleFactor: dataLogView.scaleFactor
                // 当选择文件时调用 handleSelection 方法，在其中加载并解析文件，并更新模型和视图
                onFileSelected: function (filePath) {
                    dataLogView.handleSelection(filePath);
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Components.UiTheme.color("panel")
            border.color: Components.UiTheme.color("outline")
            border.width: 1
            radius: 4

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Components.UiTheme.spacing("xl")
                spacing: Components.UiTheme.spacing("lg")

                Text {
                    text: chartsVisible ? "绘图结果" : "列信息"
                    font.bold: true
                    font.pixelSize: Components.UiTheme.fontSize("title")
                    color: Components.UiTheme.color("textPrimary")
                }

                Text {
                    text: lastSettingsSummary
                    color: Components.UiTheme.color("textSecondary")
                    wrapMode: Text.WordWrap
                    font.pixelSize: Components.UiTheme.fontSize("body")
                }

                // 该布局用于在列信息视图和绘画视图之间切换
                StackLayout {
                    id: contentStack
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: chartsVisible ? 1 : 0

                    // 列信息面板
                    ScrollView {
                        id: columnInfoScroll
                        clip: true

                        Column {
                            id: columnInfoList
                            width: columnInfoScroll.width - columnInfoScroll.leftPadding - columnInfoScroll.rightPadding
                            // 动态生成列信息项
                            Repeater {
                                model: dataLogView.csvFileManagerRef ? dataLogView.csvFileManagerRef.dataModel : null
                                delegate: Rectangle {
                                    width: columnInfoList.width
                                    height: Components.UiTheme.controlHeight(80)
                                    border.color: Components.UiTheme.color("outline")
                                    color: index % 2 === 0 ? Components.UiTheme.color("panel") : Components.UiTheme.color("panelAlt")
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: Components.UiTheme.spacing("md")
                                        spacing: Components.UiTheme.spacing("md")

                                        CheckBox {
                                            id: columnCheck
                                            checked: dataLogView.isColumnSelected(model.columnName)
                                            onToggled: dataLogView.setColumnSelected(model.columnName, checked)
                                            leftPadding: Components.UiTheme.spacing("md")
                                            rightPadding: Components.UiTheme.spacing("sm")
                                            implicitWidth: Components.UiTheme.px(60)
                                            implicitHeight: Components.UiTheme.controlHeight("buttonThin")
                                            indicator: Rectangle {
                                                implicitWidth: 32 * Components.UiTheme.controlScale
                                                implicitHeight: implicitWidth
                                                radius: Components.UiTheme.radius("md")
                                                border.color: columnCheck.checked ? Components.UiTheme.color("accentInfo") : Components.UiTheme.color("outlineStrong")
                                                border.width: 2
                                                color: columnCheck.checked ? Components.UiTheme.color("accentInfo") : "transparent"
                                                anchors.verticalCenter: parent.verticalCenter
                                                Text {
                                                    text: columnCheck.checked ? "✓" : ""
                                                    anchors.centerIn: parent
                                                    font.pixelSize: Components.UiTheme.fontSize("subtitle")
                                                    color: Components.UiTheme.color("textPrimary")
                                                }
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: Components.UiTheme.spacing("xs")

                                            Text {
                                                text: model.columnName
                                                font.bold: true
                                                color: Components.UiTheme.color("textPrimary")
                                                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                                            }

                                            Text {
                                                readonly property var stats: dataLogView.computeStats(model.dataPoints)
                                                text: "点数: " + stats.count + "    最小值: " + stats.min.toFixed(2) + "    最大值: " + stats.max.toFixed(2)
                                                color: Components.UiTheme.color("textSecondary")
                                                font.pixelSize: Components.UiTheme.fontSize("label")
                                            }
                                        }
                                    }
                                }
                        }
                    }
                    }

                    // 绘图面板
                    Flickable {
                        contentWidth: width
                        contentHeight: chartsGrid.implicitHeight
                        clip: true

                        // 图表网格布局
                        GridLayout {
                            id: chartsGrid
                            width: parent.width
                            // 指定网格为两列
                            columns: 2
                            rowSpacing: Components.UiTheme.spacing("lg")
                            columnSpacing: Components.UiTheme.spacing("lg")

                            Repeater {
                                model: dataLogView.csvFileManagerRef ? dataLogView.csvFileManagerRef.dataModel : null
                                delegate: ChartCard {
                                    readonly property bool shouldShow: dataLogView.lastPlottedColumns.indexOf(model.columnName) !== -1
                                    visible: shouldShow
                                    Layout.preferredHeight: shouldShow ? Components.UiTheme.controlHeight(220) : 0
                                    Layout.fillWidth: true
                                    chartTitle: model.columnName
                                    dataPoints: model.dataPoints
                                    scaleFactor: dataLogView.scaleFactor

                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: parent.visible
                                        // 设置手型光标提示可点击
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: dataLogView.enterZoom(index)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // 放大图表覆盖层，仅在 zoomActive 为 true 时显示
    Rectangle {
        id: zoomOverlay
        anchors.fill: parent
        radius: 0
        color: "#cc0f111a" // Slightly transparent dark
        visible: dataLogView.zoomActive
        // 确保覆盖在最顶层
        z: 99

        CustomButton {
            text: "退出全屏"
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 18 * dataLogView.scaleFactor
            anchors.rightMargin: 18 * dataLogView.scaleFactor
            width: 160 * dataLogView.scaleFactor
            height: 60 * dataLogView.scaleFactor
            scaleFactor: dataLogView.scaleFactor
            onClicked: dataLogView.exitZoom()
        }

        ChartCard {
            id: zoomChartCard
            anchors {
                top: parent.top
                bottom: parent.bottom
                left: parent.left
                right: parent.right
                topMargin: 70 * dataLogView.scaleFactor
                bottomMargin: 24 * dataLogView.scaleFactor
                leftMargin: 24 * dataLogView.scaleFactor
                rightMargin: 24 * dataLogView.scaleFactor
            }
            chartTitle: dataLogView.zoomColumnName ? dataLogView.zoomColumnName + "（放大）" : "放大图"
            dataPoints: dataLogView.zoomDataPoints || []
            color: Components.UiTheme.color("panel")
            scaleFactor: dataLogView.scaleFactor
        }
    }

    Dialog {
        id: plotSettingsDialog
        title: "绘图设置"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        implicitWidth: 440 * dataLogView.scaleFactor
        implicitHeight: 480 * dataLogView.scaleFactor
        x: Math.max(Components.UiTheme.spacing("lg"), (dataLogView.width - width) / 2)
        y: Components.UiTheme.spacing("lg")
        parent: dataLogView
        property var backupSelection: ({})

        onOpened: {
            backupSelection = JSON.parse(JSON.stringify(selectionMap));
        }
        onRejected: {
            selectionMap = backupSelection;
            updateSettingsSummary();
        }
        onAccepted: updateSettingsSummary()

        background: Rectangle {
            color: Components.UiTheme.color("panel")
            border.color: Components.UiTheme.color("outline")
            radius: Components.UiTheme.radius("sm")
        }

        // Dialog doesn't automatically style its header/footer in standard controls easily without custom contentItem
        // But the contentItem below handles the body. 
        // Note: Standard Dialog Text color might be system default. 
        // We might need to check if title color can be set.
        
        contentItem: ScrollView {
            implicitWidth: Components.UiTheme.controlWidth(340)
            implicitHeight: Components.UiTheme.controlHeight(360)
            Column {
                width: parent ? parent.width : Components.UiTheme.controlWidth(320)
                spacing: Components.UiTheme.spacing("lg")
                Repeater {
                    model: dataLogView.csvFileManagerRef ? dataLogView.csvFileManagerRef.dataModel : null
                    delegate: RowLayout {
                        width: parent.width
                        spacing: Components.UiTheme.spacing("md")
                        Rectangle {
                            Layout.fillWidth: true
                            height: Components.UiTheme.controlHeight("input")
                            color: "transparent"
                            RowLayout {
                                anchors.fill: parent
                                CheckBox {
                                    id: columnExportCheck
                                    checked: dataLogView.isColumnSelected(model.columnName)
                                    onToggled: dataLogView.setColumnSelected(model.columnName, checked)
                                    indicator: Rectangle {
                                        implicitWidth: 28 * Components.UiTheme.controlScale
                                        implicitHeight: implicitWidth
                                        radius: Components.UiTheme.radius("md")
                                        border.color: columnExportCheck.checked ? Components.UiTheme.color("accentInfo") : Components.UiTheme.color("outlineStrong")
                                        border.width: 2
                                        color: columnExportCheck.checked ? Components.UiTheme.color("accentInfo") : "transparent"
                                        anchors.verticalCenter: parent.verticalCenter
                                        Text {
                                            text: columnExportCheck.checked ? "✓" : ""
                                            anchors.centerIn: parent
                                            font.pixelSize: Components.UiTheme.fontSize("body")
                                            color: Components.UiTheme.color("textPrimary")
                                        }
                                    }
                                }
                                Text {
                                    text: model.columnName
                                    color: Components.UiTheme.color("textPrimary")
                                    font.pixelSize: Components.UiTheme.fontSize("body")
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: Components.UiTheme.controlHeight(70)
                    color: "transparent"
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: Components.UiTheme.spacing("md")
                        Text {
                            text: "导出文件名："
                            color: Components.UiTheme.color("textPrimary")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                        }
                        TextField {
                            text: dataLogView.chartFileName
                            placeholderText: "例如 datalog_chart.png"
                            Layout.fillWidth: true
                            Layout.preferredWidth: Components.UiTheme.controlWidth(320)
                            implicitHeight: Components.UiTheme.controlHeight("input")
                            font.pixelSize: Components.UiTheme.fontSize("body")
                            color: Components.UiTheme.color("textPrimary")
                            background: Rectangle {
                                color: Components.UiTheme.color("surface")
                                border.color: Components.UiTheme.color("outline")
                            }
                            onEditingFinished: {
                                if (text.length === 0)
                                dataLogView.chartFileName = "datalog_chart.png";
                                else
                                dataLogView.chartFileName = text;
                            }
                        }
                    }
                }
            }
        }
    }

    FileDialog {
        id: saveDialog
        title: "保存图表"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "png"
        nameFilters: ["PNG 图片 (*.png)", "JPEG 图片 (*.jpg *.jpeg)", "所有文件 (*)"]
        onAccepted: {
            let targetPath = null;
            if (saveDialog.currentFile) {
                targetPath = saveDialog.currentFile;
            } else {
                if (selectedFile && selectedFile.length > 0)
                targetPath = selectedFile;
                else if (currentFile && currentFile.length > 0)
                targetPath = currentFile;
                if (!targetPath && currentFolder)
                targetPath = currentFolder + "/" + dataLogView.chartFileName;
            }
            dataLogView.saveChartsTo(targetPath);
        }
        onRejected: console.log("[DataLog] FileDialog rejected")
    }

    Connections {
        target: dataLogView.csvFileManagerRef
        enabled: !!dataLogView.csvFileManagerRef
        function onActiveFileChanged() {
            browser.selectedPath = dataLogView.absolutePathFor(dataLogView.csvFileManagerRef.activeFile);
        }
    }

    Connections {
        target: dataLogView.csvFileManagerRef ? dataLogView.csvFileManagerRef.dataModel : null
        enabled: !!(dataLogView.csvFileManagerRef && dataLogView.csvFileManagerRef.dataModel)
        function onModelReset() {
            dataLogView.chartsVisible = false;
            dataLogView.lastPlottedColumns = [];
            dataLogView.selectionMap = ({});
            dataLogView.zoomActive = false;
            dataLogView.updateSettingsSummary();
            Qt.callLater(dataLogView.syncSelectionsWithModel);
        }
        function onColumnNamesChanged() {
            Qt.callLater(dataLogView.syncSelectionsWithModel);
        }
    }

    Component.onCompleted: updateSettingsSummary()
}