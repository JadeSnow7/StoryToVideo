// PreviewPage.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import QtQuick.Dialogs

Page {
    id: previewPage

    // macOS 风格配色 & 字体
    readonly property color macBackground: "#F5F5F7"
    readonly property color macCard: "#FFFFFF"
    readonly property color macBorder: "#D1D5DB"
    readonly property color macTextPrimary: "#0B0B0F"
    readonly property color macTextSecondary: "#6B7280"
    readonly property string macTitleFont: "-apple-system"
    readonly property string macBodyFont: "-apple-system"

    property string projectId: ""
    property string videoSource: ""
    property bool showStoryboardButton: false // 默认为 false
    property string lastExportPath: ""

    title: "成品预览 (" + projectId + ")"

    // 添加日志输出以便调试
    Component.onCompleted: {
        console.log("PreviewPage loaded, videoSource:", videoSource);
        console.log("Available multimedia backends:", QtMultimedia.availableBackends);
    }

    Rectangle {
        anchors.fill: parent
        color: macBackground

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        // ========== 顶部导航栏 ==========
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Button {
                text: "← 返回"
                font.family: macBodyFont
                background: Rectangle {
                    radius: 10
                    color: "transparent"
                    border.color: macBorder
                }
                contentItem: Text {
                    text: parent.text
                    color: macTextPrimary
                    font.pixelSize: 14
                    font.family: macBodyFont
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: {
                    videoPlayer.stop();
                    pageStack.pop();
                }
            }

            Text {
                text: qsTr("成品预览")
                font.pixelSize: 20
                font.bold: true
                font.family: macTitleFont
                color: macTextPrimary
                Layout.fillWidth: true
            }

            // 项目 ID 标签
            Text {
                text: qsTr("项目: %1").arg(projectId)
                font.pixelSize: 13
                font.family: macBodyFont
                color: macTextSecondary
            }
        }

        Label {
            text: "最终视频合成预览"
            font.pointSize: 15
            font.bold: true
            font.family: macTitleFont
            color: macTextPrimary
        }

        // --- 视频播放器区域 ---
        Rectangle {
            id: videoContainer
            Layout.fillWidth: true
            Layout.preferredHeight: 450
            color: "#1C1C1E"
            radius: 16

            // 【关键修改】Qt 6 中 MediaPlayer 使用 videoOutput 属性指向 VideoOutput 组件
            MediaPlayer {
                id: videoPlayer
                source: videoSource
                videoOutput: videoOutput

                // 添加事件监听用于调试
                onErrorOccurred: console.error("MediaPlayer error:", error, errorString)
                onMediaStatusChanged: {
                    console.log("MediaPlayer status:", mediaStatus);
                    if (mediaStatus === MediaPlayer.LoadedMedia) {
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
                    font.family: macBodyFont
                    background: Rectangle {
                        radius: 8
                        color: "white"
                        opacity: parent.down ? 0.9 : 1.0
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "black"
                        font.pixelSize: 13
                        font.family: macBodyFont
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: {
                        if (videoPlayer.playbackState === MediaPlayer.PlayingState) {
                            videoPlayer.pause();
                        } else {
                            if (videoPlayer.status === MediaPlayer.Loaded) {
                                videoPlayer.play();
                            } else {
                                console.log("等待视频加载...");
                                videoPlayer.play();
                            }
                        }
                    }
                }

                Button {
                    text: "停止"
                    font.family: macBodyFont
                    background: Rectangle {
                        radius: 8
                        color: "#FF453A" // macOS Red
                        opacity: parent.down ? 0.9 : 1.0
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "white"
                        font.pixelSize: 13
                        font.family: macBodyFont
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: {
                        videoPlayer.stop();
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
            color: macCard
            radius: 12
            border.color: macBorder

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12

                Text {
                    text: "视频信息: " +
                          (videoPlayer.hasVideo ? "有视频" : "无视频") + " | " +
                          (videoPlayer.hasAudio ? "有音频" : "无音频")
                    font.pointSize: 11
                    font.family: macBodyFont
                    color: macTextPrimary
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
                    font.pointSize: 11
                    font.family: macBodyFont
                    color: macTextSecondary
                }
            }
        }

        // --- 导出功能区域 ---
        RowLayout {
            Layout.fillWidth: true
            spacing: 15

            Button {
                text: "← 返回故事板"
                visible: showStoryboardButton
                font.family: macBodyFont
                background: Rectangle {
                    radius: 10
                    color: "transparent"
                    border.color: macBorder
                }
                contentItem: Text {
                    text: parent.text
                    color: macTextPrimary
                    font.pixelSize: 14
                    font.family: macBodyFont
                    horizontalAlignment: Text.AlignHCenter
                }
                onClicked: {
                    videoPlayer.stop();
                    pageStack.pop();
                }
            }

            Item { Layout.fillWidth: true }

            Button {
                id: exportButton
                text: qsTr("导出视频")
                font.pixelSize: 15
                font.bold: true
                font.family: macBodyFont
                
                property bool isExporting: false

                background: Rectangle {
                    radius: 14
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#4A8BFF" }
                        GradientStop { position: 1.0; color: "#2D6BFF" }
                    }
                }
                contentItem: Text {
                    text: parent.text
                    color: "white"
                    font.pixelSize: 15
                    font.bold: true
                    font.family: macBodyFont
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onClicked: {
                    if (!isExporting) {
                        if (!videoSource || videoSource.length === 0) {
                            exportErrorDialog.text = qsTr("没有可导出的视频地址");
                            exportErrorDialog.open();
                            return;
                        }
                        saveDialog.open();
                    }
                }
            }
        }
    }
    }

    FileDialog {
        id: saveDialog
        title: qsTr("选择导出视频路径")
        nameFilters: ["MP4 files (*.mp4)"]
        fileMode: FileDialog.SaveFile
        onAccepted: {
            var selected = saveDialog.selectedFile || saveDialog.fileUrl;
            var localPath = selected.toString().replace("file://", "");
            if (localPath.toLowerCase().lastIndexOf(".mp4") !== localPath.length - 4) {
                localPath = localPath + ".mp4";
            }
            lastExportPath = localPath;
            exportButton.isExporting = true;
            exportButton.text = qsTr("导出中...");
            videoExporter.exportVideo(videoSource, localPath);
        }
        onRejected: {
            exportButton.isExporting = false;
            exportButton.text = qsTr("导出视频");
        }
    }

    Connections {
        target: videoExporter
        onExportFinished: {
            exportButton.isExporting = false;
            exportButton.text = qsTr("导出视频");
            exportSuccessDialog.text = qsTr("视频已成功导出到本地！\n\n文件位置: %1").arg(lastExportPath);
            exportSuccessDialog.open();
        }
        onExportFailed: {
            exportButton.isExporting = false;
            exportButton.text = qsTr("导出视频");
            exportErrorDialog.text = error;
            exportErrorDialog.open();
        }
    }

    Dialog {
        id: exportSuccessDialog
        title: qsTr("导出成功")
        modal: true
        anchors.centerIn: parent
        standardButtons: Dialog.Ok
        property string text: ""
        background: Rectangle {
            radius: 12
            color: macCard
            border.color: macBorder
        }
        contentItem: Label {
            text: exportSuccessDialog.text
            wrapMode: Text.WordWrap
            width: 280
        }
    }

    Dialog {
        id: exportErrorDialog
        title: qsTr("导出失败")
        modal: true
        anchors.centerIn: parent
        standardButtons: Dialog.Ok
        property string text: ""
        background: Rectangle {
            radius: 12
            color: macCard
            border.color: macBorder
        }
        contentItem: Label {
            text: exportErrorDialog.text
            wrapMode: Text.WordWrap
            width: 280
        }
    }
}
