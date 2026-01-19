// main.cpp (修改版)
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext> // 必须
#include <QDir>
#include <QQuickStyle>
#include "ViewModel.h"
#include "datamanager.h" // 引入你的本地存储管理类
#include "videoexporter.h"

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    
    // 设置 QML 控件样式为 Basic（跨平台兼容）
    QQuickStyle::setStyle("Basic");
    
    QQmlApplicationEngine engine;
    
    // 添加 QML 导入路径（用于打包后的应用）
    QString appDir = QCoreApplication::applicationDirPath();
    engine.addImportPath(appDir + "/../Resources/qml");

    // 1️⃣ 实例化 ViewModel 对象
    ViewModel *viewModel = new ViewModel();

    // 2️⃣ 实例化 DataManager 对象
    DataManager *dataManager = new DataManager();

    // 3️⃣ 将 C++ 对象暴露给 QML
    engine.rootContext()->setContextProperty("viewModel", viewModel);
    engine.rootContext()->setContextProperty("dataManager", dataManager); // ✅ 关键
    // 注册 VideoExporter
    VideoExporter *videoExporter = new VideoExporter();
    engine.rootContext()->setContextProperty("videoExporter", videoExporter);

    // 4️⃣ 加载主 QML
    const QUrl url(QStringLiteral("qrc:/qml/main.qml"));
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreated,
                     &app, [url](QObject *obj, const QUrl &objUrl) {
        if (!obj && url == objUrl)
            QCoreApplication::exit(-1);
    }, Qt::QueuedConnection);
    engine.load(url);

    return app.exec();
}
