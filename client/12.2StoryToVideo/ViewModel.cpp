#include "ViewModel.h"
#include "NetworkManager.h"
#include "datamanager.h" // [修正] 大小写匹配文件名
#include <QCoreApplication>
#include <QDateTime>
#include <QDebug>
#include <QDir>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStandardPaths> // [新增]
#include <QTimer>
#include <QUrl>
#include <QVariantList>
#include <QVariantMap>

// ==========================================================
// C++ 实现
// ==========================================================

ViewModel::ViewModel(QObject *parent) : QObject(parent) {
  m_networkManager = new NetworkManager(this);
  m_pollingTimer = new QTimer(this);

  // 连接 NetworkManager 的信号
  connect(m_networkManager, &NetworkManager::textTaskCreated, this,
          &ViewModel::handleTextTaskCreated);

  connect(m_networkManager, &NetworkManager::shotListReceived, this,
          &ViewModel::handleShotListReceived);

  connect(m_networkManager, &NetworkManager::taskCreated, this,
          &ViewModel::handleTaskCreated);
  connect(m_networkManager, &NetworkManager::taskStatusReceived, this,
          &ViewModel::handleTaskStatusReceived);
  connect(m_networkManager, &NetworkManager::taskResultReceived, this,
          &ViewModel::handleTaskResultReceived);
  connect(m_networkManager, &NetworkManager::taskRequestFailed, this,
          &ViewModel::handleTaskRequestFailed);

  // [重要] ViewModel 监听 networkError 并转发为 generationFailed
  connect(m_networkManager, &NetworkManager::networkError, this,
          &ViewModel::handleNetworkError);

  connect(m_pollingTimer, &QTimer::timeout, this, &ViewModel::pollCurrentTask);
  m_pollingTimer->setInterval(1000); // 每 1 秒轮询一次

  qDebug() << "ViewModel 实例化成功。";
}

void ViewModel::generateStoryboard(const QString &storyText,
                                   const QString &style,
                                   const QString &projectName) {
  qDebug()
      << ">>> C++ 收到请求：生成项目并启动文本任务，委托给 NetworkManager。";

  // [修改] 使用用户提供的项目名称，如果为空则自动生成
  QString title = projectName.trimmed().isEmpty()
                      ? "新故事项目 - " + QDateTime::currentDateTime().toString(
                                              "yyyyMMdd_hhmmss")
                      : projectName.trimmed();
  QString description = "由用户输入的文本创建的项目。";

  // 触发项目创建 (POST /v1/api/projects)，返回所有 Task IDs
  m_networkManager->createProjectDirect(title, storyText, style, description);
}

void ViewModel::startVideoCompilation(const QString &storyId) {
  qDebug() << ">>> C++ 收到请求：生成视频，委托给 NetworkManager for ID:"
           << storyId;

  m_networkManager->generateVideoRequest(storyId);
}

void ViewModel::generateShotImage(const QString &shotId, const QString &prompt,
                                  const QString &transition) {
  qDebug() << ">>> C++ 收到请求：生成单张图像 Shot:" << shotId
           << "Project:" << m_projectId;
  m_networkManager->updateShotRequest(m_projectId, shotId, prompt, transition);
}

void ViewModel::loadProject(const QString &folderPath) {
  qDebug() << ">>> C++ 加载项目:" << folderPath;
  DataManager dm;
  QVariantMap data = dm.loadProjectFromPath(folderPath);

  if (data.isEmpty()) {
    emit generationFailed("无法加载项目数据 (project.json 丢失或无效)");
    return;
  }

  emit storyboardGenerated(QVariant::fromValue(data));
}

// --- 任务调度与轮询管理 ---

