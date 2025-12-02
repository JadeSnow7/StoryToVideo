// PreviewPage.qml
import QtQuick 2.6
import QtQuick.Controls 2.1
import QtQuick.Layouts 1.2
import QtMultimedia 5.8

Page {
    id: previewPage

    property string projectId: ""
    property string videoSource: ""

    title: "成品预览 (" + projectId + ")"

    // 添加日志输出以便调试
    Component.onCompleted: {
        console.log("PreviewPage loaded, videoSource:", videoSource);
        console.log("Available multimedia backends:", QtMultimedia.availableBackends);
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        Label {
            text: "最终视频合成预览"
            font.pointSize: 14
            font.bold: true
        }

        // --- 视频播放器区域 ---
        Rectangle {
            id: videoContainer
            Layout.fillWidth: true
            Layout.preferredHeight: 450
            color: "black"

            // 【关键修改】在 Qt 5.8 中，有时需要先创建 MediaPlayer，再创建 VideoOutput
            MediaPlayer {
                id: videoPlayer
                source: videoSource

                // 添加事件监听用于调试
                onError: console.error("MediaPlayer error:", error, errorString)
                onStatusChanged: {
                    console.log("MediaPlayer status:", status);
                    if (status === MediaPlayer.Loaded) {
                        console.log("视频已加载，时长:", duration, "ms");
                    }
                }
                onHasVideoChanged: console.log("Has video:", hasVideo)
                onHasAudioChanged: console.log("Has audio:", hasAudio)

                // 自动播放（可选）
                autoPlay: false
            }

            VideoOutput {
                id: videoOutput
                anchors.fill: parent
                source: videoPlayer
                fillMode: VideoOutput.PreserveAspectFit

                // 添加备用显示
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 0.8
                    height: 60
                    color: "#80000000"
                    visible: !videoPlayer.hasVideo && videoPlayer.status === MediaPlayer.Loaded

                    Text {
                        anchors.centerIn: parent
                        text: "视频无法显示（仅音频）"
                        color: "white"
                        font.pointSize: 12
                    }
                }
            }

            // 视频加载状态指示器
            BusyIndicator {
                anchors.centerIn: parent
                running: videoPlayer.status === MediaPlayer.Loading ||
                        videoPlayer.status === MediaPlayer.Buffering
                visible: running
            }

            // 简单的播放控制 UI
            RowLayout {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 10
                spacing: 10
                z: 2

                Button {
                    text: videoPlayer.playbackState === MediaPlayer.PlayingState ? "暂停" : "播放"
                    onClicked: {
                        if (videoPlayer.playbackState === MediaPlayer.PlayingState) {
                            videoPlayer.pause();
                        } else {
                            // 先确保视频已准备就绪
                            if (videoPlayer.status === MediaPlayer.Loaded) {
                                videoPlayer.play();
                            } else {
                                console.log("等待视频加载...");
                                videoPlayer.play(); // 尝试播放
                            }
                        }
                    }
                }

                Button {
                    text: "停止"
                    onClicked: {
                        videoPlayer.stop();
                        // 重置到开始位置
                        videoPlayer.seek(0);
                    }
                }

                // 添加进度显示
                Label {
                    color: "white"
                    text: {
                        if (videoPlayer.duration > 0) {
                            var current = Math.floor(videoPlayer.position / 1000);
                            var total = Math.floor(videoPlayer.duration / 1000);
                            return current + "s / " + total + "s";
                        }
                        return "0s / 0s";
                    }
                }
            }
        }

        // 添加格式信息显示
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: "#f0f0f0"
            radius: 5

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10

                Text {
                    text: "视频信息: " +
                          (videoPlayer.hasVideo ? "有视频" : "无视频") + " | " +
                          (videoPlayer.hasAudio ? "有音频" : "无音频")
                    font.pointSize: 10
                }

                Text {
                    text: "状态: " +
                          (videoPlayer.status === MediaPlayer.NoMedia ? "无媒体" :
                           videoPlayer.status === MediaPlayer.Loading ? "加载中" :
                           videoPlayer.status === MediaPlayer.Loaded ? "已加载" :
                           videoPlayer.status === MediaPlayer.Buffering ? "缓冲中" :
                           videoPlayer.status === MediaPlayer.Stalled ? "停滞" :
                           videoPlayer.status === MediaPlayer.EndOfMedia ? "播放结束" :
                           "未知状态")
                    font.pointSize: 10
                }
            }
        }

        // --- 导出功能区域 ---
        Button {
            text: "Export Video (导出成品文件)"
            Layout.alignment: Qt.AlignRight

            onClicked: {
                console.log("启动视频文件导出功能...");
            }
        }

        // 返回按钮
        Button {
            text: "返回资产库"
            Layout.alignment: Qt.AlignLeft
            onClicked: {
                videoPlayer.stop();
                pageStack.clear();
            }
        }
    }
}
