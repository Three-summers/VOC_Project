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
    
    // 规格界限 (OOS) 和 控制界限 (OOC) 的值
    property real oosLimitValue: 90.0  
    property real oocLimitValue: 80.0
    property bool showLimits: false

    property var chartStyle: {
        "v1": {
            // OOS: R220, G82, B82
            "oosColor": Qt.rgba(220/255, 82/255, 82/255, 1.0),
            // OOC: R220, G81, B52
            "oocColor": Qt.rgba(220/255, 81/255, 52/255, 1.0),
            // Chart: R128, G0, B128
            "mainColor": Qt.rgba(128/255, 0/255, 128/255, 1.0)
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

        Text {
            text: chartCard.chartTitle
            font.bold: true
            font.pixelSize: Components.UiTheme.fontSize("subtitle")
            color: Components.UiTheme.color("textPrimary")
            Layout.alignment: Qt.AlignHCenter
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
            legend.alignment: Qt.AlignBottom
            legend.labelColor: Components.UiTheme.color("textPrimary")
            
            margins.top: Components.UiTheme.spacing("sm")
            margins.bottom: Components.UiTheme.spacing("sm")
            margins.left: Components.UiTheme.spacing("md")
            margins.right: Components.UiTheme.spacing("md")

            ValueAxis {
                id: xAxis
                min: 0
                max: 10
                labelFormat: "%.0f"
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
                labelsFont.pixelSize: Components.UiTheme.fontSize("caption")
                titleFont.pixelSize: Components.UiTheme.fontSize("caption")
                labelsColor: Components.UiTheme.color("textSecondary")
                gridLineColor: Components.UiTheme.color("outline")
            }

            // -----------------------------------------------------------------
            // 1. OOS Series (规格界限) - 实线
            // -----------------------------------------------------------------
            LineSeries {
                id: oosSeries
                name: "OOS"
                axisX: xAxis
                axisY: yAxis
                color: chartCard.chartStyle.v1.oosColor
                style: Qt.SolidLine // 图片要求：实线
                width: 1.5 * Components.UiTheme.controlScale
                visible: chartCard.showLimits
                useOpenGL: chartView.width > 0 && chartView.height > 0 // 开启 OpenGL 加速渲染
            }

            // -----------------------------------------------------------------
            // 2. OOC Series (控制界限) - 虚线
            // -----------------------------------------------------------------
            LineSeries {
                id: oocSeries
                name: "OOC"
                axisX: xAxis
                axisY: yAxis
                color: chartCard.chartStyle.v1.oocColor
                style: Qt.DashLine // 图片要求：虚线
                width: 1.5 * Components.UiTheme.controlScale
                visible: chartCard.showLimits
                useOpenGL: chartView.width > 0 && chartView.height > 0
            }

            // -----------------------------------------------------------------
            // 3. Main Data Series (主数据) - 实线
            // -----------------------------------------------------------------
            LineSeries {
                id: lineSeries
                name: "Measured"
                axisX: xAxis
                axisY: yAxis
                color: chartCard.chartStyle.v1.mainColor // 图片要求：紫色 RGB(128,0,128)
                style: Qt.SolidLine
                width: Math.max(2, 2.5 * Components.UiTheme.controlScale)
                useOpenGL: chartView.width > 0 && chartView.height > 0
            }

            VXYModelMapper {
                id: mapper
                // 绑定将在 updateMapperBinding 中处理
            }
        }
    }

    // 优化后的绘制函数：绘制一条极其长的线，利用 Viewport 裁剪，避免滚动时重绘
    function updateLimitLines() {
        if (!showLimits) return;
        
        oosSeries.clear();
        oocSeries.clear();

        // 定义一个足够大的范围，覆盖所有可能的 X 轴数据（例如时间戳）
        // 假设是普通数值或 Unix 时间戳，这个范围足够大
        var hugeMin = -2000000000; 
        var hugeMax =  4000000000; 

        // 绘制 OOS 线
        oosSeries.append(hugeMin, oosLimitValue);
        oosSeries.append(hugeMax, oosLimitValue);

        // 绘制 OOC 线
        oocSeries.append(hugeMin, oocLimitValue);
        oocSeries.append(hugeMax, oocLimitValue);
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
        
        // 关键逻辑：确保 Y 轴范围包含 OOS 和 OOC 线，否则界限线可能跑到屏幕外
        if (showLimits) {
            // 获取所有关键值的最小值和最大值
            var allValues = [minY, maxY, oosLimitValue, oocLimitValue];
            minY = Math.min(...allValues);
            maxY = Math.max(...allValues);
        }

        var visibleWindow = chartCard.seriesModel.maxRows ? Math.max(10, chartCard.seriesModel.maxRows) : 60;
        
        // X 轴逻辑保持不变
        if (minX === maxX) {
            minX = minX - 1;
            maxX = maxX + 1;
        } else if (maxX - minX > visibleWindow) {
            minX = maxX - visibleWindow;
        }

        // Y 轴增加一点 Padding
        if (minY === maxY) {
            minY = minY - 1;
            maxY = maxY + 1;
        }
        
        var paddingX = Math.max(0.5, Math.abs(maxX - minX) * 0.05);
        var paddingY = Math.max(0.5, Math.abs(maxY - minY) * 0.1);
        
        xAxis.min = minX - paddingX;
        xAxis.max = maxX + paddingX;
        yAxis.min = minY - paddingY;
        yAxis.max = maxY + paddingY;
    }

    function resetAxesToDefault() {
        xAxis.min = 0;
        xAxis.max = 10;
        yAxis.min = 0;
        yAxis.max = 100;
    }

    function updateMapperBinding() {
        if (chartCard.seriesModel) {
            mapper.xColumn = chartCard.xColumn;
            mapper.yColumn = chartCard.yColumn;
            mapper.model = chartCard.seriesModel;
            mapper.series = lineSeries;
        } else {
            mapper.series = null;
            mapper.model = null;
        }
    }


    Component.onCompleted: {
        updateMapperBinding();
        updateLimitLines(); // 初始化绘制一次
    }

    // 仅当界限数值改变时才重绘
    onOosLimitValueChanged: updateLimitLines()
    onOocLimitValueChanged: updateLimitLines()
    onShowLimitsChanged: updateLimitLines()

    onSeriesModelChanged: {
        if (chartCard.seriesModel) {
            lineSeries.clear();
            updateAxesFromSeries();
            if (typeof chartCard.seriesModel.force_rebuild === "function") {
                chartCard.seriesModel.force_rebuild();
            }
        } else {
            lineSeries.clear();
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
        var minX = 0, maxX = 0, minY = 0, maxY = 0;
        if (dataPoints.length > 0) {
            minX = dataPoints[0].x;
            maxX = dataPoints[0].x;
            minY = dataPoints[0].y;
            maxY = dataPoints[0].y;
        }

        for (var i = 0; i < dataPoints.length; i++) {
            var point = dataPoints[i];
            lineSeries.append(point.x, point.y);
            if (point.x < minX) minX = point.x;
            if (point.x > maxX) maxX = point.x;
            if (point.y < minY) minY = point.y;
            if (point.y > maxY) maxY = point.y;
        }
        
        if (dataPoints.length === 0) {
            xAxis.min = 0; xAxis.max = 10;
            yAxis.min = 0; yAxis.max = 100;
        }
        // 如果是直接赋值 dataPoints 模式，也需要在这里更新轴范围
        // (省略了详细的 Y 轴自动缩放逻辑，建议尽量使用 SeriesModel)
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
