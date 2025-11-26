// main.cpp (片段)
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext> // 关键头文件
#include "ViewModel.h" // 引入我们创建的 ViewModel 类

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QQmlApplicationEngine engine;

    // 1. 实例化 C++ ViewModel 对象
    ViewModel *viewModel = new ViewModel();

    // 2. 将 C++ 对象暴露给 QML 上下文
    // QML 中可以使用 'viewModel' 这个名称来访问这个 C++ 对象
    engine.rootContext()->setContextProperty("viewModel", viewModel);

    // ...
    // engine.load(url); // 加载 QML 文件
    // ...

    // 确保在 engine.load() 之前设置 context property
    const QUrl url(QStringLiteral("qrc:/main.qml"));
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreated,
                     &app, [url](QObject *obj, const QUrl &objUrl) {
        if (!obj && url == objUrl)
            QCoreApplication::exit(-1);
    }, Qt::QueuedConnection);
    engine.load(url);

    return app.exec();
}
