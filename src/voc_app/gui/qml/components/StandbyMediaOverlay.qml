import QtQuick
import QtMultimedia

Item {
    id: overlay

    anchors.fill: parent
    z: 10000
    visible: false
    focus: visible

    property var mediaItems: []
    property int imageDurationMs: 10000
    property int mediaIndex: -1
    property int consecutiveFailures: 0

    function start() {
        if (!mediaItems || mediaItems.length === 0)
            return

        visible = true
        mediaIndex = -1
        consecutiveFailures = 0
        advance()
        forceActiveFocus()
    }

    function stop() {
        imageTimer.stop()
        player.stop()
        player.source = ""
        image.source = ""
        visible = false
    }

    function advance() {
        if (!visible || !mediaItems || mediaItems.length === 0) {
            stop()
            return
        }

        imageTimer.stop()
        player.stop()
        mediaIndex = (mediaIndex + 1) % mediaItems.length
        const entry = mediaItems[mediaIndex]
        image.visible = entry.kind === "image"
        videoOutput.visible = entry.kind === "video"

        if (entry.kind === "image") {
            image.source = entry.url
            imageTimer.restart()
        } else {
            player.source = entry.url
            player.play()
        }
    }

    function skipFailedItem() {
        if (!visible)
            return

        consecutiveFailures += 1
        if (consecutiveFailures >= mediaItems.length) {
            stop()
            return
        }
        advance()
    }

    Rectangle {
        anchors.fill: parent
        color: "black"
    }

    Image {
        id: image

        anchors.fill: parent
        asynchronous: true
        fillMode: Image.PreserveAspectFit
        visible: false

        onStatusChanged: {
            if (status === Image.Ready)
                overlay.consecutiveFailures = 0
            else if (status === Image.Error)
                overlay.skipFailedItem()
        }
    }

    VideoOutput {
        id: videoOutput

        anchors.fill: parent
        fillMode: VideoOutput.PreserveAspectFit
        visible: false
    }

    Timer {
        id: imageTimer

        interval: overlay.imageDurationMs
        repeat: false
        onTriggered: overlay.advance()
    }

    MediaPlayer {
        id: player

        videoOutput: videoOutput
        audioOutput: AudioOutput {
            muted: true
        }

        onMediaStatusChanged: {
            if (mediaStatus === MediaPlayer.EndOfMedia) {
                overlay.consecutiveFailures = 0
                overlay.advance()
            }
        }
        onErrorOccurred: overlay.skipFailedItem()
    }
}
