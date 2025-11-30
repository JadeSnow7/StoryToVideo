
// StoryboardPage.qml
import QtQuick 2.6            // 兼容 Qt 5.8.0
import QtQuick.Controls 2.1   // 兼容 Qt 5.8.0
import QtQuick.Layouts 1.2    // 兼容 Qt 5.8.0

Page {
    id: storyboardPage
    property var storyId: "" // 从 CreatePage 接收的故事ID
    property var storyTitle: "加载中..." // 接收标题

    property var actualShotsModel: []

    title: "分镜管理 (" + storyId + ")"

    // --- 模拟分镜数据模型 ---
//    property ListModel shotsModel: ListModel {
//        ListElement { shotId: 1; title: "雨中追逐"; status: "已生成"; statusColor: "#4CAF50" } // 绿色
//        ListElement { shotId: 2; title: "城市夜景"; status: "未生成"; statusColor: "#9E9E9E" } // 灰色
//        ListElement { shotId: 3; title: "最终对决"; status: "生成中..."; statusColor: "#2196F3" } // 蓝色
//        ListElement { shotId: 4; title: "镜头四"; status: "失败"; statusColor: "#F44336" } // 红色
//        ListElement { shotId: 5; title: "镜头五"; status: "已生成"; statusColor: "#4CAF50" }
//    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20 // 页面内边距
        spacing: 20

        Label { text: "当前项目分镜列表：" }

        // --- 横向滚动区域 (使用 Flickable 替代 ScrollView) ---
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 280 // 固定卡片展示区域高度
            color: "#F0F0F0" // 背景色便于观察区域

            Flickable {
                id: horizontalFlickable
                anchors.fill: parent
                contentWidth: shotsListView.width // 内容宽度由 ListView 决定
                contentHeight: parent.height
                clip: true // 裁剪滚动溢出的内容

                ListView {
                    id: shotsListView
                    orientation: ListView.Horizontal
                    spacing: 15
                    model: actualShotsModel

                    // delegate: 这里嵌入分镜卡片的结构，或者使用单独的 ShotCard.qml
                    delegate: Component {
                        // 统一使用 Rectangle 作为分镜卡片
                        Rectangle {
                            width: 250; height: 260
                            color: "white"
                            radius: 8
                            border.color: model.statusColor
                            border.width: 2

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 20
                                spacing: 8

                                // 标题和状态
                                RowLayout {
                                    Label { text: "SHOT " + model.shotId; font.bold: true }
                                    Label { text: model.title; Layout.fillWidth: true }

                                    // 状态标签
                                    Rectangle {
                                        color: model.statusColor
                                        radius: 4
                                        Text {
                                            text: model.status
                                            color: "white"
                                            font.pointSize: 9
                                            anchors.centerIn: parent
                                            anchors.margins: 4
                                        }
                                    }
                                }

                                // 缩略图占位符
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 150
                                    color: "#CCCCCC"
                                    Text { anchors.centerIn: parent; text: "缩略图预览" }
                                }

                                // 详情按钮 (底部)
                                Button {
                                    text: "详情"
                                    onClicked: {
                                        // 传递一个明确包含所有必要字段的对象
                                        pageStack.push(Qt.resolvedUrl("ShotDetailPage.qml"), {
                                            shotData: {
                                                shotId: model.shotId,
                                                title: model.title,
                                                prompt: model.prompt, // 确保 prompt 字段被传递
                                                status: model.status
                                                // ... 确保所有 ShotDetailPage 需要的属性都在这里
                                            }
                                        });
                                    }
                                }
                        }
                    }
                }
            }
        }

        // 底部：生成视频按钮
        Button {
            text: "一键批量生成视频"
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredHeight: 50

            onClicked: {
                // TODO: [后端接口] 调用 C++ VideoProcessor 触发合成任务
                console.log("启动视频合成任务...");
            }
        }
    }
}
}
