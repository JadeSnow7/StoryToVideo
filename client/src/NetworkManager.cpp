#include "NetworkManager.h"
#include <QDebug>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrlQuery>

// 用户定义的属性 Key
const QNetworkRequest::Attribute ShotIdAttribute =
    (QNetworkRequest::Attribute)(QNetworkRequest::UserMax + 1);
const QNetworkRequest::Attribute RequestTypeAttribute =
    (QNetworkRequest::Attribute)(QNetworkRequest::UserMax + 2);
const QNetworkRequest::Attribute TaskIdAttribute =
    (QNetworkRequest::Attribute)(QNetworkRequest::UserMax + 3);

NetworkManager::NetworkManager(QObject *parent) : QObject(parent) {
  m_networkManager = new QNetworkAccessManager(this);

  connect(m_networkManager, &QNetworkAccessManager::finished, this,
          &NetworkManager::onNetworkReplyFinished);

  qDebug() << "NetworkManager 实例化成功。";
}

// --- 1. 业务 API 请求：直接创建项目 (POST /v1/api/projects) ---
void NetworkManager::createProjectDirect(const QString &title,
                                         const QString &storyText,
                                         const QString &style,
                                         const QString &description) {
  qDebug() << "发送 CreateProjectDirect 请求...";

  // 构造带 Query 参数的完整 URL
  QUrl url(PROJECT_API_URL);
  QUrlQuery query;
  query.addQueryItem("Title", title);
  query.addQueryItem("StoryText", storyText);
  query.addQueryItem("Style", style);
  query.addQueryItem("Desription", description);
  url.setQuery(query);

  QNetworkRequest request(url);
  request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
  request.setAttribute(RequestTypeAttribute,
                       NetworkManager::CreateProjectDirect);

  m_networkManager->post(request, QByteArray());
}

// --- 2. 资源获取 API：获取分镜列表 (GET /v1/api/projects/:id/shots) ---
void NetworkManager::getShotListRequest(const QString &projectId) {
  // GET {apiBaseUrl}/v1/api/projects/:projectId/shots
  QUrl queryUrl = PROJECT_API_URL.toString() + "/" + projectId + "/shots";
  qDebug() << "发送 GetShotList 请求 for Project ID:" << projectId;

  QNetworkRequest request(queryUrl);
  request.setAttribute(RequestTypeAttribute, NetworkManager::GetShotList);

  // 存储 projectId，用于在回复时关联数据
  request.setRawHeader("X-Project-Id", projectId.toUtf8());

  m_networkManager->get(request);
}

// --- 3. 任务 API 请求：更新分镜 (POST /v1/projects/:project_id/shots/:shot_id)
// ---
void NetworkManager::updateShotRequest(const QString &projectId,
                                       const QString &shotId,
                                       const QString &prompt,
                                       const QString &style) {
  // Gateway 使用 /v1/projects/{project_id}/shots/{shot_id} 来更新分镜
  QUrl url =
      QUrl(PROJECT_API_URL.toString() + "/" + projectId + "/shots/" + shotId);
  qDebug() << "发送 UpdateShot 请求 URL:" << url;

  QJsonObject requestJson;
  requestJson["style"] = style;
  requestJson["prompt"] = prompt;

  QJsonDocument doc(requestJson);
  QByteArray postData = doc.toJson(QJsonDocument::Compact);

  QNetworkRequest request(url);
  request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

  request.setAttribute(RequestTypeAttribute, NetworkManager::UpdateShot);
  request.setAttribute(ShotIdAttribute, shotId);

  m_networkManager->post(request, postData);
}

// --- 4. 任务 API 请求：生成视频 (POST /v1/api/projects/:project_id/video) ---
void NetworkManager::generateVideoRequest(const QString &projectId) {
  // Gateway 使用 /v1/api/projects/{project_id}/video 来生成视频
  QUrl url = QUrl(PROJECT_API_URL.toString() + "/" + projectId + "/video");
  qDebug() << "发送 GenerateVideo 请求 for Project ID:" << projectId
           << "URL:" << url;

  QJsonObject requestJson;
  requestJson["format"] = "mp4";
  requestJson["resolution"] = "1920x1080";

  QJsonDocument doc(requestJson);
  QByteArray postData = doc.toJson(QJsonDocument::Compact);

  QNetworkRequest request(url);
  request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

  request.setAttribute(RequestTypeAttribute, NetworkManager::GenerateVideo);

  m_networkManager->post(request, postData);
}

// --- 5. 任务状态查询 API (GET /v1/api/tasks/:task_id) ---
void NetworkManager::pollTaskStatus(const QString &taskId) {
  QUrl queryUrl = TASK_API_BASE_URL.toString() + "/" + taskId;
  qDebug() << "发送 PollTaskStatus 请求 for Task ID:" << taskId;

  QNetworkRequest request(queryUrl);
  request.setAttribute(RequestTypeAttribute, NetworkManager::PollStatus);
  request.setAttribute(TaskIdAttribute, taskId);

  m_networkManager->get(request);
}

