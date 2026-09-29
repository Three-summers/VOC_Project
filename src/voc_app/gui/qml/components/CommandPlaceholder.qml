import QtQuick
import "." as Components

// 命令面板占位提示：用于当前页面没有可用操作的情况，
// 替代以前那些只打 console.log、没有任何实际动作的按钮。
Text {
    property string message: "本页暂无可用操作"

    width: parent ? parent.width : implicitWidth
    text: message
    wrapMode: Text.WordWrap
    horizontalAlignment: Text.AlignHCenter
    color: Components.UiTheme.color("textSecondary")
    font.pixelSize: Components.UiTheme.fontSize("body")
}
