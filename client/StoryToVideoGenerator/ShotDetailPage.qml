// ShotDetailPage.qml
import QtQuick 2.6            // 兼容 Qt 5.8.0
import QtQuick.Controls 2.1   // 兼容 Qt 5.8.0
import QtQuick.Layouts 1.2    // 兼容 Qt 5.8.0

Page {
    id: shotDetailPage

    // 接收从 StoryboardPage 传递来的分镜数据
    property var shotData: ({ title: "未命名分镜", status: "未生成", prompt: "一个孤独的宇航员站在火星表面", shotId: 0 })

    // 页面标题
    title: "分镜详情 (" + shotData.title + ")"

    // 内部状态，用于编辑
    property string currentPrompt: shotData.prompt || "无描述"
    property string narrationText: ""
    property string transitionEffect: "Crossfade"
    property string generationStatus: shotData.status

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        // --- 顶部状态与预览 ---
        RowLayout {
            width: parent.width
            Label { text: "当前状态：" + generationStatus; font.bold: true; Layout.fillWidth: true }

            // 预览图占位
            Rectangle {
                Layout.preferredWidth: 150
                Layout.preferredHeight: 100
                color: "#DCDCDC"
                Text { anchors.centerIn: parent; text: "分镜预览图" }
            }
        }

        // --- 可滚动编辑区域 (使用 Flickable 替代 ScrollView) ---
        Rectangle { // 外部 Rectangle 用于控制布局填充
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"

            Flickable { // ✅ 使用 Flickable 实现滚动
                id: editFlickable
                anchors.fill: parent
                clip: true

                // ContentWidth/Height 必须基于内部 ColumnLayout 的 ID
                contentWidth: contentLayout.width
                contentHeight: contentLayout.height

                ColumnLayout {
                    id: contentLayout // 内部布局的 ID，用于 Flickable 引用
                    width: editFlickable.width // 宽度填充 Flickable
                    spacing: 15

                    // 1. Prompt 文本框 (核心编辑区)
                    Label { text: "Prompt 文本 (图像生成描述):" }
                    // 使用 Rectangle 包装 TextArea 来模拟 Controls 样式
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 100
                        border.color: "#AAAAAA"
                        border.width: 1
                        radius: 4
                        color: "white"
                        TextArea {
                            anchors.fill: parent
                            text: currentPrompt
                            placeholderText: "输入或修改用于生成图像的详细描述词..."
                            onTextChanged: currentPrompt = text
                            color: "black"
                        }
                    }

                    // 2. Narration (配音文本)
                    Label { text: "Narration 文本 (配音旁白/对话):" }
                    TextField {
                        Layout.fillWidth: true
                        placeholderText: "请输入此镜头所需的旁白或对话文本"
                        onTextChanged: narrationText = text
                    }

                    // 3. 视频过渡效果选择
                    Label { text: "视频过渡效果 (与下一镜头):" }
                    ComboBox {
                        Layout.fillWidth: true
                        model: ["Crossfade", "Ken Burns (平移缩放)", "Cut (硬切)", "Volume Mix"]
                        currentIndex: model.indexOf(transitionEffect)
                        onCurrentIndexChanged: transitionEffect = model[currentIndex]
                    }

                    // 4. 保存更改并生成图像按钮
                    Button {
                        text: generationStatus === "生成中..." ? "生成中..." : "保存更改并生成图像"
                        Layout.alignment: Qt.AlignRight
                        enabled: generationStatus !== "生成中..." && currentPrompt.trim().length > 0

                        onClicked: {
                            generationStatus = "生成中...";

                            // 核心调用：使用 C++ ViewModel 的函数
                            viewModel.generateShotImage(
                                shotData.shotId,
                                currentPrompt,
                                transitionEffect
                            );

                            console.log("分镜图像生成请求已发送，Shot ID:", shotData.shotId);

                            // 实际的 generationStatus 更新应来自 C++ 的 imageGenerationFinished 信号
                        }
                    }
                } // End ColumnLayout (contentLayout)
            } // End Flickable
        } // End Rectangle
    } // End main ColumnLayout
}
