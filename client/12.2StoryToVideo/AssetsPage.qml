// AssetsPage.qml
import QtQuick 2.6
import QtQuick.Controls 2.1
import QtQuick.Layouts 1.2
import Qt.labs.folderlistmodel 2.1    // 用于读取本地文件目录

Page {
    id: assetsPage
    title: "资产库"
    Component.onCompleted: {
        console.log("AssetsPage loaded. assetsRoot =", assetsRoot)
    }

    // ⚠ 请你在这里填写资产文件夹路径，例如：
    // file:///C:/Users/admin/Desktop/Assert/
    // macOS: 改为本机存在的目录，避免无效路径阻断 UI
    property string assetsRoot: "file:///Users/huaodong/Movies/Videos/"   // 填绝对路径

    // 读取资产根目录下的所有子文件夹
    FolderListModel {
        id: folderModel
        folder: assetsRoot
        nameFilters: ["*"]
        showDirs: true
        showFiles: false
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        // 顶部搜索 + 新建按钮（原样保留）
        RowLayout {
            width: parent.width

            TextField {
                Layout.fillWidth: true;
                placeholderText: "按故事名称或生成时间筛选..."
            }

            Button {
                text: "新建故事"
                onClicked: {
                    pageStack.push(Qt.resolvedUrl("CreatePage.qml"))
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"

            Flow {
                width: assetsPage.width - 40
                spacing: 15

                // ★ 动态读取子文件夹数量
                Repeater {
                    model: folderModel.count

                    // 不展示根目录自身（第 0 项一般是 "."）
                    delegate: Rectangle {
                        width: 200
                        height: 180
                        color: "#EEEEEE"
                        radius: 8
                        border.color: "#CCCCCC"

                        // 当前子文件夹的绝对路径
                        property string folderPath: folderModel.get(index, "filePath")

                        // 缩略图路径 (thumb.jpg 或 thumb.png)
                        property string thumbPathJpg: folderPath + "/thumb.jpg"
                        property string thumbPathPng: folderPath + "/thumb.png"
                        property string thumbToShow: ""

                        Component.onCompleted: {
                            if (Qt.resolvedUrl(thumbPathJpg) !== "") {
                                thumbToShow = "file:///" + thumbPathJpg
                            } else if (Qt.resolvedUrl(thumbPathPng) !== "") {
                                thumbToShow = "file:///" + thumbPathPng
                            } else {
                                thumbToShow = ""
                            }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10

                            // 缩略图区域
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 110
                                color: "#DCDCDC"

                                Image {
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    fillMode: Image.PreserveAspectCrop
                                    visible: thumbToShow !== ""
                                    source: thumbToShow
                                }

                                // fallback 文本
                                Text {
                                    anchors.centerIn: parent
                                    visible: thumbToShow === ""
                                    text: "缩略图\n未找到"
                                    color: "gray"
                                }
                            }

                            Label {
                                text: folderPath.split("/").pop()  // 用文件夹名字当标题
                                font.bold: true
                            }

                            Label {
                                text: "本地资产文件夹"
                                font.pointSize: 9
                                color: "#666666"
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    // 视频路径：file:///xxx/video.mp4
                                    var videoPath = "file:///" + folderPath + "/video.mp4"

                                    console.log("打开视频:", videoPath)

                                    pageStack.push(Qt.resolvedUrl("PreviewPage.qml"), {
                                        videoPath: videoPath
                                    })
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

