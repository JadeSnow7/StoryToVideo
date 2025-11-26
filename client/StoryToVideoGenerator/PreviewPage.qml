// PreviewPage.qml
import QtQuick 2.6            // 兼容 Qt 5.8.0
import QtQuick.Controls 2.1   // 兼容 Qt 5.8.0
import QtQuick.Layouts 1.2    // 兼容 Qt 5.8.0
import QtMultimedia 5.8       // 兼容 Qt 5.8.0 的多媒体模块

Page {
    id: previewPage
    property var storyId: "STORY-001" // 接收故事 ID
    title: "成品预览 (" + storyId + ")"

    // 模拟视频源路径
    // 注意: 实际项目中需要将视频文件放入 QRC 资源系统或本地文件路径
    property string videoSource: "qrc:/assets/placeholder.mp4"

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
            Layout.fillWidth: true
            Layout.preferredHeight: 450 // 视频播放器固定高度
            color: "black" // 播放器背景

            Video {
                id: videoPlayer
                source: videoSource
                anchors.fill: parent

                // 确保视频填充整个区域并保持比例
                fillMode: VideoOutput.PreserveAspectFit
            }

            // 简单的播放控制 UI
            RowLayout {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 10
                spacing: 10

                Button {
                    text: videoPlayer.playbackState === Video.PlayingState ? "暂停" : "播放"
                    onClicked: {
                        if (videoPlayer.playbackState === Video.PlayingState) {
                            videoPlayer.pause();
                        } else {
                            videoPlayer.play();
                        }
                    }
                }

                Button {
                    text: "停止"
                    onClicked: videoPlayer.stop()
                }
            }
        }

        // --- 导出功能区域 ---
        Button {
            text: "Export Video (导出成品文件)"
            Layout.alignment: Qt.AlignRight

            onClicked: {
                // TODO: [后端接口]
                // 1. 调用 C++ VideoProcessor.exportVideo(storyId)
                // 2. 弹出文件保存对话框

                console.log("启动视频文件导出功能...");
            }
        }

        // 返回按钮
        Button {
            text: "返回资产库"
            Layout.alignment: Qt.AlignLeft
            onClicked: {
                // 返回 StackView 的最底层，即 AssetsPage
                pageStack.clear();
            }
        }
    }
}
