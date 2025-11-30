#include "ViewModel.h"
#include "NetworkManager.h"
#include <QDebug>
#include <QDateTime>
#include <QTimer>
#include <QVariantMap>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QUrl>
#include <QCoreApplication>
#include <QDir>


// ==========================================================
// C++ 实现
// ==========================================================

ViewModel::ViewModel(QObject *parent) : QObject(parent)
{
    m_networkManager = new NetworkManager(this);
    m_pollingTimer = new QTimer(this);

    // 连接网络管理器的信号到 ViewModel 的槽函数
    // 注意：项目创建现在直接连接到 handleTaskCreated
    connect(m_networkManager, &NetworkManager::taskCreated,
            this, &ViewModel::handleTaskCreated);
    connect(m_networkManager, &NetworkManager::taskStatusReceived,
            this, &ViewModel::handleTaskStatusReceived);
    connect(m_networkManager, &NetworkManager::taskResultReceived,
            this, &ViewModel::handleTaskResultReceived);
    connect(m_networkManager, &NetworkManager::taskRequestFailed,
            this, &ViewModel::handleTaskRequestFailed);

    connect(m_networkManager, &NetworkManager::networkError,
            this, &ViewModel::handleNetworkError);

    // 连接定时器
    connect(m_pollingTimer, &QTimer::timeout, this, &ViewModel::pollCurrentTask);
    m_pollingTimer->setInterval(1000); // 每 1 秒轮询一次

    qDebug() << "ViewModel 实例化成功，等待网络请求。";
}


void ViewModel::generateStoryboard(const QString &storyText, const QString &style)
{
    qDebug() << ">>> C++ 收到请求：生成项目并启动分镜任务，委托给 NetworkManager。";

    // 构造 Title 和 Description
    QString title = "新故事项目 - " + QDateTime::currentDateTime().toString("yyyyMMdd_hhmmss");
    QString description = "由用户输入的文本创建的项目。";

    // 触发项目创建 (API 1: POST /v1/api/projects)，它将返回 TaskID
    m_networkManager->createProjectDirect(
        title,
        storyText,
        style,
        description
    );
}

void ViewModel::startVideoCompilation(const QString &storyId)
{
    qDebug() << ">>> C++ 收到请求：生成视频，委托给 NetworkManager for ID:" << storyId;
    // 假设 storyId 即为 ProjectId
    m_networkManager->generateVideoRequest(storyId);
}

void ViewModel::generateShotImage(int shotId, const QString &prompt, const QString &transition)
{
    qDebug() << ">>> C++ 收到请求：生成单张图像 Shot:" << shotId;
    m_networkManager->updateShotRequest(shotId, prompt, transition);
}


// --- 任务轮询管理逻辑 ---

void ViewModel::handleTaskCreated(const QString &taskId, int shotId)
{
    qDebug() << "ViewModel: 收到新任务 Task ID:" << taskId;

    QVariantMap taskInfo;
    taskInfo["id"] = shotId;
    QString finalTaskId = taskId;
    finalTaskId = "124";  //静态调试123
    // shotId=0 代表是项目创建/视频生成任务
    if (shotId == 0) {
        // 项目创建任务或视频生成任务都视为 story/video 级别任务
        taskInfo["type"] = "story";
        // 我们不知道 Project ID，但任务 ID 够用
        taskInfo["id"] = QString("TASK-%1").arg(finalTaskId);
    } else {
        // 更新分镜任务
        taskInfo["type"] = "shot";
    }

    m_activeTasks.insert(finalTaskId, taskInfo);

    startPollingTimer();
}


void ViewModel::handleTaskStatusReceived(const QString &taskId, int progress, const QString &status, const QString &message)
{
    if (m_activeTasks.contains(taskId)) {
        QVariantMap taskInfo = m_activeTasks[taskId];
        QString type = taskInfo["type"].toString();

        if (type == "story" || type == "video") {
            // 视频合成或故事板生成进度
            emit compilationProgress(taskInfo["id"].toString(), progress);
        } else if (type == "shot") {
            // 图像生成进度
            qDebug() << "Shot ID:" << taskInfo["id"].toInt() << " Progress:" << progress;
        }

        // 用于解决警告，实际使用 status 和 message
        qDebug() << "Task:" << taskId << " Status:" << status << " Message:" << message;
    }
}


void ViewModel::handleTaskResultReceived(const QString &taskId, const QVariantMap &resultData)
{
    if (m_activeTasks.contains(taskId)) {
        QVariantMap taskInfo = m_activeTasks[taskId];
        QString type = taskInfo["type"].toString();
        QString storyId = taskInfo["id"].toString(); // 可能是 ProjectID 或占位符

        if (type == "story") {
            // 故事板生成任务完成
            processStoryboardResult(taskId, resultData);
        } else if (type == "shot") {
            // 图像生成完成
            processImageResult(taskInfo["id"].toInt(), resultData);
        } else if (type == "video") {
            // 视频合成完成
            processVideoResult(storyId, resultData);
        }

        stopPollingTimer(taskId); // 停止该任务的轮询
    }
}


