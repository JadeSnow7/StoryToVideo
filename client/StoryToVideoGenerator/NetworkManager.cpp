#include "NetworkManager.h"
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QDebug>
#include <QUrlQuery>

// 用户定义的属性 Key
const QNetworkRequest::Attribute ShotIdAttribute =
    (QNetworkRequest::Attribute)(QNetworkRequest::UserMax + 1);
const QNetworkRequest::Attribute RequestTypeAttribute =
    (QNetworkRequest::Attribute)(QNetworkRequest::UserMax + 2);
const QNetworkRequest::Attribute TaskIdAttribute =
    (QNetworkRequest::Attribute)(QNetworkRequest::UserMax + 3);


NetworkManager::NetworkManager(QObject *parent) : QObject(parent)
{
    m_networkManager = new QNetworkAccessManager(this);

    connect(m_networkManager, &QNetworkAccessManager::finished,
            this, &NetworkManager::onNetworkReplyFinished);

    qDebug() << "NetworkManager 实例化成功。";
}


// --- 1. 业务 API 请求：直接创建项目 (POST /v1/api/projects) ---
void NetworkManager::createProjectDirect(const QString &title, const QString &storyText, const QString &style, const QString &description)
{
    qDebug() << "发送 CreateProjectDirect 请求...";

    // 1. 构造带 Query 参数的完整 URL
    QUrl url(PROJECT_API_URL);
    QUrlQuery query;
    query.addQueryItem("Title", title);
    query.addQueryItem("StoryText", storyText);
    query.addQueryItem("Style", style);
    query.addQueryItem("Desription", description);
    url.setQuery(query);

    QNetworkRequest request(url);

    // 修复 Content-Type 警告
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    // 2. 设置请求类型和发送 POST 请求
    request.setAttribute(RequestTypeAttribute, NetworkManager::CreateProjectDirect);

    m_networkManager->post(request, QByteArray());
}


// --- 2. 任务 API 请求：更新分镜 (POST /v1/api/tasks) ---
void NetworkManager::updateShotRequest(int shotId, const QString &prompt, const QString &style)
{
    qDebug() << "发送 UpdateShot 请求...";

    QJsonObject requestJson;
    requestJson["type"] = "updateShot";
    requestJson["shotId"] = QString::number(shotId);

    QJsonObject parameters;
    QJsonObject shot;
    shot["style"] = style;
    shot["image_llm"] = prompt;
    shot["generate_tts"] = false;
    parameters["shot"] = shot;
    requestJson["parameters"] = parameters;

    QJsonDocument doc(requestJson);
    QByteArray postData = doc.toJson(QJsonDocument::Compact);

    QNetworkRequest request(TASK_API_BASE_URL);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    request.setAttribute(RequestTypeAttribute, NetworkManager::UpdateShot);
    request.setAttribute(ShotIdAttribute, shotId);

    m_networkManager->post(request, postData);
}


// --- 任务 API 请求：生成视频 (POST /v1/api/tasks) ---
void NetworkManager::generateVideoRequest(const QString &projectId)
{
    qDebug() << "发送 GenerateVideo 请求 for Project ID:" << projectId;

    QJsonObject requestJson;
    requestJson["type"] = "generateVideo";
    requestJson["projectId"] = projectId;

    QJsonObject parameters;
    QJsonObject video;
    video["format"] = "mp4";
    video["resolution"] = "1920x1080";
    parameters["video"] = video;
    requestJson["parameters"] = parameters;


    QJsonDocument doc(requestJson);
    QByteArray postData = doc.toJson(QJsonDocument::Compact);

    QNetworkRequest request(TASK_API_BASE_URL);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    request.setAttribute(RequestTypeAttribute, NetworkManager::GenerateVideo);

    m_networkManager->post(request, postData);
}

