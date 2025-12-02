// ShotDetailPage.qml

import QtQuick 2.6
import QtQuick.Controls 2.1
import QtQuick.Layouts 1.2
import QtQuick.Window 2.2

Page {
    id: shotDetailPage

    // 接收从 StoryboardPage 传递过来的单个分镜数据
    property var shotData: ({})

    // --- 可编辑状态属性 (在 onShotDataChanged 中赋值) ---
    // 添加默认值以防万一
    property string editablePrompt: ""
    property string editableNarration: ""
    property string selectedTransition: "cut"

    // 使用属性值作为页面标题
    title: qsTr("分镜详情")

    // 假设可用的转场效果列表
    readonly property var transitionModels: ["cut", "fade", "wipe", "zoom", "dissolve", "crossfade"]


    // --- 核心修复：监听 shotData 变化，执行初始化 ---
    onShotDataChanged: {
        // 确保 shotData 是一个对象且包含 shotId
        if (shotData && shotData.shotId) {
            console.log("✅ ShotDetail: 数据有效性检查通过。ID:", shotData.shotId);

            // 1. 初始化可编辑属性
            // 使用 || "" 确保属性不会是 null 或 undefined
            editablePrompt = shotData.shotPrompt || "";
            editableNarration = shotData.shotDescription || "";
            selectedTransition = shotData.transition || "cut";

            // 2. 更新页面标题
            shotDetailPage.title = qsTr("分镜 %1: %2").arg(shotData.shotOrder || "?").arg(shotData.shotTitle || "详情");

        } else {
            console.error("❌ 数据初始化失败：shotData 为空或未包含 shotId。");
        }
    }


    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        // --- 临时诊断标签 (检查数据是否到达 UI) ---
        Text {
            // 如果成功，这里会显示 Prompt 的前60个字符
            text: qsTr("DEBUG CHECK (Prompt): %1").arg(editablePrompt.substring(0, 60) + (editablePrompt.length > 60 ? "..." : ""))
            color: "red"
            font.bold: true
            Layout.fillWidth: true
            Layout.preferredHeight: 20
        }
        // ----------------------------------------

        // --- 1. 图像预览区 ---
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 300
            color: "#ECEFF1"

            Image {
                id: shotImage
                anchors.fill: parent
                // 注意：这里使用 shotData.imageUrl，确保数据属性名一致
                source: (shotData && shotData.imageUrl) ? shotData.imageUrl : ""
                fillMode: Image.PreserveAspectFit

                Text {
                    visible: shotImage.status !== Image.Ready
                    text: qsTr("图像加载中...")
                    anchors.centerIn: parent
                    color: "gray"
                }
            }
        }

        // --- 2. 详情编辑区 (Flickable) ---
        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentHeight: contentLayout.implicitHeight

            ColumnLayout {
                id: contentLayout
                Layout.fillWidth: true
                spacing: 10

                // --- 2.1 Prompt 编辑 (文生图提示词) ---
                Text { text: qsTr("绘画提示词 (Prompt)"); font.bold: true; color: "teal" }
                TextArea {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 80
                    text: editablePrompt
                    onTextChanged: editablePrompt = text
                    wrapMode: Text.WordWrap
                    color: "black"
                }

                // --- 2.2 配音文案/旁白编辑 (Narration) ---
                Text { text: qsTr("旁白/文案 (Narration Text)"); font.bold: true }
                TextArea {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 80
                    text: editableNarration
                    onTextChanged: editableNarration = text
                    wrapMode: Text.WordWrap
                    color: "black"
                }

                // --- 2.3 视频转场选择 (Transition) ---
                Text { text: qsTr("视频转场效果"); font.bold: true }
                ComboBox {
                    Layout.fillWidth: true
                    model: transitionModels
                    currentIndex: model.indexOf(selectedTransition)
                    onCurrentIndexChanged: { selectedTransition = model[currentIndex]; }
                }
            }
        }

        // --- 3. 操作按钮 ---
        Button {
            text: qsTr("触发文生图任务 (生成图像)")
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            enabled: editablePrompt.trim().length > 0 && shotData.shotId
            onClicked: {
                // 确保 shotData.shotId 存在
                if (shotData.shotId) {
                    viewModel.generateShotImage(
                        shotData.shotId,
                        editablePrompt,
                        selectedTransition
                    );
                    console.log("请求重新生成分镜:", shotData.shotId);
                }
            }
        }

        // 返回按钮
        Button {
            text: qsTr("返回故事板")
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            onClicked: {
                StackView.view.pop();
            }
        }
    }
}
