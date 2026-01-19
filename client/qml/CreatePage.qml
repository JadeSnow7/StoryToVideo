// CreatePage.qml

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import Qt5Compat.GraphicalEffects

Page {
    id: createPage
    title: qsTr("新建故事")

    // 状态属性
    property string storyText: ""
    property string projectName: ""  // [新增] 项目名称
    property string selectedStyle: "电影"
    property bool isGenerating: false
    property int generationProgress: 0
    property string statusMessage: ""

    // 默认样式列表 - 扩展风格选项
    readonly property var styleModel: [
        { name: "电影", icon: "🎬", desc: "好莱坞大片质感" },
        { name: "动画", icon: "🎨", desc: "皮克斯/吉卜力风格" },
        { name: "写实", icon: "📷", desc: "摄影级真实画面" },
        { name: "水墨风", icon: "🖌️", desc: "中国传统水墨意境" },
        { name: "赛博朋克", icon: "🌃", desc: "霓虹科幻未来城市" },
        { name: "油画", icon: "🎭", desc: "印象派艺术质感" },
        { name: "漫画", icon: "💥", desc: "日漫/美漫风格" },
        { name: "像素", icon: "👾", desc: "复古8-bit游戏风" },
        { name: "3D渲染", icon: "🧊", desc: "Blender质感建模" },
        { name: "梦幻", icon: "✨", desc: "童话般柔和光影" },
        { name: "黑白", icon: "🎞️", desc: "经典黑白电影" },
        { name: "浮世绘", icon: "🗾", desc: "日本传统木版画" }
    ]

    // macOS 风格配色 & 字体
    readonly property color macBackground: "#F5F5F7"
    readonly property color macCard: "#FFFFFF"
    readonly property color macSecondary: "#F8F9FB"
    readonly property color macBorder: "#D1D5DB"
    readonly property color macTextPrimary: "#0B0B0F"
    readonly property color macTextSecondary: "#6B7280"
    readonly property string macTitleFont: "-apple-system"
    readonly property string macBodyFont: "-apple-system"

    // --- 接收 C++ ViewModel 发出的信号 ---
    Connections {
        target: viewModel

        function onStoryboardGenerated(storyData) {
            if (!isGenerating) {
                return;
            }
            if (StackView.view && StackView.view.currentItem !== createPage) {
                return;
            }
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
                    videoPath: storyData.videoPath || "",
                    videoLocalPath: storyData.videoLocalPath || "",
                    stackViewRef: pageStack
                });
                console.log("导航成功，已跳转到 StoryboardPage。");
            } catch (e) {
                console.error("导航失败，请检查 main.qml 中 StackView 的 ID 是否为 pageStack。", e);
            }
        }

        function onGenerationFailed(errorMsg) {
            isGenerating = false;
            generationProgress = 0;
            statusMessage = "";
            console.error("故事生成失败:", errorMsg);
            
            // 显示错误对话框
            errorDialog.errorMessage = errorMsg;
            errorDialog.open();
        }