void ViewModel::handleTaskRequestFailed(const QString &taskId, const QString &errorMsg)
{
    if (m_activeTasks.contains(taskId)) {
        QVariantMap taskInfo = m_activeTasks[taskId];
        qDebug() << "任务轮询失败:" << taskId << errorMsg;
        emit generationFailed(QString("任务 %1 失败: %2").arg(taskInfo["id"].toString()).arg(errorMsg));
        stopPollingTimer(taskId);
    }
}


// --- 定时器管理 ---
void ViewModel::startPollingTimer()
{
    if (!m_pollingTimer->isActive()) {
        m_pollingTimer->start();
        qDebug() << "轮询定时器已启动。";
    }
}

void ViewModel::stopPollingTimer(const QString &taskId)
{
    m_activeTasks.remove(taskId); // 从活动列表中移除任务

    if (m_activeTasks.isEmpty() && m_pollingTimer->isActive()) {
        m_pollingTimer->stop();
        qDebug() << "所有任务完成，轮询定时器已停止。";
    }
}

void ViewModel::pollCurrentTask()
{
    if (m_activeTasks.isEmpty()) {
        m_pollingTimer->stop();
        return;
    }

    QList<QString> taskIds = m_activeTasks.keys();
    for (const QString &taskId : taskIds) {
        m_networkManager->pollTaskStatus(taskId);
    }
}

void ViewModel::handleNetworkError(const QString &errorMsg)
{
    qDebug() << "通用网络错误发生:" << errorMsg;
    emit generationFailed(QString("网络通信失败: %1").arg(errorMsg));
}


// --- 结果处理辅助函数 ---

void ViewModel::processStoryboardResult(const QString &taskId, const QVariantMap &resultData)
{
    // 假设 resultData 结构为: { "task_shots": { "generated_shots": [ {title:..., prompt:...}, ... ] } }

    QVariantMap taskInfo = m_activeTasks[taskId];
    QString storyIdPlaceholder = taskInfo["id"].toString();

    QVariantMap taskShots = resultData["task_shots"].toMap();
    QVariantList shotsList = taskShots["generated_shots"].toList();

    // 从 shotsList 的第一个元素中提取 ProjectId (假设后端将 ProjectId 放在 shotsList 中)
    QString projectId = resultData["projectId"].toString(); // 假设 Project ID 在顶层返回

    if (shotsList.isEmpty()) {
        emit generationFailed("LLM 返回的分镜列表为空。");
        return;
    }

    QVariantMap storyMap;
    // 假设后端返回的 Project ID 才是真正的故事 ID
    storyMap["id"] = projectId.isEmpty() ? storyIdPlaceholder : projectId;
    storyMap["title"] = "LLM 生成的故事";
    storyMap["shots"] = shotsList;

    qDebug() << "LLM 解析成功，分镜数:" << shotsList.count();

    emit storyboardGenerated(QVariant::fromValue(storyMap));
}

void ViewModel::processImageResult(int shotId, const QVariantMap &resultData)
{
    // 假设 resultData 结构为: { "task_video": { "path": "/static/tasks/124/image.png", ... } }

    QVariantMap taskVideo = resultData["task_video"].toMap();
    QString imagePath = taskVideo["path"].toString();

    if (imagePath.isEmpty()) {
        emit generationFailed(QString("Shot %1: 图像生成 API 未返回路径。").arg(shotId));
        return;
    }

    // 构造 QML 可识别的 URL：http://119.45.124.222:8080/static/tasks/124/image.png
    QString qmlUrl = QString("http://119.45.124.222:8080%1").arg(imagePath);

    qDebug() << "图像生成成功，QML URL:" << qmlUrl;

    // --- 2. 保存到本地文件 (可选，如果 QML 需要本地文件路径) ---
    // 为了简化，我们依赖 QML 直接加载 URL

    emit imageGenerationFinished(shotId, qmlUrl);
}

void ViewModel::processVideoResult(const QString &storyId, const QVariantMap &resultData)
{
    // 假设 resultData 结构为: { "task_video": { "path": "/static/tasks/123/output.mp4", ... } }
    QVariantMap taskVideo = resultData["task_video"].toMap();
    QString videoPath = taskVideo["path"].toString();

    qDebug() << "视频生成成功，文件路径:" << videoPath;

    // 通知 QML 进度达到 100%
    emit compilationProgress(storyId, 100);
    // [TODO] 如果 QML 需要最终 URL，这里可以添加新的信号
}
