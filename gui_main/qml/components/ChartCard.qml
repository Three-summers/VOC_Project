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
    color: "white"
    border.color: "#ccc"
    border.width: Math.max(1, Components.UiTheme.controlScale)
    radius: Components.UiTheme.radius("sm")

    property string chartTitle: "Time Series Data"
    property var dataPoints: []
    property var seriesModel: null
    property int xColumn: 0
    property int yColumn: 1
    property real scaleFactor: Components.UiTheme.controlScale
    readonly property real effectiveScale: Components.UiTheme.controlScale

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Components.UiTheme.spacing("md")

        Text {
            text: chartCard.chartTitle
            font.bold: true
            font.pixelSize: Components.UiTheme.fontSize("subtitle")
            Layout.alignment: Qt.AlignHCenter
        }

        ChartView {
            id: chartView
            Layout.fillWidth: true
            Layout.fillHeight: true
            // antialiasing: false // 禁用抗锯齿，避免触发 FBO
            backgroundRoundness: 0
            dropShadowEnabled: false
            animationOptions: ChartView.NoAnimation
            antialiasing: true
            // animationOptions: ChartView.SeriesAnimations
            titleFont.pixelSize: Components.UiTheme.fontSize("body")
            margins.top: Components.UiTheme.spacing("sm")
            margins.bottom: Components.UiTheme.spacing("sm")
            margins.left: Components.UiTheme.spacing("md")
            margins.right: Components.UiTheme.spacing("md")

            title: chartCard.chartTitle
            legend.visible: false

            ValueAxis {
                id: xAxis
                min: 0
                max: 10
                labelFormat: "%d"
                tickCount: 5
                labelsFont.pixelSize: Components.UiTheme.fontSize("caption")
                titleFont.pixelSize: Components.UiTheme.fontSize("caption")
            }

            ValueAxis {
                id: yAxis
                min: 0
                max: 100
                labelFormat: "%d"
                tickCount: 5
                labelsFont.pixelSize: Components.UiTheme.fontSize("caption")
                titleFont.pixelSize: Components.UiTheme.fontSize("caption")
            }

            LineSeries {
                id: lineSeries
                axisX: xAxis
                axisY: yAxis
                color: "red" // 使用红色提升可视性
                width: Math.max(2, 2.5 * Components.UiTheme.controlScale)
            }

            VXYModelMapper {
                id: mapper
                series: chartCard.seriesModel ? lineSeries : null
            }
        }
    }

    function updateAxesFromSeries() {
        if (!chartCard.seriesModel || !chartCard.seriesModel.hasData)
        return;
        var minX = chartCard.seriesModel.minX;
        var maxX = chartCard.seriesModel.maxX;
        var minY = chartCard.seriesModel.minY;
        var maxY = chartCard.seriesModel.maxY;
        var visibleWindow = chartCard.seriesModel.maxRows ? Math.max(10, chartCard.seriesModel.maxRows) : 60;
        if (minX === maxX) {
            minX = minX - 1;
            maxX = maxX + 1;
        } else if (maxX - minX > visibleWindow) {
            minX = maxX - visibleWindow;
        }
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

    Component.onCompleted: updateMapperBinding()

    onSeriesModelChanged: {
        if (chartCard.seriesModel) {
            lineSeries.clear();
            updateAxesFromSeries();
        } else {
            lineSeries.clear();
        }
        updateMapperBinding();
    }

    onXColumnChanged: updateMapperBinding()
    onYColumnChanged: updateMapperBinding()

    onDataPointsChanged: {
        if (chartCard.seriesModel)
        return;
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

        // Adjust axes based on data (using fixed range for now)
        // xAxis.min = minX;
        // xAxis.max = maxX + 1;
        // yAxis.min = minY - 5;
        // yAxis.max = maxY + 5;
        // console.log("  Axes adjusted: X[" + xAxis.min + "," + xAxis.max + "] Y[" + yAxis.min + "," + yAxis.max + "]");

        if (dataPoints.length === 0) {
            // Reset axes if no data
            xAxis.min = 0; xAxis.max = 10;
            yAxis.min = 0; yAxis.max = 100;
        }
    }

    Connections {
        target: chartCard.seriesModel
        enabled: chartCard.seriesModel
        function onBoundsChanged() {
            chartCard.updateAxesFromSeries();
        }
    }
}