// [修改] 阶段 1：处理文本任务创建成功 (DEBUG INJECTION HERE)
void ViewModel::handleTextTaskCreated(const QString &projectId,
                                      const QString &textTaskId,
                                      const QVariantList &shotTaskIds) {
  qDebug() << "ViewModel: 收到 Text Task ID:" << textTaskId
           << "，Shot Tasks Count:" << shotTaskIds.count();

  m_projectId = projectId;
  m_textTaskId = textTaskId;
  m_shotTaskIds = shotTaskIds;

  QVariantMap taskInfo;
  taskInfo["type"] = "text_task";
  taskInfo["id"] = projectId;

  m_activeTasks.insert(textTaskId, taskInfo);
  startPollingTimer();
}

// [修改] 阶段 1/2：处理分镜列表获取成功
void ViewModel::handleShotListReceived(const QString &projectId,
                                       const QVariantList &shots) {
  qDebug() << "ViewModel: 成功获取分镜列表，共" << shots.count() << "条。";

  // --- 构造完整 URL 并标准化数据结构 ---
  QVariantList processedShots;
  const QString API_BASE_URL = "http://119.45.124.222:8080";

  for (const QVariant &varShot : shots) {
    QVariantMap shotMap = varShot.toMap();

    // 服务端返回 camelCase: imagePath；兼容旧字段 image_path
    QString imagePath = shotMap.value("imagePath").toString();
    if (imagePath.isEmpty()) {
      imagePath = shotMap.value("image_path").toString();
    }

    if (!imagePath.isEmpty()) {
      // 若已是完整 URL，则直接使用；否则拼接 API 基址
      if (imagePath.startsWith("http", Qt::CaseInsensitive)) {
        shotMap["imageUrl"] = imagePath;
      } else {
        shotMap["imageUrl"] = API_BASE_URL + imagePath;
      }
    }

    // QML ListModel 期望的键名为 'shotId', 'shotOrder', 'shotTitle' 等
    // 由于 backend SQL 使用 'id', 'order', 'title'，我们在这里进行映射。
    shotMap["shotId"] = shotMap["id"];
    shotMap["shotOrder"] = shotMap["order"];
    shotMap["shotTitle"] = shotMap["title"];
    shotMap["shotDescription"] = shotMap["description"];
    shotMap["shotPrompt"] = shotMap["prompt"];

    processedShots.append(shotMap);
  }
  // ------------------------------------

  // 将分镜列表发射给 QML (StoryboardPage)
  QVariantMap storyMap;
  storyMap["id"] = projectId;

  // [修正] 使用第一个分镜的标题或项目 ID 作为故事标题
  QString storyTitle = "新故事项目";
  if (!processedShots.isEmpty()) {
    QVariantMap firstShot = processedShots.first().toMap();
    QString shotTitle = firstShot.value("title", "").toString();
    if (!shotTitle.isEmpty() && shotTitle != "...") {
      storyTitle = shotTitle;
    }
  }
  storyMap["title"] = storyTitle;
  storyMap["shots"] = processedShots; // 传递处理后的分镜列表

  emit storyboardGenerated(QVariant::fromValue(storyMap));

  // [新增] 持久化保存项目初始数据
  m_currentProjectData = storyMap;
  QString basePath =
      QStandardPaths::writableLocation(QStandardPaths::MoviesLocation);
  m_projectFolderPath = basePath + "/StoryToVideo/Project_" + projectId;

  DataManager dm;
  if (dm.saveProjectToPath(m_projectFolderPath, m_currentProjectData)) {
    qDebug() << "ViewModel: Project initial data saved to:"
             << m_projectFolderPath;
  }

  // [TODO] 启动所有 shot_task_ids 的轮询 (Stage 2) - 真实流程需要在此处启动
  // ...
}

