// CreatePage.qml

import QtQuick 2.6
import QtQuick.Controls 2.1
import QtQuick.Layouts 1.2
import QtQuick.Window 2.2

Page {
    id: createPage
    title: qsTr("新建故事")

    // 状态属性
    property string storyText: ""
    property string selectedStyle: "电影"
    property bool isGenerating: false

    // 默认样式列表
    readonly property var styleModel: ["电影", "动画", "写实", "水墨风"]

    // --- 接收 C++ ViewModel 发出的信号 ---
    Connections {
        target: viewModel

        onStoryboardGenerated: {
            isGenerating = false;
            var storyId = storyData.id;
            var storyTitle = storyData.title;
            var shotsList = storyData.shots // 分镜列表数据


            // --- [新增调试代码] 打印分镜的详细内容 ---
            console.log("--- DEBUG: 接收到的所有分镜详情 ---");
            if (shotsList && shotsList.length > 0) {
                for (var i = 0; i < shotsList.length; i++) {
                    var shot = shotsList[i];
                    // 打印关键字段，验证数据有效性
                    console.log("Shot " + (i + 1) + " - Title:", shot.title,
                                "Prompt:", shot.prompt,
                                "Image Path:", shot.imagePath);
                }
            } else {
                console.warn("Shots 列表为空或未定义，无法打印详情。");
            }
            console.log("-------------------------------");
            // --- [调试代码结束] ---


            // 成功后导航至 StoryboardPage，并将数据传递过去
            try {
                // 使用 pageStack ID 进行导航
                pageStack.replace(Qt.resolvedUrl("StoryboardPage.qml"), {
                    storyId: storyId,
                    storyTitle: storyTitle,
                    shotsData: shotsList, // 传递分镜列表数据
                    stackViewRef: pageStack
                });
                console.log("导航成功，已跳转到 StoryboardPage。");
            } catch (e) {
                console.error("导航失败，请检查 main.qml 中 StackView 的 ID 是否为 pageStack。", e);
            }
        }

        onGenerationFailed: {
            isGenerating = false;
            console.error("故事生成失败:", errorMsg);
        }

//        onNetworkError: {
//            isGenerating = false;
//            console.error("网络错误:", errorMsg);
//        }
        onCompilationProgress: function(sId, pct) {
                // 如果 C++ 信号能被 QML 接收，这条日志一定会出现！
                console.log("!!! TEMP TEST SUCCESS: Signal Received in CreatePage. Progress:", pct, "ID:", sId);
            }
    }


    // --- 页面布局 (省略，与之前保持一致) ---
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        // 故事文本输入框
        Label { text: qsTr("输入故事文本：") }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 180
            border.color: "#AAAAAA"
            border.width: 1
            radius: 4
            color: "white"

            TextArea {
                anchors.fill: parent
                leftPadding: 8; rightPadding: 8; topPadding: 8; bottomPadding: 8
                placeholderText: qsTr("请输入您的故事，系统将自动生成分镜...")
                text: storyText
                onTextChanged: storyText = text
                color: "black"
//                ScrollBar.vertical: ScrollBar {}
            }
        }

        // 风格选择
        Label { text: qsTr("选择风格：") }
        ComboBox {
            Layout.fillWidth: true
            model: styleModel
            onCurrentIndexChanged: selectedStyle = model[currentIndex]
            currentIndex: styleModel.indexOf(selectedStyle)
        }

        // 进度指示器
        BusyIndicator {
            visible: isGenerating
            running: isGenerating
            Layout.alignment: Qt.AlignHCenter
        }

        // 生成故事按钮
        Button {
            text: isGenerating ? qsTr("生成中...") : qsTr("生成故事")
            Layout.alignment: Qt.AlignRight
            Layout.preferredWidth: 150
            Layout.preferredHeight: 40

            enabled: !isGenerating && storyText.trim().length > 0

            onClicked: {
                isGenerating = true;
                console.log("调用 C++ generateStoryboard，风格:", selectedStyle);
                viewModel.generateStoryboard(storyText.trim(), selectedStyle);
            }
        }
    }
}
