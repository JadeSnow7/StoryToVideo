// CreatePage.qml
import QtQuick 2.6            // 兼容 Qt 5.8.0
import QtQuick.Controls 2.1   // 兼容 Qt 5.8.0
import QtQuick.Layouts 1.2    // 兼容 Qt 5.8.0

Page {
    id: createPage
    title: "新建故事"

    // 状态属性
    property string storyText: ""
    property string selectedStyle: "电影"
    property bool isGenerating: false // 加载状态

    // --- 接收 C++ ViewModel 发出的信号 ---
    Connections {
        target: viewModel

        onStoryboardGenerated: {
            isGenerating = false;

            // storyData 是 C++ 传递的 QVariantMap，包含 id 和 title
            var storyId = storyData.id;
            var storyTitle = storyData.title;
            var shotsList = storyData.shots;

            console.log("QML 收到 C++ 成功通知，ID:", storyId, "标题:", storyTitle);

            // 成功后导航至 StoryboardPage，并将数据传递过去
            pageStack.replace(Qt.resolvedUrl("StoryboardPage.qml"), {
                storyId: storyId,
                storyTitle: storyTitle,
                actualShotsModel: shotsList
            });
        }

        onGenerationFailed: {
            isGenerating = false;
            // TODO: 这里应添加一个弹窗来显示错误信息 errorMsg
            console.log("QML 收到 C++ 失败通知:", errorMsg);
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20 // 使用 anchors.margins 代替 padding
        spacing: 20

        // 故事文本输入框
        Label { text: "输入故事文本：" }

        // --- TextArea 组件 ---
        // 注意：TextArea 没有 background 属性，我们使用外部 Rectangle 模拟边框
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 150
            border.color: "#AAAAAA"
            border.width: 1
            radius: 4
            color: "white" // 文本框背景色

            TextArea {
                // 确保 TextArea 填充 Rectangle 的内容区域
                anchors.fill: parent
                // 移除 padding 属性
                placeholderText: "请输入您的故事，系统将自动生成分镜..."
                text: storyText
                onTextChanged: storyText = text

                // 确保文本颜色在白色背景上可见
                color: "black"
            }
        }
        // --- TextArea 组件结束 ---

        // 风格选择
        Label { text: "选择风格：" }
        ComboBox {
            Layout.fillWidth: true
            model: ["电影", "动画", "写实"]
            // 确保 ComboBox 能够反映选中状态
            onCurrentIndexChanged: selectedStyle = model[currentIndex]
        }

        // 生成故事按钮
        Button {
            text: isGenerating ? "生成中..." : "生成故事"
            Layout.alignment: Qt.AlignRight
            // 确保 enabled 属性是一个布尔表达式
            enabled: !isGenerating && storyText.trim().length > 0

            onClicked: {
                isGenerating = true;

                // 核心调用：调用 C++ 函数
                viewModel.generateStoryboard(storyText, selectedStyle);
            }
        }
    }
}