void ViewModel::handleTaskResultReceived(const QString &taskId,
                                         const QVariantMap &resultData) {
  qDebug() << "-0000000000  -";
  bool isMissing = !m_activeTasks.contains(taskId);

  qDebug() << "DEBUG CHECK (Missing Task): Task ID" << taskId
           << "is in m_activeTasks:"
           << !isMissing; // 打印 true/false 的反向值 (即是否在列表中)
  if (isMissing) {
    qDebug() << "ERROR: Task ID" << taskId << "is not being tracked. Aborting.";
    return;
  }
  qDebug() << "-2222222  -";
  QVariantMap taskInfo = m_activeTasks.value(taskId);
  qDebug() << "DEBUG MAP CHECK: Successfully retrieved map. Task Type:"
           << taskInfo["type"].toString();
  QString type = taskInfo["type"].toString();
  QString projectId = taskInfo["id"].toString();

  qDebug() << "333333  -" << type;
  if (type == "text_task") {
    // [Stage 1 Done] 文本任务完成
    stopPollingTimer(taskId);
    m_networkManager->getShotListRequest(m_projectId); // 获取分镜列表

  } else if (type == "shot_task" || type == "shot") {
    // 分镜图片任务完成 (Stage 2 Done 或重生成)
    stopPollingTimer(taskId);

    // 假设这里只处理重生成任务，因为初始分镜由 GetShotListRequest 获取
    // 传递 shotId 和 resultData
    processImageResult(taskInfo["id"].toString(), resultData);

  } else if (type == "video") {
    qDebug() << "DEBUG CALL CHECK: Attempting to call processVideoResult for "
                "Project:"
             << projectId;
    processVideoResult(projectId, resultData);
    stopPollingTimer(taskId);
  }
}

// --- 辅助函数 (其他函数保持不变) ---

void ViewModel::handleTaskCreated(const QString &taskId,
                                  const QString &shotId) {
  qDebug() << "ViewModel: 收到通用任务 Task ID:" << taskId;

  // 此函数主要处理分镜重生成或视频生成任务
  QVariantMap taskInfo;

  if (shotId.isEmpty()) {
    taskInfo["type"] = "video";
    taskInfo["id"] = m_projectId; // 使用当前 Project ID
  } else {
    taskInfo["type"] = "shot";
    taskInfo["id"] = shotId;
  }

  m_activeTasks.insert(taskId, taskInfo);
  startPollingTimer();
}

void ViewModel::handleTaskStatusReceived(const QString &taskId, int progress,
                                         const QString &status,
                                         const QString &message) {
  if (!m_activeTasks.contains(taskId))
    return;

  QVariantMap taskInfo = m_activeTasks[taskId];
  QString type = taskInfo["type"].toString();
  QString identifier = taskInfo["id"].toString();

  if (type == "text_task" || type == "video") {
    emit compilationProgress(identifier, progress);
  }

  qDebug() << "Task:" << taskId << " Status:" << status
           << " Message:" << message;
}

void ViewModel::handleTaskRequestFailed(const QString &taskId,
                                        const QString &errorMsg) {
  if (m_activeTasks.contains(taskId)) {
    QVariantMap taskInfo = m_activeTasks[taskId];
    qDebug() << "任务轮询失败:" << taskId << errorMsg;
    emit generationFailed(QString("任务 %1 失败: %2")
                              .arg(taskInfo["id"].toString())
                              .arg(errorMsg));
    stopPollingTimer(taskId);
  }
}

void ViewModel::startPollingTimer() {
  if (!m_pollingTimer->isActive()) {
    m_pollingTimer->start();
    qDebug() << "轮询定时器已启动。";
  }
}

void ViewModel::stopPollingTimer(const QString &taskId) {
  m_activeTasks.remove(taskId);
  if (m_activeTasks.isEmpty() && m_pollingTimer->isActive()) {
    m_pollingTimer->stop();
    qDebug() << "所有任务完成，轮询定时器已停止。";
  }
}

void ViewModel::pollCurrentTask() {
  if (m_activeTasks.isEmpty()) {
    m_pollingTimer->stop();
    return;
  }
  QList<QString> taskIds = m_activeTasks.keys();
  for (const QString &taskId : taskIds) {
    m_networkManager->pollTaskStatus(taskId);
  }
}

void ViewModel::handleNetworkError(const QString &errorMsg) {
  qDebug() << "通用网络错误发生:" << errorMsg;
  emit generationFailed(QString("网络通信失败: %1").arg(errorMsg));
}