//        onNetworkError: {
//            isGenerating = false;
//            console.error("网络错误:", errorMsg);
//        }
        onCompilationProgress: function(sId, pct) {
            // 更新进度显示
            generationProgress = pct;
            console.log("生成进度更新:", pct + "%", "Story ID:", sId);
        }
    }

    // --- 错误对话框 (macOS 风格) ---
    Dialog {
        id: errorDialog
        title: ""
        modal: true
        anchors.centerIn: parent
        width: 360
        padding: 0

        property string errorMessage: ""

        background: Rectangle {
            radius: 16
            color: macCard
            border.color: macBorder
            layer.enabled: true
            layer.effect: DropShadow {
                radius: 20
                samples: 25
                color: "#30000000"
                verticalOffset: 8
            }
        }

        contentItem: ColumnLayout {
            spacing: 16
            
            // 标题栏
            Rectangle {
                Layout.fillWidth: true
                height: 50
                radius: 16
                color: "#FF6B6B"
                
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: parent.height / 2
                    color: parent.color
                }
                
                Text {
                    anchors.centerIn: parent
                    text: qsTr("生成失败")
                    font.bold: true
                    font.pixelSize: 18
                    font.family: macTitleFont
                    color: "white"
                }
            }
            
            // 错误信息
            Text {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                text: errorDialog.errorMessage
                wrapMode: Text.WordWrap
                font.pixelSize: 14
                font.family: macBodyFont
                color: macTextPrimary
            }
            
            // 按钮区
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                Layout.bottomMargin: 20
                spacing: 12
                
                Button {
                    Layout.fillWidth: true
                    text: qsTr("取消")
                    background: Rectangle {
                        radius: 10
                        color: macSecondary
                        border.color: macBorder
                    }
                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 14
                        font.family: macBodyFont
                        color: macTextPrimary
                        horizontalAlignment: Text.AlignHCenter
                    }
                    onClicked: errorDialog.close()
                }
                
                Button {
                    Layout.fillWidth: true
                    text: qsTr("重试")
                    background: Rectangle {
                        radius: 10
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#4A8BFF" }
                            GradientStop { position: 1.0; color: "#2D6BFF" }
                        }
                    }
                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 14
                        font.bold: true
                        font.family: macBodyFont
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                    }
                    onClicked: {
                        errorDialog.close()
                        if (storyText.trim().length > 0) {
                            isGenerating = true;
                            generationProgress = 0;
                            statusMessage = "";
                            viewModel.generateStoryboard(storyText.trim(), selectedStyle, projectName);
                        }
                    }
                }
            }
        }
    }


    // --- 页面布局 ---
    Rectangle {
        anchors.fill: parent
        color: macBackground

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 18

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Button {
                    text: "← " + qsTr("返回")
                    Layout.preferredWidth: 98
                    // 生成期间也可以点击返回
                    enabled: true
                    font.family: macBodyFont
                    background: Rectangle {
                        radius: 10
                        color: "transparent"
                        border.color: "#BFC4D2"
                        border.width: 1
                    }
                    contentItem: Text {
                        text: parent.text
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: macTextPrimary
                        font.pixelSize: 14
                        font.family: macBodyFont
                    }
                    onClicked: {
                        pageStack.pop()
                    }
                }

                Item { Layout.fillWidth: true }

                Button {
                    text: qsTr("查看所有故事")
                    Layout.preferredWidth: 150
                    // 生成期间也可以查看故事列表
                    enabled: true
                    font.family: macBodyFont
                    background: Rectangle {
                        radius: 14
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#4F91FF" }
                            GradientStop { position: 1.0; color: "#2D6BFF" }
                        }
                        border.color: "transparent"
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "white"
                        font.pixelSize: 14
                        font.bold: true
                        font.family: macBodyFont
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: {
                        // 使用 push 而不是 pop，这样 CreatePage 保留在栈中
                        // 用户可以从 AssetsPage 返回继续查看生成进度
                        pageStack.push(Qt.resolvedUrl("AssetsPage.qml"))
                    }
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 140

                Rectangle {
                    id: heroCard
                    anchors.fill: parent
                    radius: 18
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#8FB8FF" }
                        GradientStop { position: 1.0; color: "#6FA0FF" }
                    }

                    Column {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 6

                        Text {
                            text: qsTr("新建故事脚本")
                            font.pixelSize: 26
                            font.bold: true
                            font.family: macTitleFont
                            color: "white"
                        }

                        Text {
                            text: qsTr("粘贴剧情梗概或文字提示，我们会为你生成镜头级分镜。")
                            font.pixelSize: 16
                            font.family: macBodyFont
                            color: "#EFF4FF"
                        }

                        Text {
                            text: qsTr("提示：越清晰的指令越容易获得满意的镜头。")
                            font.pixelSize: 13
                            font.family: macBodyFont
                            color: "#E0E8FF"
                        }
                    }
                }

                DropShadow {
                    anchors.fill: heroCard
                    source: heroCard
                    radius: 18
                    samples: 25
                    color: "#0000001A"
                    horizontalOffset: 0
                    verticalOffset: 10
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 18

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 18
                    color: macCard
                    border.color: macBorder
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 14

                        // [新增] 项目名称输入
                        Text {
                            text: qsTr("项目名称")
                            font.pixelSize: 20
                            font.family: macTitleFont
                            color: macTextPrimary
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 44
                            radius: 10
                            color: macSecondary
                            border.color: macBorder

                            TextField {
                                id: projectNameField
                                anchors.fill: parent
                                anchors.margins: 8
                                placeholderText: qsTr("输入项目名称（可选）")
                                text: projectName
                                onTextChanged: projectName = text
                                font.pixelSize: 14
                                font.family: macBodyFont
                                color: macTextPrimary
                                background: null
                            }
                        }

                        Item { height: 8 }  // 间距

                        Text {
                            text: qsTr("故事文本")
                            font.pixelSize: 20
                            font.family: macTitleFont
                            color: macTextPrimary
                        }

                        Text {
                            text: qsTr("描述场景、角色和节奏，或直接粘贴剧本。")
                            color: macTextSecondary
                            font.pixelSize: 14
                            font.family: macBodyFont
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 120
                            radius: 14
                            color: macSecondary
                            border.color: macBorder

                            ScrollView {
                                anchors.fill: parent
                                anchors.margins: 4
                                clip: true

                                TextArea {
                                    id: storyTextArea
                                    anchors.margins: 14
                                    placeholderText: qsTr("请输入您的故事，系统将自动生成分镜...")
                                    color: macTextPrimary
                                    wrapMode: TextEdit.Wrap
                                    text: storyText
                                    onTextChanged: storyText = text
                                    font.pixelSize: 14
                                    font.family: macBodyFont
                                    background: null
                                    cursorVisible: true
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Text {
                                text: qsTr("选择风格")
                                font.pixelSize: 17
                                font.family: macTitleFont
                                color: macTextPrimary
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 4
                                columnSpacing: 10
                                rowSpacing: 10

                                Repeater {
                                    model: styleModel

                                    Rectangle {
                                        property bool active: modelData.name === selectedStyle
                                        radius: 14
                                        color: active ? "#E6EEFF" : "#FFFFFF"
                                        border.color: active ? "#4D7CFE" : macBorder
                                        border.width: active ? 2 : 1
                                        implicitHeight: 70
                                        implicitWidth: 110
                                        Layout.fillWidth: true
                                        layer.enabled: true
                                        layer.effect: DropShadow {
                                            radius: active ? 16 : 8
                                            samples: 20
                                            color: active ? "#4D7CFE30" : "#00000010"
                                            horizontalOffset: 0
                                            verticalOffset: active ? 6 : 3
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            hoverEnabled: true
                                            onClicked: selectedStyle = modelData.name
                                            onEntered: parent.scale = 1.03
                                            onExited: parent.scale = 1.0
                                        }

                                        Behavior on scale {
                                            NumberAnimation { duration: 120; easing.type: Easing.OutQuad }
                                        }

                                        Column {
                                            anchors.centerIn: parent
                                            spacing: 4

                                            Text {
                                                anchors.horizontalCenter: parent.horizontalCenter
                                                text: modelData.icon
                                                font.pixelSize: 22
                                            }

                                            Text {
                                                anchors.horizontalCenter: parent.horizontalCenter
                                                text: modelData.name
                                                color: active ? "#1B2A4B" : macTextPrimary
                                                font.pixelSize: 13
                                                font.bold: active
                                                font.family: macBodyFont
                                            }
                                        }

                                        // 选中指示器
                                        Rectangle {
                                            visible: active
                                            anchors.top: parent.top
                                            anchors.right: parent.right
                                            anchors.margins: 6
                                            width: 18
                                            height: 18
                                            radius: 9
                                            color: "#4D7CFE"

                                            Text {
                                                anchors.centerIn: parent
                                                text: "✓"
                                                color: "white"
                                                font.pixelSize: 11
                                                font.bold: true
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Button {
                            text: isGenerating ? qsTr("生成中…") : qsTr("生成故事")
                            Layout.alignment: Qt.AlignRight
                            Layout.preferredWidth: 190
                            Layout.preferredHeight: 46
                            enabled: !isGenerating && storyText.trim().length > 0
                            font.pixelSize: 16
                            font.bold: true
                            font.family: macBodyFont
                            background: Rectangle {
                                radius: 18
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: "#4A8BFF" }
                                    GradientStop { position: 1.0; color: "#2D6BFF" }
                                }
                                border.color: "#1E4ED8"
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
                                isGenerating = true;
                                console.log("调用 C++ generateStoryboard，风格:", selectedStyle);
                                viewModel.generateStoryboard(storyText.trim(), selectedStyle, projectName);
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 320
                    Layout.fillHeight: true
                    radius: 18
                    color: "#FFFFFFCC"
                    border.color: "#E2E5EC"
                    border.width: 1
                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 30
                        samples: 32
                        color: "#00000014"
                        horizontalOffset: 0
                        verticalOffset: 12
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 16

                        Text {
                            text: qsTr("生成进度")
                            font.pixelSize: 18
                            font.family: macTitleFont
                            color: macTextPrimary
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            radius: 16
                            color: macCard
                            border.color: macBorder
                            height: 120

                            Column {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 10

                                Row {
                                    width: parent.width
                                    spacing: 10

                                    BusyIndicator {
                                        running: isGenerating
                                        visible: isGenerating
                                        width: 26
                                        height: 26
                                    }

                                    Text {
                                        text: isGenerating ? (statusMessage.length > 0 ? statusMessage : qsTr("正在生成中...")) : qsTr("准备就绪")
                                        color: macTextSecondary
                                        font.pixelSize: 14
                                        font.family: macBodyFont
                                    }
                                }

                                Text {
                                    text: generationProgress + "%"
                                    font.pixelSize: 28
                                    font.bold: true
                                    font.family: macTitleFont
                                    color: "#2563EB"
                                }

                                ProgressBar {
                                    id: progressCardBar
                                    from: 0
                                    to: 100
                                    value: generationProgress
                                    Layout.fillWidth: true
                                    implicitHeight: 10
                                    background: Rectangle {
                                        color: "#E5E7EB"
                                        radius: 6
                                    }
                                    contentItem: Rectangle {
                                        width: progressCardBar.visualPosition * parent.width
                                        height: parent.height
                                        radius: 6
                                        color: "#34C759"
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            radius: 16
                            color: "#FFFFFF"
                            border.color: macBorder
                            Layout.fillHeight: true

                            Column {
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 12

                                Text {
                                    text: qsTr("写作提示")
                                    font.pixelSize: 17
                                    font.family: macTitleFont
                                    color: macTextPrimary
                                }

                                Repeater {
                                    model: [
                                        qsTr("说明故事背景、角色关系、冲突"),
                                        qsTr("强调镜头语言：远景、跟拍、加速等"),
                                        qsTr("指明期望氛围：温暖、悬疑、科幻")
                                    ]

                                    Row {
                                        width: parent.width
                                        spacing: 8

                                        Rectangle {
                                            width: 6
                                            height: 6
                                            radius: 3
                                            color: "#2563EB"
                                            anchors.verticalCenter: tipText.verticalCenter
                                        }

                                        Text {
                                            id: tipText
                                            text: modelData
                                            color: macTextSecondary
                                            font.pixelSize: 14
                                            font.family: macBodyFont
                                            wrapMode: Text.WordWrap
                                            width: parent.width - 30
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
