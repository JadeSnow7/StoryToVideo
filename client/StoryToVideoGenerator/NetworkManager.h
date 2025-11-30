#ifndef NETWORKMANAGER_H
#define NETWORKMANAGER_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QString>
#include <QUrl>
#include <QVariantMap>

class NetworkManager : public QObject
{
    Q_OBJECT
public:
    explicit NetworkManager(QObject *parent = nullptr);

    // --- 1. 项目创建 (Direct / projects API) ---
    // 负责创建项目并获取初始 TaskID
    void createProjectDirect(const QString &title, const QString &storyText, const QString &style, const QString &description);

    // --- 2. 任务 API 请求 (异步 / tasks API) ---
    // 仅用于后续步骤（如分镜重生成、视频合成），不用于首次故事板生成
    void updateShotRequest(int shotId, const QString &prompt, const QString &style);
    void generateVideoRequest(const QString &projectId);

    // --- 3. 任务状态查询 API ---
    void pollTaskStatus(const QString &taskId);


signals:
    // 1. 业务请求成功并返回 task_id (包括项目创建返回的第一个 TaskID)
    void taskCreated(const QString &taskId, int shotId = 0);

    // 2. 任务状态更新 (用于轮询)
    void taskStatusReceived(const QString &taskId, int progress, const QString &status, const QString &message);

    // 3. 任务完成并返回最终结果
    void taskResultReceived(const QString &taskId, const QVariantMap &resultData);

    // 4. 任务请求失败（如 404, 500 等，针对轮询）
    void taskRequestFailed(const QString &taskId, const QString &errorMsg);

    // 5. 通用错误信号
    void networkError(const QString &errorMsg);

private slots:
    // 处理所有请求的回复
    void onNetworkReplyFinished(QNetworkReply *reply);

private:
    QNetworkAccessManager *m_networkManager;

    // --- API 地址常量 ---
    const QUrl PROJECT_API_URL = QUrl("http://119.45.124.222:8080/v1/api/projects");
    const QUrl TASK_API_BASE_URL = QUrl("http://119.45.124.222:8080/v1/api/tasks");

    // 用于区分回复是来自 哪个操作
    enum RequestType {
        CreateProjectDirect = 1,     // 直接创建项目（现同时返回 TaskID）
        UpdateShot = 2,              // 任务创建：更新分镜
        GenerateVideo = 3,           // 任务创建：生成视频
        PollStatus = 4               // 任务查询
        // 移除 GenerateStoryboardTask
    };
};

#endif // NETWORKMANAGER_H
