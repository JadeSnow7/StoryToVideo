// AssetsPage.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import Qt.labs.folderlistmodel    // 用于读取本地文件目录

Page {
    id: assetsPage
    title: "资产库"

    // macOS 风格配色 & 字体
    readonly property color macBackground: "#F5F5F7"
    readonly property color macCard: "#FFFFFF"
    readonly property color macBorder: "#D1D5DB"
    readonly property color macTextPrimary: "#0B0B0F"
    readonly property color macTextSecondary: "#6B7280"
    readonly property string macTitleFont: "-apple-system"
    readonly property string macBodyFont: "-apple-system"

    Component.onCompleted: {
        console.log("AssetsPage loaded. assetsRoot =", assetsRoot)
    }

    // ⚠ 请你在这里填写资产文件夹路径，例如：
    // file:///C:/Users/admin/Desktop/Assert/
    // macOS: 改为本机存在的目录，避免无效路径阻断 UI
    property string assetsRoot: "file:///Users/huaodong/Movies/StoryToVideo/"   // 专用项目存储目录
    property bool isLoadingProject: false // 防止与 CreatePage 的信号冲突

    // 读取资产根目录下的所有子文件夹
    FolderListModel {
        id: folderModel
        folder: assetsRoot
        nameFilters: ["Project_*"]  // 只显示 Project_* 文件夹
        showDirs: true
        showFiles: false
        showDotAndDotDot: false  // 排除 . 和 .. 目录
    }

    Connections {
        target: viewModel
        function onStoryboardGenerated(data) {
            if (assetsPage.isLoadingProject) {
                console.log("AssetsPage:Project loaded, navigating to StoryboardPage");
                assetsPage.isLoadingProject = false;
                pageStack.push(Qt.resolvedUrl("StoryboardPage.qml"), {
                    storyId: data.id,
                    storyTitle: data.title || "加载的项目",
                    shotsData: data.shots || [], // [修正] 匹配 StoryboardPage 的 shotsData 属性
                    videoPath: data.videoPath || "",
                    videoLocalPath: data.videoLocalPath || "",
                    stackViewRef: pageStack     // [重要] 传递 stackViewRef 用于后续导航
                });
            }
        }
    }

    Connections {
        target: viewModel
        function onGenerationFailed(msg) {
            if (assetsPage.isLoadingProject) {
                console.log("AssetsPage: Loading failed", msg);
                assetsPage.isLoadingProject = false;
                // 可以显示一个 Toast 或 Dialog，这里简单打印
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: macBackground

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 20

        // ========== 顶部导航栏 ==========
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Text {
                text: qsTr("资产库")
                font.pixelSize: 22
                font.bold: true
                font.family: macTitleFont
                color: macTextPrimary
                Layout.fillWidth: true
            }

            Button {
                text: "刷新"
                font.pixelSize: 14
                font.family: macBodyFont
                background: Rectangle {
                    radius: 18
                    color: "white"
                    border.color: macBorder
                    border.width: 1
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
                    // 重新加载文件夹列表
                    folderModel.folder = "";
                    folderModel.folder = assetsRoot;
                    console.log("资产库已刷新");
                }
            }
        }

        // 搜索 + 新建按钮
        RowLayout {
            Layout.fillWidth: true

            TextField {
                Layout.fillWidth: true
                placeholderText: qsTr("按故事名称或生成时间筛选...")
                leftPadding: 12
                background: Rectangle {
                    radius: 20
                    color: "white"
                    border.color: "#E0E0E0"
                }
            }

            Button {
                text: qsTr("+ 新建故事")
                Layout.preferredWidth: 140
                background: Rectangle {
                    radius: 18
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#6C63FF" }
                        GradientStop { position: 1.0; color: "#5A54E3" }
                    }
                }
                onClicked: {
                    pageStack.push(Qt.resolvedUrl("CreatePage.qml"))
                }
            }
        }

        // 资产统计提示
        Rectangle {
            Layout.fillWidth: true
            height: 70
            radius: 14
            color: macCard
            border.color: macBorder
            RowLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16

                ColumnLayout {
                    Layout.fillWidth: true
                    Text {
                        text: qsTr("可用项目")
                        font.pixelSize: 13
                        font.family: macBodyFont
                        color: macTextSecondary
                    }
                    Text {
                        text: folderModel.count
                        font.pixelSize: 28
                        font.bold: true
                        font.family: macTitleFont
                        color: macTextPrimary
                    }
                }

                ColumnLayout {
                    Text {
                        text: qsTr("资源目录")
                        font.pixelSize: 13
                        font.family: macBodyFont
                        color: macTextSecondary
                    }
                    Text {
                        text: assetsRoot
                        font.pixelSize: 14
                        font.family: macBodyFont
                        color: macTextPrimary
                        elide: Text.ElideRight
                        Layout.preferredWidth: 320
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 18
            color: macCard
            border.color: macBorder
            clip: true

            ScrollView {
                anchors.fill: parent
                contentWidth: parent.width

                Flow {
                    width: parent.width
                    padding: 24
                    spacing: 20

                // ★ 动态读取子文件夹数量
                Repeater {
                    model: folderModel.count

                    // 不展示根目录自身（第 0 项一般是 "."）
                    delegate: Rectangle {
                        id: cardRect
                        width: 240
                        height: 220
                        radius: 16
                        color: macCard
                        border.color: macBorder
                        border.width: 1
                        layer.enabled: true
                        layer.effect: DropShadow {
                            color: "#1F000000"
                            radius: 12
                            samples: 15
                            verticalOffset: 6
                        }

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

                        // ★ MouseArea 放在 Rectangle 级别，覆盖整个卡片
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            hoverEnabled: true
                            onClicked: {
                                // 点击尝试加载项目进入故事板
                                console.log("尝试加载项目:", cardRect.folderPath)
                                assetsPage.isLoadingProject = true
                                viewModel.loadProject(cardRect.folderPath)
                            }
                            onEntered: {
                                cardRect.border.color = "#4D7CFE"
                                cardRect.border.width = 2
                                cardRect.scale = 1.02
                            }
                            onExited: {
                                cardRect.border.color = macBorder
                                cardRect.border.width = 1
                                cardRect.scale = 1.0
                            }
                        }

                        Behavior on scale {
                            NumberAnimation { duration: 120; easing.type: Easing.OutQuad }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 110
                                radius: 12
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: "#D9D9F3" }
                                    GradientStop { position: 1.0; color: "#C3C8FF" }
                                }

                                Image {
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    fillMode: Image.PreserveAspectCrop
                                    visible: cardRect.thumbToShow !== ""
                                    source: cardRect.thumbToShow
                                }

                                // fallback 文本
                                Text {
                                    anchors.centerIn: parent
                                    visible: cardRect.thumbToShow === ""
                                    text: "缩略图\n未找到"
                                    color: "gray"
                                }
                            }

                            Text {
                                text: dataManager.getProjectTitle(cardRect.folderPath)
                                font.bold: true
                                font.pixelSize: 16
                                font.family: macTitleFont
                                color: macTextPrimary
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            Rectangle {
                                width: 96
                                height: 26
                                radius: 13
                                color: "#F0F1FF"
                                Text {
                                    anchors.centerIn: parent
                                    text: qsTr("本地资产")
                                    font.pixelSize: 12
                                    color: "#5A54E3"
                                }
                            }
                    }
                }
                } // 结束 Flow

                // 空态提示 - 完全独立于 Flow
                Text {
                    visible: folderModel.count === 0
                    text: qsTr("未检测到资产，请先在右上角创建故事或配置 assetsRoot")
                    font.family: macBodyFont
                    font.pixelSize: 14
                    color: macTextSecondary
                    x: 40
                    y: 40
                }
            } // 结束 ScrollView
        } // 结束 Rectangle
        }
        }
    }
}
