import QtQuick 2.6
import QtQuick.Controls 2.1
import QtQuick.Layouts 1.2
import QtMultimedia 5.8
import QtQuick.Dialogs 1.2

Page {
    id: previewPage
    title: "视频预览"
    property string videoPath: ""

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        Label {
            text: "视频预览"
            font.pointSize: 14
            font.bold: true
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 450
            color: "black"

            // Qt 5.8 推荐写法
            MediaPlayer {
                id: mediaPlayer
                source: videoPath
                autoPlay: false
            }

            VideoOutput {
                anchors.fill: parent
                source: mediaPlayer
                fillMode: VideoOutput.PreserveAspectFit
            }

            RowLayout {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 10
                spacing: 10

                Button {
                    text: mediaPlayer.playbackState === MediaPlayer.PlayingState ? "暂停" : "播放"
                    onClicked: {
                        if (mediaPlayer.playbackState === MediaPlayer.PlayingState)
                            mediaPlayer.pause()
                        else
                            mediaPlayer.play()
                    }
                }

                Button {
                    text: "停止"
                    onClicked: mediaPlayer.stop()
                }
            }
        }

        Button {
            text: "导出视频"
            Layout.alignment: Qt.AlignRight
            onClicked: saveDialog.open()
        }

        Button {
            text: "返回资产页"
            Layout.alignment: Qt.AlignLeft
            onClicked: pageStack.pop()
        }
    }

    FileDialog {
        id: saveDialog
        title: "选择导出视频路径"
        nameFilters: ["MP4 files (*.mp4)"]
        selectExisting: false
        onAccepted: {
            var localPath = fileUrl.replace("file:///", "")
            videoExporter.exportVideo(videoPath, localPath)
        }
    }

    Connections {
        target: videoExporter
        onExportFinished: console.log("导出成功:", msg)
        onExportFailed: console.log("导出失败:", error)
    }
}
