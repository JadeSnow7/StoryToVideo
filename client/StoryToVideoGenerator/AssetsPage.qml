// AssetsPage.qml
import QtQuick 2.6          // 兼容 Qt 5.8.0 的 QtQuick 版本
import QtQuick.Controls 2.1   // ✅ 兼容 Qt 5.8.0 的 Controls 版本
import QtQuick.Layouts 1.2    // 兼容 Qt 5.8.0 的 Layouts 版本

Page {
    id: assetsPage
    title: "资产库"

    // 假设 pageStack 在 main.qml 中定义，并作为 context 暴露出来
    // property alias pageStack: appWindow.pageStack // 如果需要，可以这样设置别名

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        // 顶部：搜索与新建
        RowLayout {
            width: parent.width

            TextField {
                Layout.fillWidth: true;
                placeholderText: "按故事名称或生成时间筛选..."
                // TODO: 绑定搜索逻辑
            }

            Button {
                text: "新建故事"
                onClicked: {
                    // 导航到新建故事页 (CreatePage.qml)
                    pageStack.push(Qt.resolvedUrl("CreatePage.qml"))
                }
            }
        }

        // 列表区域：使用 ScrollView 包含 Flow 布局实现卡片网格
        Rectangle {
            // 确保 ScrollView 被正确导入 (Controls 2.1)
            Layout.fillWidth: true
            Layout.fillHeight: true

            Flow {
                width: assetsPage.width - 40 // 减去 padding
                spacing: 15

                // 模拟故事数据
                Repeater {
                    model: 8 // 假设有 8 个故事卡片

                    // --- 故事资产卡片组件 ---
                    Rectangle {
                        width: 200
                        height: 180
                        color: "#EEEEEE"
                        radius: 8
                        border.color: "#CCCCCC"
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10

                            // 缩略图占位符 (极简模式)
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 110
                                color: "#DCDCDC"
                                Text {
                                    anchors.centerIn: parent;
                                    text: "缩略图\n(未生成)"
                                    color: "gray"
                                }
                            }

                            Label {
                                text: "故事标题 " + (index + 1)
                                font.bold: true
                            }
                            Label {
                                text: "生成时间: 2025-11-21"
                                font.pointSize: 9
                                color: "#666666"
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    // 点击卡片 -> 跳转至 PreviewPage.qml
                                    pageStack.push(Qt.resolvedUrl("PreviewPage.qml"), {
                                        storyId: "ASSET-" + index
                                    })
                                }
                            }
                        }
                    }
                    // --- 故事资产卡片组件结束 ---
                }
            }
        }
    }
}