// --- 3. 任务状态查询 API (GET /v1/api/tasks/{task_id}) ---
void NetworkManager::pollTaskStatus(const QString &taskId)
{
    // GET http://119.45.124.222:8080/v1/api/tasks/{task_id}
    QUrl queryUrl = TASK_API_BASE_URL.toString() + "/" + taskId;
    qDebug() << "发送 PollTaskStatus 请求 for Task ID:" << taskId;

    QNetworkRequest request(queryUrl);
    request.setAttribute(RequestTypeAttribute, NetworkManager::PollStatus);
    request.setAttribute(TaskIdAttribute, taskId);

    m_networkManager->get(request);
}


void NetworkManager::onNetworkReplyFinished(QNetworkReply *reply)
{
    // --- 1. 检查网络错误 ---
    if (reply->error() != QNetworkReply::NoError) {
        QString errorMsg = QString("网络错误 (%1): %2").arg(reply->error()).arg(reply->errorString());
        qDebug() << errorMsg;

        RequestType type = (RequestType)reply->request().attribute(RequestTypeAttribute).toInt();
        if (type == NetworkManager::PollStatus) {
             QString taskId = reply->request().attribute(TaskIdAttribute).toString();
             emit taskRequestFailed(taskId, errorMsg);
        } else {
            emit networkError(errorMsg);
        }

        reply->deleteLater();
        return;
    }

    // --- 2. 区分请求类型并处理回复 ---
    QByteArray responseData = reply->readAll();
    RequestType type = (RequestType)reply->request().attribute(RequestTypeAttribute).toInt();

    // A. 处理直接创建项目 (Project) 的回复 (现同时返回 TaskID)
    if (type == NetworkManager::CreateProjectDirect)
    {
        QJsonDocument jsonDoc = QJsonDocument::fromJson(responseData);
        QJsonObject jsonObj = jsonDoc.object();

        QString projectId = jsonObj["ProjectID"].toString();
        QString taskId = jsonObj["TaskID"].toString(); // [新增/修改] 提取 TaskID

        if (taskId.isEmpty()) {
             qDebug() << "API 返回中未找到 TaskID。";
             emit networkError("项目创建成功但 API 返回中未找到 TaskID，无法开始分镜生成。");
        } else {
            qDebug() << "项目创建成功，Project ID:" << projectId << "，初始 Task ID:" << taskId;
            // 直接发出 taskCreated 信号，启动轮询
            emit taskCreated(taskId, 0);
        }
    }
    // B. 处理其他任务创建 (POST /v1/api/tasks) 回复
    else if (type == NetworkManager::UpdateShot ||
             type == NetworkManager::GenerateVideo)
    {
        QJsonDocument jsonDoc = QJsonDocument::fromJson(responseData);
        QJsonObject jsonObj = jsonDoc.object();

        QString taskId = jsonObj["task_id"].toString();

        if (taskId.isEmpty()) {
            qDebug() << "API 返回中未找到 task_id。";
            emit networkError("API 返回中未找到 task_id。");
        } else {
            qDebug() << "任务创建成功，Task ID:" << taskId;
            int shotId = (type == NetworkManager::UpdateShot) ? reply->request().attribute(ShotIdAttribute).toInt() : 0;
            emit taskCreated(taskId, shotId);
        }
    }
    // C. 任务状态查询 (GET) 回复
    else if (type == NetworkManager::PollStatus)
    {
        QString taskId = reply->request().attribute(TaskIdAttribute).toString();

        QJsonDocument jsonDoc = QJsonDocument::fromJson(responseData);
        QJsonObject jsonObj = jsonDoc.object();
        QJsonObject taskObj = jsonObj["task"].toObject();

        QString status = taskObj["status"].toString();
        int progress = taskObj["progress"].toInt();
        QString message = taskObj["message"].toString();

        qDebug() << "Task ID:" << taskId << " Status:" << status << " Progress:" << progress;

        if (status == "finished") {
            // 任务完成，提取 result 字段
            QJsonObject resultObj = taskObj["result"].toObject();
            QVariantMap resultMap = resultObj.toVariantMap();

            emit taskResultReceived(taskId, resultMap);
        } else {
            // 任务进行中
            emit taskStatusReceived(taskId, progress, status, message);
        }
    }

    reply->deleteLater();
}