void ViewModel::processStoryboardResult(const QString &taskId,
                                        const QVariantMap &resultData) {
  qDebug() << "Note: processStoryboardResult 仅用于历史兼容或视频任务解析。";
}

void ViewModel::processImageResult(const QString &shotId,
                                   const QVariantMap &resultData) {
  // 用于分镜重生成任务完成后的处理

  // [修正] 优先尝试从新的 resource_url 结构中获取路径
  QString imagePath = resultData["resource_url"].toString();

  if (imagePath.isEmpty()) {
    // 兼容旧的或嵌套的结构
    QVariantMap taskVideo = resultData["task_video"].toMap();
    imagePath = taskVideo["path"].toString();
  }

  if (imagePath.isEmpty()) {
    emit generationFailed(
        QString("Shot %1: 图像生成 API 未返回路径。").arg(shotId));
    return;
  }

  QString qmlUrl = imagePath;
  if (!qmlUrl.startsWith("http", Qt::CaseInsensitive)) {
    qmlUrl = QString("http://119.45.124.222:8080%1").arg(imagePath);
  }
  qDebug() << "图像重生成成功，QML URL:" << qmlUrl;
  emit imageGenerationFinished(shotId, qmlUrl);

  // [新增] 更新本地数据并保存
  if (!m_currentProjectData.isEmpty()) {
    QVariantList shots = m_currentProjectData["shots"].toList();
    bool updated = false;
    for (int i = 0; i < shots.size(); ++i) {
      QVariantMap shot = shots[i].toMap();
      if (shot["id"].toString() == shotId) {
        shot["imagePath"] = qmlUrl;
        shots[i] = shot;
        updated = true;
        break;
      }
    }
    if (updated) {
      m_currentProjectData["shots"] = shots;
      DataManager dm;
      dm.saveProjectToPath(m_projectFolderPath, m_currentProjectData);
    }
  }
}

void ViewModel::processVideoResult(const QString &storyId,
                                   const QVariantMap &resultData) {
  // --- [CRITICAL DIAGNOSTIC LOG 1] ---
  qDebug() << "DEBUG PROCESS VIDEO: Function entered. StoryID:" << storyId;

  // 检查输入数据是否为空
  if (resultData.isEmpty()) {
    qDebug() << "ERROR PROCESS VIDEO: resultData 映射为空。";
    emit generationFailed(QString("视频合成失败：结果数据为空。"));
    return;
  }

  // 检查 1：优先尝试从新的 resource_url 结构中获取路径
  QString videoPath = resultData["resource_url"].toString();
  qDebug() << "DEBUG PROCESS VIDEO: [1] resource_url 键值:" << videoPath;

  if (videoPath.isEmpty()) {
    // 检查 2：兼容旧的或嵌套的 task_video 结构
    QVariantMap taskVideo = resultData["task_video"].toMap();
    videoPath = taskVideo["path"].toString();
    qDebug() << "DEBUG PROCESS VIDEO: [2] task_video/path 键值:" << videoPath;
  }

  if (videoPath.isEmpty()) {
    qDebug() << "视频生成失败，最终未找到视频路径。";
    emit generationFailed(QString("视频合成失败：未找到资源路径。"));
    return;
  }

  // 构造完整的 URL
  QString qmlUrl = videoPath;
  if (!qmlUrl.startsWith("http", Qt::CaseInsensitive)) {
    qmlUrl = QString("http://119.45.124.222:8080%1").arg(videoPath);
  }

  // 最终确认日志
  qDebug() << "视频资源 URL:" << qmlUrl;

  // [新增] 保存视频路径到项目文件
  if (!m_currentProjectData.isEmpty()) {
    m_currentProjectData["videoPath"] = qmlUrl;
    DataManager dm;
    dm.saveProjectToPath(m_projectFolderPath, m_currentProjectData);
    qDebug() << "ViewModel: Project video path saved.";
  }

  // 发射信号给 QML
  emit compilationProgress(storyId, 100);
  qDebug() << "C++ DEBUG: CompilationProgress signal EMITTED for ID:"
           << storyId;
}