void NetworkManager::onNetworkReplyFinished(QNetworkReply *reply) {
  // --- 1. 检查网络错误 ---
  if (reply->error() != QNetworkReply::NoError) {
    QString errorMsg = QString("网络错误 (%1): %2")
                           .arg(reply->error())
                           .arg(reply->errorString());
    qDebug() << errorMsg;

    RequestType type =
        (RequestType)reply->request().attribute(RequestTypeAttribute).toInt();
    if (type == NetworkManager::PollStatus) {
      QString taskId = reply->request().attribute(TaskIdAttribute).toString();
      emit taskRequestFailed(taskId, errorMsg);
    } else {
      emit networkError(errorMsg);
    }

    reply->deleteLater();
    return;
  }

  QByteArray responseData = reply->readAll();
  RequestType type =
      (RequestType)reply->request().attribute(RequestTypeAttribute).toInt();

  // A. 处理创建项目 (Project) 的回复 (返回 Task IDs)
  if (type == NetworkManager::CreateProjectDirect) {
    QJsonDocument jsonDoc = QJsonDocument::fromJson(responseData);
    QJsonObject jsonObj = jsonDoc.object();

    QString projectId = jsonObj["project_id"].toString();
    QString textTaskId = jsonObj["text_task_id"].toString();
    QJsonArray shotTaskIdsJson = jsonObj["shot_task_ids"].toArray();

    QVariantList shotTaskIdsList;
    for (const QJsonValue &value : shotTaskIdsJson) {
      shotTaskIdsList.append(value.toString());
    }

    if (textTaskId.isEmpty() || shotTaskIdsList.isEmpty()) {
      qDebug() << "API 返回中缺少 Task ID 信息。";
      emit networkError("项目创建成功，但缺少任务 ID 无法启动轮询。");
    } else {
      qDebug() << "项目和任务创建成功，Project ID:" << projectId
               << "，Text Task ID:" << textTaskId;
      // 发出信号，通知 ViewModel 启动文本任务轮询
      emit textTaskCreated(projectId, textTaskId, shotTaskIdsList);
    }
  }
  // B. 处理获取分镜列表 (GET /projects/:id/shots) 的回复
  else if (type == NetworkManager::GetShotList) {
    QString projectId = reply->request().rawHeader("X-Project-Id");

    QJsonDocument jsonDoc = QJsonDocument::fromJson(responseData);
    QJsonObject jsonObj = jsonDoc.object();
    QJsonArray shotsArray =
        jsonObj["shots"].toArray(); // 假设分镜列表在 "shots" 键下

    QVariantList shotsList;
    for (const QJsonValue &value : shotsArray) {
      // 将每个分镜对象转换为 QVariantMap，用于 ViewModel 处理
      shotsList.append(value.toObject().toVariantMap());
    }

    emit shotListReceived(projectId, shotsList);
  }
  // C. 处理任务创建/更新 (UpdateShot/GenerateVideo) 的回复
  else if (type == NetworkManager::UpdateShot ||
           type == NetworkManager::GenerateVideo) {
    QJsonDocument jsonDoc = QJsonDocument::fromJson(responseData);
    QJsonObject jsonObj = jsonDoc.object();
    QString taskId = jsonObj["task_id"].toString();

    if (taskId.isEmpty()) {
      emit networkError("API 返回中未找到 task_id。");
    } else {
      QString shotId =
          (type == NetworkManager::UpdateShot)
              ? reply->request().attribute(ShotIdAttribute).toString()
              : QString();
      emit taskCreated(taskId, shotId);
    }
  }
  // D. 任务状态查询 (PollStatus) 的回复
  else if (type == NetworkManager::PollStatus) {
    QString taskId = reply->request().attribute(TaskIdAttribute).toString();
    QJsonDocument jsonDoc = QJsonDocument::fromJson(responseData);
    QJsonObject rootObj = jsonDoc.object();

    // [修正] 服务器返回 {"task": {...}}，需要提取嵌套对象
    QJsonObject taskObj =
        rootObj.contains("task") ? rootObj["task"].toObject() : rootObj;

    QString status = taskObj["status"].toString();
    int progress = taskObj["progress"].toInt();

    qDebug() << "Task:" << taskId << " Status:" << status
             << " Progress:" << progress
             << " Message:" << taskObj["message"].toString();

    if (status == "finished") {
      // 任务完成，提取 result 字段
      QVariantMap resultMap = taskObj["result"].toObject().toVariantMap();
      const QString shotId = taskObj["shotId"].toString();
      if (!shotId.isEmpty()) {
        resultMap["shot_id"] = shotId;
      }
      emit taskResultReceived(taskId, resultMap);
    } else {
      // 任务进行中
      emit taskStatusReceived(taskId, progress, status,
                              taskObj["message"].toString());
    }
  }

  reply->deleteLater();
}
