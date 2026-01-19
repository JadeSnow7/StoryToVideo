// ShotDetailPage.qml

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Page {
    id: shotDetailPage

    // macOS 风格配色 & 字体
    readonly property color macBackground: "#F5F5F7"
    readonly property color macCard: "#FFFFFF"
    readonly property color macBorder: "#D1D5DB"
    readonly property color macTextPrimary: "#0B0B0F"
    readonly property color macTextSecondary: "#6B7280"
    readonly property string macTitleFont: "-apple-system"
    readonly property string macBodyFont: "-apple-system"

    // 接收从 StoryboardPage 传递过来的单个分镜数据
    property var shotData: ({})

    // --- 可编辑状态属性 (在 onShotDataChanged 中赋值) ---
    // 添加默认值以防万一
    property string editablePrompt: ""
    property string editableNarration: ""
    property string selectedTransition: "cut"
    property bool isGenerating: false
    property int imageRetryCount: 0

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

    Connections {
        target: viewModel

        function onImageGenerationFinished(shotId, imageUrl) {
            if (shotData && shotData.shotId === shotId) {
                isGenerating = false;
                imageRetryCount = 0;
                shotData = Object.assign({}, shotData, {
                    imageUrl: imageUrl,
                    status: "generated"
                });
                shotImage.source = imageUrl;
            }
        }

        function onGenerationFailed(errorMsg) {
            if (isGenerating) {
                isGenerating = false;
                console.error("生成失败:", errorMsg);
            }
        }
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

            // 顶部返回按钮 (使用 Rectangle + MouseArea)
            Rectangle {
                id: topBackButton
                width: 80
                height: 32
                radius: 10
                color: "transparent"
                border.color: macBorder

                Text {
                    anchors.centerIn: parent
                    text: "← 返回"
                    color: macTextPrimary
                    font.pixelSize: 14
                    font.family: macBodyFont
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        console.log("=== 顶部返回按钮点击 ===");
                        var stackView = resolveStackView();
                        if (stackView) {
                            stackView.pop();
                        }
                    }
                }
            }

            Text {
                text: qsTr("分镜 %1: %2").arg(shotData.shotOrder || "?").arg(shotData.shotTitle || "详情")
                font.pixelSize: 20
                font.bold: true
                font.family: macTitleFont
                color: macTextPrimary
                Layout.fillWidth: true
            }

            // 状态标签
            Rectangle {
                Layout.preferredWidth: statusLabel.implicitWidth + 16
                Layout.preferredHeight: 28
                radius: 14
                color: getStatusColor(shotData.status || "pending")

                Text {
                    id: statusLabel
                    anchors.centerIn: parent
                    text: getStatusText(shotData.status || "pending")
                    font.pixelSize: 12
                    font.bold: true
                    color: "white"
                }
            }
        }

        // --- 1. 图像预览区 ---
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 300
            color: macCard
            radius: 16
            border.color: macBorder

            Image {
                id: shotImage
                anchors.fill: parent
                // 注意：这里使用 shotData.imageUrl，确保数据属性名一致
                source: (shotData && shotData.imageUrl) ? shotData.imageUrl : ""
                fillMode: Image.PreserveAspectFit
                cache: false
                onSourceChanged: imageRetryCount = 0
                onStatusChanged: {
                    if (status === Image.Error && shotData && shotData.imageUrl && imageRetryCount < 3) {
                        imageRetryCount += 1;
                        retryTimer.restart();
                    }
                }

                Text {
                    visible: shotImage.status !== Image.Ready && !isGenerating
                    text: qsTr("图像加载中...")
                    anchors.centerIn: parent
                    color: macTextSecondary
                    font.family: macBodyFont
                }

                BusyIndicator {
                    anchors.centerIn: parent
                    running: isGenerating
                    visible: isGenerating
                }
            }
        }

        // --- 2. 详情编辑区 (Flickable) ---
        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentHeight: contentLayout.implicitHeight
            contentWidth: width
            clip: true  // 防止内容溢出覆盖按钮

            ColumnLayout {
                id: contentLayout
                width: parent.width
                spacing: 10

                // --- 2.1 Prompt 编辑 (文生图提示词) ---
                Text { text: qsTr("绘画提示词 (Prompt)"); font.bold: true; font.family: macTitleFont; color: "#2563EB" }
                TextArea {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 80
                    text: editablePrompt
                    onTextChanged: editablePrompt = text
                    wrapMode: Text.WordWrap
                    color: macTextPrimary
                    font.family: macBodyFont
                    background: Rectangle {
                        radius: 12
                        color: macCard
                        border.color: macBorder
                    }
                }

                // --- 2.2 配音文案/旁白编辑 (Narration) ---
                Text { text: qsTr("旁白/文案 (Narration Text)"); font.bold: true; font.family: macTitleFont; color: macTextPrimary }
                TextArea {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 80
                    text: editableNarration
                    onTextChanged: editableNarration = text
                    wrapMode: Text.WordWrap
                    color: macTextPrimary
                    font.family: macBodyFont
                    background: Rectangle {
                        radius: 12
                        color: macCard
                        border.color: macBorder
                    }
                }

                // --- 2.3 视频转场选择 (Transition) ---
                Text { text: qsTr("视频转场效果"); font.bold: true; font.family: macTitleFont; color: macTextPrimary }
                ComboBox {
                    Layout.fillWidth: true
                    model: transitionModels
                    currentIndex: model.indexOf(selectedTransition)
                    onCurrentIndexChanged: { selectedTransition = model[currentIndex]; }
                }
            }
        }

        // --- 3. 操作按钮 (使用 Rectangle + MouseArea 确保点击事件) ---
        Rectangle {
            id: generateButton
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            radius: 14
            opacity: isGenerating ? 0.7 : 1.0
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#4A8BFF" }
                GradientStop { position: 1.0; color: "#2D6BFF" }
            }

            Text {
                anchors.centerIn: parent
                text: isGenerating ? qsTr("生成中...") : qsTr("触发文生图任务 (生成图像)")
                color: "white"
                font.pixelSize: 15
                font.bold: true
                font.family: macBodyFont
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                enabled: !isGenerating
                onClicked: {
                    console.log("=== 生成按钮点击事件触发 ===");
                    console.log("shotData.shotId:", shotData.shotId);
                    console.log("editablePrompt:", editablePrompt);
                    
                    if (shotData.shotId) {
                        isGenerating = true;
                        imageRetryCount = 0;
                        shotData = Object.assign({}, shotData, {
                            status: "processing"
                        });
                        // [修改] 不清空 source，保持旧图显示直到新图加载
                        // shotImage.source = ""; 
                        viewModel.generateShotImage(
                            shotData.shotId,
                            editablePrompt,
                            selectedTransition
                        );
                        console.log("请求重新生成分镜:", shotData.shotId);
                    } else {
                        console.error("shotData.shotId 为空，无法生成");
                    }
                }
            }
        }

        // 返回按钮 (使用 Rectangle + MouseArea)
        Rectangle {
            id: backButton
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            radius: 14
            color: "transparent"
            border.color: macBorder
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: qsTr("返回故事板")
                color: macTextPrimary
                font.pixelSize: 15
                font.family: macBodyFont
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    console.log("=== 返回按钮点击 ===");
                    var stackView = resolveStackView();
                    if (stackView) {
                        stackView.pop();
                    }
                }
            }
        }
    }
    }

    Timer {
        id: retryTimer
        interval: 800
        repeat: false
        onTriggered: {
            if (shotData && shotData.imageUrl) {
                var sep = shotData.imageUrl.indexOf("?") >= 0 ? "&" : "?";
                shotImage.source = shotData.imageUrl + sep + "retry=" + Date.now();
            }
        }
    }

    // ========== 状态映射辅助函数 ==========
    function getStatusColor(status) {
        switch (status) {
            case "finished":
            case "generated":
            case "completed": // [新增]
                return "#4CAF50";  // 绿色
            case "pending":
            case "running":
            case "processing":
                return "#FFC107";  // 黄色
            case "error":
            case "failed":
                return "#F44336";  // 红色
            default:
                return "#9E9E9E";  // 灰色
        }
    }

    function getStatusText(status) {
        switch (status) {
            case "finished":
            case "generated":
            case "completed": // [新增]
                return qsTr("已完成");
            case "pending":
                return qsTr("待处理");
            case "running":
            case "processing":
                return qsTr("生成中");
            case "error":
            case "failed":
                return qsTr("失败");
            default:
                return qsTr("未知");
        }
    }

    function resolveStackView() {
        if (typeof pageStack !== "undefined" && pageStack) {
            return pageStack;
        }
        if (StackView.view) {
            return StackView.view;
        }
        return null;
    }
}
