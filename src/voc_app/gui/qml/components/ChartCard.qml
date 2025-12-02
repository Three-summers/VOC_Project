import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtCharts
import QtQml
import "." as Components

Rectangle {
    id: chartCard
    Layout.fillWidth: true
    Layout.fillHeight: true
    Layout.preferredHeight: Components.UiTheme.controlHeight(220)
    color: Components.UiTheme.color("panel")
    border.color: Components.UiTheme.color("outline")
    border.width: Math.max(1, Components.UiTheme.controlScale)
    radius: Components.UiTheme.radius("sm")

    property string chartTitle: "Humidity/Temperature" // 示例标题
    property string yAxisUnit: ""  // Y轴单位，如 ppb, dB, ℃, %
    property real currentValue: Number.NaN  // 当前值

    // 规格界限 (OOS) 和 控制界限 (OOC) 的值
    property real oosLimitValue: 90.0
    property real oosLowerLimitValue: Number.NaN
    property real oocLimitValue: 80.0
    property real oocLowerLimitValue: Number.NaN
    property real targetValue: Number.NaN
    property bool showLimits: true
    property bool showOocUpper: true   // 是否显示OOC上界
    property bool showOocLower: true   // 是否显示OOC下界
    property bool showOosUpper: true   // 是否显示OOS上界
    property bool showOosLower: true   // 是否显示OOS下界
    property bool showTarget: true     // 是否显示Target线

    property var chartStyle: {
        "v1": {
            // OOS: R220, G82, B82
            "oosColor": Qt.rgba(220/255, 82/255, 82/255, 1.0),
            // OOC: R220, G81, B52
            "oocColor": Qt.rgba(220/255, 81/255, 52/255, 1.0),
            // Chart: R128, G0, B128
            "mainColor": Qt.rgba(128/255, 0/255, 128/255, 1.0),
            "targetColor": Qt.rgba(0/255, 122/255, 204/255, 1.0)
        }
    }

    // 数据相关属性
    property var dataPoints: []
    property var seriesModel: null
    property int xColumn: 0
    property int yColumn: 1
    property real scaleFactor: Components.UiTheme.controlScale


    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Components.UiTheme.spacing("md")

        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignHCenter
            spacing: Components.UiTheme.spacing("md")

            Text {
                text: chartCard.chartTitle
                font.bold: true
                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                color: Components.UiTheme.color("textPrimary")
            }

            Text {
                visible: !isNaN(chartCard.currentValue)
                text: {
                    if (isNaN(chartCard.currentValue)) return "";
                    var valueStr = chartCard.currentValue.toFixed(2);
                    return chartCard.yAxisUnit ? valueStr + " " + chartCard.yAxisUnit : valueStr;
                }
                font.pixelSize: Components.UiTheme.fontSize("subtitle")
                font.bold: true
                color: {
                    // 根据值与限值关系显示不同颜色
                    if (isNaN(chartCard.currentValue)) return Components.UiTheme.color("textSecondary");
                    var val = chartCard.currentValue;
                    // OOS 超限 - 红色
                    if ((!isNaN(chartCard.oosLimitValue) && val > chartCard.oosLimitValue) ||
                        (!isNaN(chartCard.oosLowerLimitValue) && val < chartCard.oosLowerLimitValue)) {
                        return Components.UiTheme.color("accentAlarm");
                    }
                    // OOC 超限 - 橙色
                    if ((!isNaN(chartCard.oocLimitValue) && val > chartCard.oocLimitValue) ||
                        (!isNaN(chartCard.oocLowerLimitValue) && val < chartCard.oocLowerLimitValue)) {
                        return Components.UiTheme.color("accentWarning");
                    }
                    // 正常 - 绿色
                    return Components.UiTheme.color("accentSuccess");
                }
            }
        }

        ChartView {
            id: chartView
            Layout.fillWidth: true
            Layout.fillHeight: true
            antialiasing: true
            backgroundRoundness: 0
            dropShadowEnabled: false
            animationOptions: ChartView.NoAnimation
            backgroundColor: "transparent"

            // 图例设置
            legend.visible: true
            legend.alignment: Qt.AlignTop
            legend.labelColor: Components.UiTheme.color("textPrimary")
            legend.font.pixelSize: Components.UiTheme.fontSize("body")

            margins.top: Components.UiTheme.spacing("sm")
            margins.bottom: Components.UiTheme.spacing("sm")
            margins.left: Components.UiTheme.spacing("md")
            margins.right: Components.UiTheme.spacing("md")

            Timer {
                id: legendRefresher
                interval: 100 // 延迟 100ms，给底层渲染一点时间生成图例
                running: true // 组件加载完成后自动启动一次
                repeat: false
                onTriggered: {
                    chartLegendHelper.hideSeriesInLegend(chartView, [lineSeries, pointSeries]);
                }
            }
            //
            // function updateLegendVisibility() {
            //     if (!chartView.legend || !chartView.legend.markers) {
            //         return;
            //     }
            //
            //     var markers = chartView.legend.markers;
            //
            //     for (var i = 0; i < markers.length; i++) {
            //         var marker = markers[i];
            //
            //         if (marker.series === lineSeries || marker.series === pointSeries) {
            //             marker.visible = false;
            //         }
            //     }
            // }

            DateTimeAxis {
                id: xAxis
                min: new Date(Date.now() - 30000)
                max: new Date(Date.now() + 30000)
                format: "HH:mm:ss"
                tickCount: 6
                labelsFont.pixelSize: Components.UiTheme.fontSize("caption")
                titleFont.pixelSize: Components.UiTheme.fontSize("caption")
                labelsColor: Components.UiTheme.color("textSecondary")
                gridLineColor: Components.UiTheme.color("outline")
                // 注意：这里移除了 onMinChanged/onMaxChanged 的监听，提升性能
            }

            ValueAxis {
                id: yAxis
                min: 0
                max: 100
                labelFormat: "%.0f"
                tickCount: 5
                titleText: chartCard.yAxisUnit  // 显示Y轴单位
                labelsFont.pixelSize: Components.UiTheme.fontSize("caption")
                titleFont.pixelSize: Components.UiTheme.fontSize("caption")
                labelsColor: Components.UiTheme.color("textSecondary")
                titleVisible: chartCard.yAxisUnit.length > 0
                gridLineColor: Components.UiTheme.color("outline")
            }

            // -----------------------------------------------------------------
            // 1. OOS Series (规格界限) - 实线
            // -----------------------------------------------------------------
            LineSeries {
                id: oosSeries
                name: "OOS 上界"
                axisX: xAxis
                axisY: yAxis
                color: chartCard.chartStyle.v1.oosColor
                style: Qt.SolidLine // 图片要求：实线
                width: 1.5 * Components.UiTheme.controlScale
                visible: chartCard.showLimits && chartCard.showOosUpper
                // useOpenGL: chartView.width > 0 && chartView.height > 0 // 开启 OpenGL 加速渲染
            }

            // -----------------------------------------------------------------
            // 2. OOS 下界 - 实线
            // -----------------------------------------------------------------
            LineSeries {
                id: oosLowerSeries
                name: "OOS 下界"
                axisX: xAxis
                axisY: yAxis
                color: chartCard.chartStyle.v1.oosColor
                style: Qt.SolidLine
                width: 1.5 * Components.UiTheme.controlScale
                visible: chartCard.showLimits && chartCard.showOosLower
                // useOpenGL: chartView.width > 0 && chartView.height > 0
            }

            // -----------------------------------------------------------------
            // 3. OOC Series (控制界限) - 虚线
            // -----------------------------------------------------------------
            LineSeries {
                id: oocSeries
                name: "OOC 上界"
                axisX: xAxis
                axisY: yAxis
                color: chartCard.chartStyle.v1.oocColor
                style: Qt.DashLine // 图片要求：虚线
                width: 1.5 * Components.UiTheme.controlScale
                visible: chartCard.showLimits && chartCard.showOocUpper
                // useOpenGL: chartView.width > 0 && chartView.height > 0
            }

            // -----------------------------------------------------------------
            // 4. OOC 下界 - 虚线
            // -----------------------------------------------------------------
            LineSeries {
                id: oocLowerSeries
                name: "OOC 下界"
                axisX: xAxis
                axisY: yAxis
                color: chartCard.chartStyle.v1.oocColor
                style: Qt.DashLine
                width: 1.5 * Components.UiTheme.controlScale
                visible: chartCard.showLimits && chartCard.showOocLower
                // useOpenGL: chartView.width > 0 && chartView.height > 0
            }

            // -----------------------------------------------------------------
            // 5. Target 线 - 点划线
            // -----------------------------------------------------------------
            LineSeries {
                id: targetSeries
                name: "Target"
                axisX: xAxis
                axisY: yAxis
                color: chartCard.chartStyle.v1.targetColor
                style: Qt.DotLine
                width: 2 * Components.UiTheme.controlScale
                visible: chartCard.showLimits && chartCard.showTarget
                // useOpenGL: chartView.width > 0 && chartView.height > 0
            }

            // -----------------------------------------------------------------
            // 6. Main Data Series (主数据) - 实线
            // -----------------------------------------------------------------
            LineSeries {
                id: lineSeries
                name: "Measured"
                // pointsVisible: true
                axisX: xAxis
                axisY: yAxis
                color: chartCard.chartStyle.v1.mainColor // 图片要求：紫色 RGB(128,0,128)
                style: Qt.SolidLine
                width: Math.max(1, 1.25 * Components.UiTheme.controlScale)
                // useOpenGL: chartView.width > 0 && chartView.height > 0
            }

            ScatterSeries {
                id: pointSeries
                name: "Point"
                axisX: xAxis
                axisY: yAxis
                color: "green"
                markerSize: 12
            }

            VXYModelMapper {
                id: lineMapper
                // 绑定将在 updateMapperBinding 中处理
            }
            VXYModelMapper {
                id: pointMapper
            }


            // onSeriesAdded: Qt.callLater(updateLegendVisibility);
        }
    }


    // 优化后的绘制函数：绘制一条极其长的线，利用 Viewport 裁剪，避免滚动时重绘
    function updateLimitLines() {
        oosSeries.clear();
        oosLowerSeries.clear();
        oocSeries.clear();
        oocLowerSeries.clear();
        targetSeries.clear();

        if (!showLimits) return;

        var minX = null;
        var maxX = null;

        if (chartCard.seriesModel && chartCard.seriesModel.hasData) {
            minX = chartCard.seriesModel.minX;
            maxX = chartCard.seriesModel.maxX;
        } else if (chartCard.dataPoints && chartCard.dataPoints.length > 0) {
            minX = chartCard.dataPoints[0].x;
            maxX = chartCard.dataPoints[0].x;
            for (var i = 1; i < chartCard.dataPoints.length; i++) {
                var px = chartCard.dataPoints[i].x;
                if (px < minX) minX = px;
                if (px > maxX) maxX = px;
            }
        }

        var nowMs = Date.now();
        if (minX === null || maxX === null) {
            minX = nowMs - 30000;
            maxX = nowMs + 30000;
        } else if (minX === maxX) {
            minX = minX - 1000;
            maxX = maxX + 1000;
        }

        var span = Math.abs(maxX - minX);
        var margin = Math.max(1000, span * 0.1);
        var startX = minX - margin;
        var endX = maxX + margin;

        if (!isNaN(oosLimitValue)) {
            oosSeries.append(startX, oosLimitValue);
            oosSeries.append(endX, oosLimitValue);
        }
        if (!isNaN(oosLowerLimitValue)) {
            oosLowerSeries.append(startX, oosLowerLimitValue);
            oosLowerSeries.append(endX, oosLowerLimitValue);
        }
        if (!isNaN(oocLimitValue)) {
            oocSeries.append(startX, oocLimitValue);
            oocSeries.append(endX, oocLimitValue);
        }
        if (!isNaN(oocLowerLimitValue)) {
            oocLowerSeries.append(startX, oocLowerLimitValue);
            oocLowerSeries.append(endX, oocLowerLimitValue);
        }
        if (!isNaN(targetValue)) {
            targetSeries.append(startX, targetValue);
            targetSeries.append(endX, targetValue);
        }
    }

    function updateAxesFromSeries() {
        if (!chartCard.seriesModel || !chartCard.seriesModel.hasData) {
            resetAxesToDefault();
            return;
        }
        var minX = chartCard.seriesModel.minX;
        var maxX = chartCard.seriesModel.maxX;
        var minY = chartCard.seriesModel.minY;
        var maxY = chartCard.seriesModel.maxY;

        // 关键逻辑：确保 Y 轴范围包含 OOS/OOC 上下界和 Target
        if (showLimits) {
            var allValues = [minY, maxY];
            if (!isNaN(oosLimitValue)) allValues.push(oosLimitValue);
            if (!isNaN(oosLowerLimitValue)) allValues.push(oosLowerLimitValue);
            if (!isNaN(oocLimitValue)) allValues.push(oocLimitValue);
            if (!isNaN(oocLowerLimitValue)) allValues.push(oocLowerLimitValue);
            if (!isNaN(targetValue)) allValues.push(targetValue);
            minY = Math.min(...allValues);
            maxY = Math.max(...allValues);
        }

        var visibleWindowMs = (chartCard.seriesModel.maxRows ? Math.max(10, chartCard.seriesModel.maxRows) : 60) * 1000.0;

        if (minX === maxX) {
            minX = minX - 1000;
            maxX = maxX + 1000;
        } else if (maxX - minX > visibleWindowMs) {
            minX = maxX - visibleWindowMs;
        }

        // Y 轴增加一点 Padding
        if (minY === maxY) {
            minY = minY - 1;
            maxY = maxY + 1;
        }

        var paddingX = Math.max(500, Math.abs(maxX - minX) * 0.05);
        var paddingY = Math.max(0.5, Math.abs(maxY - minY) * 0.1);

        xAxis.min = new Date(minX - paddingX);
        xAxis.max = new Date(maxX + paddingX);
        yAxis.min = minY - paddingY;
        yAxis.max = maxY + paddingY;
        updateLimitLines();
    }

    function resetAxesToDefault() {
        var nowMs = Date.now();
        var halfWindow = 30000;
        xAxis.min = new Date(nowMs - halfWindow);
        xAxis.max = new Date(nowMs + halfWindow);
        yAxis.min = 0;
        yAxis.max = 100;
        updateLimitLines();
    }

    function updateMapperBinding() {
        if (chartCard.seriesModel) {
            lineMapper.xColumn = chartCard.xColumn;
            lineMapper.yColumn = chartCard.yColumn;
            lineMapper.model = chartCard.seriesModel;
            lineMapper.series = lineSeries;

            pointMapper.xColumn = chartCard.xColumn;
            pointMapper.yColumn = chartCard.yColumn;
            pointMapper.model = chartCard.seriesModel;
            pointMapper.series = pointSeries;

        } else {
            lineMapper.series = null;
            lineMapper.model = null;

            pointMapper.series = null;
            pointMapper.model = null;
        }
    }


    Component.onCompleted: {
        updateMapperBinding();
        updateLimitLines(); // 初始化绘制一次
        // Qt.callLater(chartView.updateLegendVisibility);
    }

    // 仅当界限数值改变时才重绘
    onOosLimitValueChanged: updateLimitLines()
    onOocLimitValueChanged: updateLimitLines()
    onShowLimitsChanged: updateLimitLines()


    onSeriesModelChanged: {
        if (chartCard.seriesModel) {
            lineSeries.clear();
            pointSeries.clear();
            updateAxesFromSeries();
            if (typeof chartCard.seriesModel.force_rebuild === "function") {
                chartCard.seriesModel.force_rebuild();
            }
        } else {
            lineSeries.clear();
            pointSeries.clear();
            resetAxesToDefault();
        }
        updateMapperBinding();
    }

    onXColumnChanged: updateMapperBinding()
    onYColumnChanged: updateMapperBinding()

    // 如果不使用 Model 而是直接传入 dataPoints 数组
    onDataPointsChanged: {
        if (chartCard.seriesModel) return;

        lineSeries.clear();
        pointSeries.clear();
        if (!dataPoints || dataPoints.length === 0) {
            resetAxesToDefault();
            return;
        }

        var minX = dataPoints[0].x;
        var maxX = dataPoints[0].x;
        var minY = dataPoints[0].y;
        var maxY = dataPoints[0].y;

        for (var i = 0; i < dataPoints.length; i++) {
            var point = dataPoints[i];
            lineSeries.append(point.x, point.y);
            pointSeries.append(point.x, point.y);
            if (point.x < minX) minX = point.x;
            if (point.x > maxX) maxX = point.x;
            if (point.y < minY) minY = point.y;
            if (point.y > maxY) maxY = point.y;
        }

        if (showLimits) {
            var values = [minY, maxY];
            if (!isNaN(oosLimitValue)) values.push(oosLimitValue);
            if (!isNaN(oosLowerLimitValue)) values.push(oosLowerLimitValue);
            if (!isNaN(oocLimitValue)) values.push(oocLimitValue);
            if (!isNaN(oocLowerLimitValue)) values.push(oocLowerLimitValue);
            if (!isNaN(targetValue)) values.push(targetValue);
            minY = Math.min(...values);
            maxY = Math.max(...values);
        }

        if (minX === maxX) {
            minX = minX - 1000;
            maxX = maxX + 1000;
        }
        if (minY === maxY) {
            minY = minY - 1;
            maxY = maxY + 1;
        }

        var paddingX = Math.max(500, Math.abs(maxX - minX) * 0.05);
        var paddingY = Math.max(0.5, Math.abs(maxY - minY) * 0.1);
        xAxis.min = new Date(minX - paddingX);
        xAxis.max = new Date(maxX + paddingX);
        yAxis.min = minY - paddingY;
        yAxis.max = maxY + paddingY;
        updateLimitLines();
    }

    Connections {
        target: chartCard.seriesModel
        enabled: chartCard.seriesModel

        property int previousRowCount: 0

        function onBoundsChanged() {
            var currentRowCount = chartCard.seriesModel ? chartCard.seriesModel.rowCount() : 0;

            if (!chartCard.seriesModel || !chartCard.seriesModel.hasData) {
                lineSeries.clear();
                chartCard.resetAxesToDefault();
                previousRowCount = currentRowCount;
                return;
            }

            if (previousRowCount === 0 && currentRowCount > 0) {
                chartCard.seriesModel.force_rebuild();
                chartCard.updateMapperBinding();
            }

            previousRowCount = currentRowCount;
            chartCard.updateAxesFromSeries();
        }
    }
}
