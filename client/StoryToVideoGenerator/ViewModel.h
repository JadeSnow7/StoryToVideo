#ifndef VIEWMODEL_H
#define VIEWMODEL_H

#include <QObject>
#include <QString>
#include <QVariant>
#include <QVariantMap>

class NetworkManager; // 前置声明

class ViewModel : public QObject
{
    Q_OBJECT

public:
    explicit ViewModel(QObject *parent = nullptr);

    // QML 可调用函数 (Q_INVOKABLE)
    Q_INVOKABLE void generateStoryboard(const QString &storyText, const QString &style);
    Q_INVOKABLE void startVideoCompilation(const QString &storyId);
    Q_INVOKABLE void generateShotImage(int shotId, const QString &prompt, const QString &transition);

signals:
    // C++ 发出，QML 接收的信号
    void storyboardGenerated(const QVariant &storyData);
    void generationFailed(const QString &errorMsg);
    void imageGenerationFinished(int shotId, const QString &imageUrl);
    void compilationProgress(const QString &storyId, int percent);

private slots:
    // 内部槽函数：处理 NetworkManager 的回复
    void handleOllamaResponse(const QString &ollamaRawResponse);
    void handleImageResponse(int shotId, const QString &base64Image);
    void handleNetworkError(const QString &errorMsg);

private:
    NetworkManager *m_networkManager; // 实际执行网络请求的对象
};

#endif // VIEWMODEL_H
