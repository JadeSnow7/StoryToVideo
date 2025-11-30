#ifndef VIEWMODEL_H
#define VIEWMODEL_H

#include <QObject>
#include <QString>
#include <QVariant>
#include <QVariantMap>
#include <QTimer>
#include <QHash>

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
    // 任务状态管理槽函数
    void handleTaskCreated(const QString &taskId, int shotId);
    void handleTaskStatusReceived(const QString &taskId, int progress, const QString &status, const QString &message);
    void handleTaskResultReceived(const QString &taskId, const QVariantMap &resultData);
    void handleTaskRequestFailed(const QString &taskId, const QString &errorMsg);

    // 定时器相关
    void startPollingTimer();
    void stopPollingTimer(const QString &taskId);
    void pollCurrentTask();

    void handleNetworkError(const QString &errorMsg);


private:
    NetworkManager *m_networkManager;

    // 移除 m_currentStoryText, m_currentStyle, m_currentProjectId，因为不再需要存储过渡数据

    // 任务轮询相关
    QTimer *m_pollingTimer;
    // 存储所有正在轮询的任务 ID -> 对应的 QML ID (storyId 或 shotId)
    // key: taskId, value: QVariantMap{ "id": QML ID, "type": "story" or "shot" or "video" }
    QHash<QString, QVariantMap> m_activeTasks;

    // 私有辅助函数：处理故事板结果和图像结果
    void processStoryboardResult(const QString &taskId, const QVariantMap &resultData);
    void processImageResult(int shotId, const QVariantMap &resultData);
    void processVideoResult(const QString &storyId, const QVariantMap &resultData);

};

#endif // VIEWMODEL_H
