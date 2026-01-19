// StoryboardPage.qml

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Page {
    id: storyboardPage
    title: qsTr("故事板预览")

    // macOS 风格配色 & 字体
    readonly property color macBackground: "#F5F5F7"
    readonly property color macCard: "#FFFFFF"
    readonly property color macBorder: "#D1D5DB"
    readonly property color macTextPrimary: "#0B0B0F"
    readonly property color macTextSecondary: "#6B7280"
    readonly property string macTitleFont: "-apple-system"
    readonly property string macBodyFont: "-apple-system"

    // 状态属性：用于控制视频生成进度和按钮状态
    property bool isVideoGenerating: false
    property string videoStatusMessage: ""
    property bool videoPreviewOpened: false
    property string videoPath: ""
    property string videoLocalPath: ""
    property string projectVideoUrl: ""
    property bool previewOpenInProgress: false

    // 基础常量：API 地址前缀
    readonly property string apiBaseUrl: (viewModel && viewModel.apiBaseUrl)
                                         ? viewModel.apiBaseUrl
                                         : "http://127.0.0.1:8080"

    // ----------------------------------------------------
    // 1. 接收属性 (从 CreatePage 导航时传递)
    // ----------------------------------------------------
    property string storyId: ""         // 接收项目 ID
    property string storyTitle: ""      // 接收项目标题
    property var shotsData: []          // 接收分镜列表 (QVariantList)

    // 【核心修复】接收 StackView 的引用 (需要 CreatePage.qml 传递 pageStack)
    property var stackViewRef: null

    // ----------------------------------------------------
    // 2. 数据模型
    // ----------------------------------------------------
    ListModel {
        id: storyboardModel
    }
    // ----------------------------------------------------
    // 4. 页面初始化和信号连接
    // ----------------------------------------------------
    Component.onCompleted: {
        // [新增调试] 检查 viewModel 对象是否有效
        if (viewModel) {
            console.log("DEBUG: ViewModel target is valid (Object found).");
        } else {
            console.error("FATAL ERROR: ViewModel target is null or undefined!");
        }

        if (shotsData && shotsData.length > 0) {
            loadShotsModel(shotsData);
        } else {
            console.warn("Component.onCompleted: shotsData 为空。");
        }

        if (!stackViewRef && StackView.view) {
            stackViewRef = StackView.view;
        }
        refreshProjectVideo();

        if (viewModel && storyId.length > 0) {
            viewModel.refreshShots(storyId);
        }

        console.log("DEBUG CHECK: Now defining the ViewModel signal CONNECTIONS block.");
    }

    Connections {
        target: viewModel

        function onStoryboardGenerated(storyData) {
            storyId = storyData.id;
            storyTitle = storyData.title;
            videoPreviewOpened = false;
            isVideoGenerating = false;
            videoStatusMessage = "";
            loadShotsModel(storyData.shots);
            refreshProjectVideo(storyData.videoLocalPath, storyData.videoPath);
        }

        function onShotListUpdated(storyData) {
            if (storyData.id !== storyboardPage.storyId) {
                return;
            }
            if (storyData.title) {
                storyTitle = storyData.title;
            }
            loadShotsModel(storyData.shots);
            refreshProjectVideo(storyData.videoLocalPath, storyData.videoPath);
        }

        // [核心] 视频进度连接 (使用 sId, pct 避免冲突)

        function onCompilationProgress(storyId, percent) {
            // C++ 信号参数名：storyId, percent
            console.log("DEBUG A2: onCompilationProgress HANDLER FIRED. Progress:", percent, "ID:", storyId);

            if (storyId === storyboardPage.storyId) {
                console.log("QML DEBUG A2: Project ID Match (Signal ID === Page ID).");

                storyboardPage.isVideoGenerating = (percent < 100);
                storyboardPage.videoStatusMessage = qsTr("视频合成中 (%1)...").arg(percent);
            } else {
                console.warn("QML WARNING A2: Project ID Mismatch. Ignoring signal.");
            }
        }

        function onVideoGenerationFinished(storyId, videoUrl) {
            if (storyId !== storyboardPage.storyId) {
                return;
            }
            if (videoPreviewOpened) {
                return;
            }
            videoPreviewOpened = true;
            storyboardPage.isVideoGenerating = false;
            storyboardPage.videoStatusMessage = qsTr("合成完成");
            projectVideoUrl = videoUrl;
            displayVideoResource(storyId, videoUrl);
        }

        function onGenerationFailed(errorMsg) {
            storyboardPage.isVideoGenerating = false;
            storyboardPage.videoStatusMessage = qsTr("生成失败: %1").arg(errorMsg);
            console.error("生成失败:", errorMsg);
        }

        function onImageGenerationFinished(shotId, imageUrl) {
            for (var i = 0; i < storyboardModel.count; i++) {
                var shot = storyboardModel.get(i);
                if (shot.shotId === shotId) {
                    storyboardModel.setProperty(i, "imageUrl", imageUrl);
                    storyboardModel.setProperty(i, "status", "generated");
                    break;
                }
            }
        }
    }

    // ----------------------------------------------------
    // 5. UI 布局
    // ----------------------------------------------------
    Rectangle {
        anchors.fill: parent
        color: macBackground

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        // ========== 顶部导航栏 ==========
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Button {
                text: "← 返回"
                font.family: macBodyFont
                background: Rectangle {
                    radius: 10
                    color: "transparent"
                    border.color: macBorder
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
                    var stackView = resolveStackView();
                    if (stackView) {
                        stackView.pop();
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: storyTitle.length > 0 ? storyTitle : qsTr("故事板预览")
                    font.pixelSize: 20
                    font.bold: true
                    font.family: macTitleFont
                    color: macTextPrimary
                }

                Text {
                    text: qsTr("项目 ID: %1 · %2 个分镜").arg(storyId.length > 0 ? storyId : "N/A").arg(storyboardModel.count)
                    font.pixelSize: 13
                    font.family: macBodyFont
                    color: macTextSecondary
                }
            }
        }

        // ========== 分镜列表 (GridView) ==========
        GridView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: storyboardModel
            cellWidth: 320
            cellHeight: 320
            clip: true
            z: 0

            delegate: Item {
                width: GridView.view.cellWidth
                height: GridView.view.cellHeight

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 6
                    radius: 14
                    border.color: macBorder
                    border.width: 1
                    color: macCard

                    // 点击区域 (用于导航到 ShotDetailPage)
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            // [核心修复] 使用 StackView 引用进行导航
                            var stackView = resolveStackView();
                            if (!stackView) {
                                console.error("导航失败：StackView 引用不可用。");
                                return;
                            }
                            stackView.push(Qt.resolvedUrl("ShotDetailPage.qml"), {
                                shotData: {
                                    shotId: model.shotId,
                                    shotOrder: model.shotOrder,
                                    shotTitle: model.shotTitle,
                                    shotDescription: model.shotDescription,
                                    shotPrompt: model.shotPrompt,
                                    status: model.status,
                                    imageUrl: model.imageUrl,
                                    transition: model.transition
                                }
                            });
                        }

                        // ... (布局内容)
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 5

                            // 1. 状态标签和图像预览
                            RowLayout {
                                Layout.fillWidth: true

                                Text {
                                    text: mapStatus(model.status).text
                                    color: mapStatus(model.status).color
                                    font.pixelSize: 12
                                    font.bold: true
                                    Layout.fillWidth: true
                                }

                                // 2. 图像预览区
                                Rectangle {
                                    Layout.preferredWidth: 100
                                    Layout.preferredHeight: 100
                                    color: "#ECEFF1"

                                    Image {
                                        id: thumbImage
                                        source: model.imageUrl
                                        anchors.fill: parent
                                        fillMode: Image.PreserveAspectFit
                                        cache: false
                                        property int retryCount: 0
                                        onSourceChanged: retryCount = 0
                                        onStatusChanged: {
                                            if (status === Image.Error && model.imageUrl && retryCount < 2) {
                                                retryCount += 1;
                                                var sep = model.imageUrl.indexOf("?") >= 0 ? "&" : "?";
                                                source = model.imageUrl + sep + "retry=" + Date.now();
                                            }
                                        }
                                    }
                                }
                            }

                            // 3. 分镜序号和描述
                            Text {
                                text: qsTr("分镜 %1: %2").arg(model.shotOrder).arg(model.shotTitle)
                                font.bold: true
                                font.family: macTitleFont
                                color: macTextPrimary
                                Layout.fillWidth: true
                            }
                            Text {
                                text: model.shotDescription
                                font.pixelSize: 12
                                font.family: macBodyFont
                                color: macTextSecondary
                                Layout.maximumHeight: 40
                                elide: Text.ElideRight
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }
        }

        // 视频生成按钮
        Button {
            // [修复] 兼容 Qt 5.8 语法
            text: isVideoGenerating
                ? qsTr("合成中 (%1)").arg(
                    (videoStatusMessage.match(/(\d+%)/) && videoStatusMessage.match(/(\d+%)/)[1])
                        ? videoStatusMessage.match(/(\d+%)/)[1]
                        : "..."
                  )
                : qsTr("生成最终视频")

            Layout.fillWidth: true
            Layout.preferredHeight: 44
            enabled: !isVideoGenerating && storyboardModel.count > 0 && storyId.length > 0
            font.pixelSize: 15
            font.bold: true
            font.family: macBodyFont
            background: Rectangle {
                radius: 14
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#4A8BFF" }
                    GradientStop { position: 1.0; color: "#2D6BFF" }
                }
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
                if (!isVideoGenerating) {
                    viewModel.startVideoCompilation(storyId);
                    isVideoGenerating = true;
                    videoStatusMessage = qsTr("启动合成...");
                    videoPreviewOpened = false;
                }
            }
        }

        Button {
            text: qsTr("打开成品预览")
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            enabled: storyboardModel.count > 0
            z: 2
            font.pixelSize: 14
            font.family: macBodyFont
            background: Rectangle {
                radius: 14
                color: enabled ? "white" : "#E5E7EB"
                border.color: macBorder
            }
            contentItem: Text {
                text: parent.text
                color: enabled ? macTextPrimary : macTextSecondary
                font.pixelSize: 14
                font.family: macBodyFont
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            onPressed: {
                openPreviewFromButton();
            }
        }

        // 状态消息显示
        Label {
            text: videoStatusMessage
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            font.family: macBodyFont
            font.pixelSize: 13
            color: isVideoGenerating ? "#2563EB" : (videoStatusMessage.includes("成功") ? "#34C759" : "#FF3B30")
        }
    }
    }


    // ----------------------------------------------------
    // 3. 核心函数：数据加载与跳转
    // ----------------------------------------------------
    function normalizeLocalVideoUrl(path) {
        if (!path || path.length === 0) {
            return "";
        }
        if (path.indexOf("file://") === 0) {
            return path;
        }
        return "file://" + path;
    }

    function normalizeRemoteVideoUrl(path) {
        if (!path || path.length === 0) {
            return "";
        }
        if (path.indexOf("http") === 0) {
            return path;
        }
        return apiBaseUrl + path;
    }

    function resolvePreviewUrl() {
        refreshProjectVideo();
        if (projectVideoUrl && projectVideoUrl.length > 0) {
            return projectVideoUrl;
        }
        if (viewModel && storyId.length > 0 && viewModel.getProjectVideoLocalPath) {
            var diskPath = viewModel.getProjectVideoLocalPath(storyId);
            if (diskPath && diskPath.length > 0) {
                var diskUrl = normalizeLocalVideoUrl(diskPath);
                projectVideoUrl = diskUrl;
                return diskUrl;
            }
        }
        if (videoLocalPath && videoLocalPath.length > 0) {
            var localUrl = normalizeLocalVideoUrl(videoLocalPath);
            projectVideoUrl = localUrl;
            return localUrl;
        }
        if (videoPath && videoPath.length > 0) {
            var remoteUrl = normalizeRemoteVideoUrl(videoPath);
            projectVideoUrl = remoteUrl;
            return remoteUrl;
        }
        return "";
    }

    function openPreviewFromButton() {
        if (previewOpenInProgress) {
            return;
        }
        previewOpenInProgress = true;
        videoStatusMessage = qsTr("正在打开成品预览...");
        var url = resolvePreviewUrl();
        if (url.length > 0) {
            displayVideoResource(storyId, url);
        } else {
            videoStatusMessage = qsTr("未找到成品视频");
        }
        previewOpenInProgress = false;
    }

    function refreshProjectVideo(localPath, remotePath) {
        var localCandidate = localPath || videoLocalPath || "";
        var remoteCandidate = remotePath || videoPath || "";
        if (viewModel && storyId.length > 0 && viewModel.getProjectVideoLocalPath) {
            var diskPath = viewModel.getProjectVideoLocalPath(storyId);
            if (diskPath && diskPath.length > 0) {
                localCandidate = diskPath;
                videoLocalPath = diskPath;
            }
        }
        updateProjectVideo(localCandidate, remoteCandidate);
    }

    function updateProjectVideo(localPath, remotePath) {
        var nextUrl = "";
        if (localPath && localPath.length > 0) {
            nextUrl = normalizeLocalVideoUrl(localPath);
        } else if (remotePath && remotePath.length > 0) {
            nextUrl = normalizeRemoteVideoUrl(remotePath);
        }
        if (nextUrl.length > 0 && nextUrl !== projectVideoUrl) {
            projectVideoUrl = nextUrl;
        }
    }

    function loadShotsModel(shotsList) {
        console.log("--- DEBUG: loadShotsModel 函数已运行 ---");

        if (!shotsList || shotsList.length === 0) return;

        var canUpdateInPlace = storyboardModel.count === shotsList.length;
        if (canUpdateInPlace) {
            for (var j = 0; j < shotsList.length; j++) {
                var existing = storyboardModel.get(j);
                if (!existing || existing.shotId !== shotsList[j].id) {
                    canUpdateInPlace = false;
                    break;
                }
            }
        }

        if (!canUpdateInPlace) {
            storyboardModel.clear();
        }

        for (var i = 0; i < shotsList.length; i++) {
            var shot = shotsList[i];
            var existingRow = canUpdateInPlace ? storyboardModel.get(i) : null;

            // 调试输出 (用于验证数据完整性)
            console.log("Shot " + (i + 1) + " ID:", shot.id,
                        "Title:", shot.title,
                        "Prompt:", shot.prompt);

            // 构造完整的图像 URL（优先使用服务端给出的绝对 URL）
            var fullImageUrl = "";
            if (shot.imageUrl && shot.imageUrl.length > 0) {
                fullImageUrl = shot.imageUrl;
            } else if (shot.imagePath && shot.imagePath.length > 0) {
                if (shot.imagePath.toLowerCase().startsWith("http")) {
                    fullImageUrl = shot.imagePath;
                } else {
                    fullImageUrl = apiBaseUrl + shot.imagePath;
                }
            }

            if (existingRow && fullImageUrl) {
                var existingUrl = existingRow.imageUrl || "";
                var existingUpdatedAt = existingRow.updatedAt || "";
                var newUpdatedAt = shot.updatedAt || "";

                var existingBase = existingUrl.split("?")[0];
                var nextBase = fullImageUrl.split("?")[0];

                if (existingBase !== nextBase) {
                    // 文件名变了，直接使用新 URL
                } else {
                    // 文件名没变，检查 updatedAt
                    if (newUpdatedAt > existingUpdatedAt) {
                         // 内容已更新，强制刷新
                         var sep = fullImageUrl.indexOf("?") >= 0 ? "&" : "?";
                         fullImageUrl = fullImageUrl + sep + "v=" + Date.now();
                    } else {
                         // 内容未更新，保留旧 URL (避免签名变化导致的闪烁)
                         fullImageUrl = existingUrl;
                    }
                }
            }

            var row = {
                // ListModel 的键名
                shotId: shot.id,
                shotOrder: shot.order,
                shotTitle: shot.title,
                shotDescription: shot.description,
                shotPrompt: shot.prompt,
                status: shot.status,
                imageUrl: fullImageUrl,
                transition: shot.transition,
                updatedAt: shot.updatedAt // [新增] 保存时间戳
            };

            if (canUpdateInPlace) {
                storyboardModel.set(i, row);
            } else {
                storyboardModel.append(row);
            }
        }

        console.log("DEBUG: ListModel 填充完成，总数:", storyboardModel.count);
        storyboardPage.title = qsTr("故事板预览: %1").arg(storyTitle);
    }

    // *** 视频合成完成后的跳转函数 (使用 stackViewRef) ***
    function displayVideoResource(projectId, videoUrl) {
        if (!videoUrl || videoUrl.length === 0) {
            console.error("预览失败：视频地址为空");
            videoStatusMessage = qsTr("预览失败：视频地址为空");
            videoPreviewOpened = false;
            return;
        }

        // --- DIAGNOSTIC LOG 1: Function Entry ---
        console.log("NAV DEBUG 1: Display resource function entered. Project:", projectId);
        console.log("NAV DEBUG 2: Checking stackViewRef validity (Type):", typeof stackViewRef);

        // 【核心修复】使用 Qt.callLater 延迟执行
        Qt.callLater(function() {
            // --- DIAGNOSTIC LOG 3: CallLater Execution ---
            console.log("NAV DEBUG 3: Qt.callLater executed (Next event loop).");

            var stackView = resolveStackView();
            if (stackView) {
                // --- DIAGNOSTIC LOG 4: Valid Stack Reference ---
                console.log("NAV DEBUG 4: Stack reference found. Attempting push...");

                try {
                    // 使用传递进来的 StackView 引用进行 push
                    stackView.push(Qt.resolvedUrl("PreviewPage.qml"), {
                        videoSource: videoUrl,
                        projectId: projectId,
                        showStoryboardButton: true
                    });
                    console.log("✅ NAV SUCCESS: PreviewPage push succeeded.");
                    videoStatusMessage = "";
                } catch (e) {
                    console.error("❌ NAV FAILURE 5: Error during stack push (Method failed).", e);
                    videoStatusMessage = qsTr("预览失败：无法打开页面");
                    videoPreviewOpened = false;
                }
            } else {
                console.error("❌ NAV FAILURE 5: stackViewRef is NULL. Navigation skipped.");
                videoStatusMessage = qsTr("预览失败：导航栈不可用");
                videoPreviewOpened = false;
            }
        });
    }

    function resolveStackView() {
        if (stackViewRef) {
            return stackViewRef;
        }
        if (typeof pageStack !== "undefined" && pageStack) {
            return pageStack;
        }
        if (StackView.view) {
            return StackView.view;
        }
        return null;
    }



    // ----------------------------------------------------
    // 6. 状态映射辅助函数
    // ----------------------------------------------------
    function mapStatus(status) {
        switch (status) {
            case "finished":
            case "generated": return { color: "#4CAF50", text: qsTr("✓ 已完成") };
            case "completed": return { color: "#4CAF50", text: qsTr("✓ 已完成") };
            case "pending":
            case "running": case "processing": return { color: "#FFC107", text: qsTr("... 生成中") };
            case "error": case "failed": return { color: "#F44336", text: qsTr("✗ 失败") };
            default: return { color: "gray", text: qsTr("未知") };
        }
    }
}
