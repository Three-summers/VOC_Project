pragma Singleton
import QtQuick

QtObject {
    id: constants

    // 通道限值默认值
    readonly property real defaultOocUpper: 80
    readonly property real defaultOocLower: 20
    readonly property real defaultOosUpper: 90
    readonly property real defaultOosLower: 10
    readonly property real defaultTarget: 50

    // 限值显示开关默认值
    readonly property bool defaultShowOocUpper: true
    readonly property bool defaultShowOocLower: true
    readonly property bool defaultShowOosUpper: true
    readonly property bool defaultShowOosLower: true
    readonly property bool defaultShowTarget: true

    // 防抖定时器间隔
    readonly property int resizeDebounceInterval: 32

    // 便捷函数：返回完整默认限值对象
    function defaultLimits() {
        return {
            oocUpper: defaultOocUpper,
            oocLower: defaultOocLower,
            oosUpper: defaultOosUpper,
            oosLower: defaultOosLower,
            target: defaultTarget
        }
    }
}
