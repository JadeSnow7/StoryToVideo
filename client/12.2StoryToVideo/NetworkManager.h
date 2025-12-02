#ifndef NETWORKMANAGER_H
#define NETWORKMANAGER_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QString>
#include <QUrl>
#include <QVariantMap>
#include <QVariantList>

class NetworkManager : public QObject
{
    Q_OBJECT
public:
    explicit NetworkManager(QObject *parent = nullptr);

    // --- 1. 项目创建 (Direct / projects API) ---
    // 负责创建项目并获取所有 Task IDs
    void createProjectDirect(const QString &title, const QString &storyText, const QString &style, const QString &description);

    // --- 2. 资源获取 API (项目/分镜数据) ---
    // [新增] 获取分镜列表，用于文本任务完成后
    void getShotListRequest(const QString &projectId);

    // --- 3. 任务 API 请求 (异步 / tasks API) ---
    void updateShotRequest(int shotId, const QString &prompt, const QString &style);
    void generateVideoRequest(const QString &projectId);

    // --- 4. 任务状态查询 API ---
    void pollTaskStatus(const QString &taskId);


signals:
    // [修改] 1. 文本任务创建成功信号：返回 ProjectID 和所有 Task IDs
    void textTaskCreated(const QString &projectId, const QString &textTaskId, const QVariantList &shotTaskIds);

    // [保留] 2. 业务请求成功并返回 task_id (用于分镜重生成/视频)
    void taskCreated(const QString &taskId, int shotId = 0);

    // [保留] 3. 任务状态更新 (用于轮询)
    void taskStatusReceived(const QString &taskId, int progress, const QString &status, const QString &message);

    // [保留] 4. 任务完成并返回最终结果 (用于分镜/视频任务)
    void taskResultReceived(const QString &taskId, const QVariantMap &resultData);

    // [新增] 5. 分镜列表获取成功信号
    void shotListReceived(const QString &projectId, const QVariantList &shots);

    // [保留] 6. 错误信号
    void taskRequestFailed(const QString &taskId, const QString &errorMsg);
    void networkError(const QString &errorMsg);

private slots:
    void onNetworkReplyFinished(QNetworkReply *reply);

private:
    QNetworkAccessManager *m_networkManager;

    const QUrl PROJECT_API_URL = QUrl("http://119.45.124.222:8081/v1/api/projects");
    const QUrl TASK_API_BASE_URL = QUrl("http://119.45.124.222:8081/v1/api/tasks");

    enum RequestType {
        CreateProjectDirect = 1,
        UpdateShot = 2,
        GenerateVideo = 3,
        PollStatus = 4,
        // [新增] 资源获取类型
        GetShotList = 5
    };
};

#endif // NETWORKMANAGER_H
