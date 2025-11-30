
// main.qml
import QtQuick 2.6            // 兼容 Qt 5.8.0
import QtQuick.Controls 2.1   // 兼容 Qt 5.8.0
import QtQuick.Layouts 1.2    // 兼容 Qt 5.8.0

// ApplicationWindow 是桌面应用的主窗口
ApplicationWindow {
    id: appWindow
    visible: true
    width: 1024
    height: 768
    title: qsTr("故事到视频生成器")

    // --- 核心导航结构：StackView ---
    // StackView 用于管理页面的堆栈，实现页面的前进(push)和后退(pop)
    StackView {
        id: pageStack // 定义 StackView 的 ID
        anchors.fill: parent

        // 应用程序启动时加载项目的首页，即 AssetsPage.qml
        initialItem: Qt.resolvedUrl("AssetsPage.qml")

        // 配置页面的默认属性，让子页面可以访问 StackView
        // 这样在任何子页面中，都可以通过 StackView.view.push() 来进行导航
    }

    // --- 关键修正说明 ---
    // 之前在子页面中直接调用 pageStack.clear() 可能失败，
    // 因为 pageStack 的 ID 作用域通常只在其定义的文件内。
    // 在子页面中，我们应使用 StackView.view.push/pop/clear() 进行操作。

    // 例如，在 PreviewPage.qml 中，您现在可以使用：
    // onClicked: StackView.view.clear();
    // 来安全地返回到 AssetsPage (栈底)。
}
