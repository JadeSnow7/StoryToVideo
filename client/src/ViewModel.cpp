#include "ViewModel.h"
#include "ApiConfig.h"
#include "NetworkManager.h"
#include "datamanager.h" // [修正] 大小写匹配文件名
#include <QCoreApplication>
#include <QDateTime>
#include <QDebug>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
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
  m_apiBaseUrl = ApiConfig::apiBaseUrl();
  m_assetDownloader = new QNetworkAccessManager(this);

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

QString ViewModel::apiBaseUrl() const { return m_apiBaseUrl; }

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
  // [并发安全]
  // 强制清理该项目下所有已存在的旧任务（防止僵尸任务导致的进度条跳动）
  QList<QString> keysToRemove;
  QHashIterator<QString, QVariantMap> i(m_activeTasks);
  while (i.hasNext()) {
    i.next();
    const QString currentId = i.value()["id"].toString();
    const QString currentType = i.value()["type"].toString();

    // 如果发现同一个 Project ID 的任务 (无论是 video 还是
    // text_task)，都视为冲突/旧任务清理掉
    if (currentId == storyId &&
        (currentType == "video" || currentType == "text_task")) {
      keysToRemove.append(i.key());
      qDebug() << "WARN: Cleaning up zombie/duplicate task for Project ID:"
               << storyId << "Task ID:" << i.key();
    }
  }

  for (const QString &key : keysToRemove) {
    m_activeTasks.remove(key);
  }

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

bool ViewModel::isGenerationInProgress(const QString &storyId) {
  if (storyId.isEmpty()) {
    return false;
  }
  QHashIterator<QString, QVariantMap> it(m_activeTasks);
  while (it.hasNext()) {
    it.next();
    const QVariantMap taskInfo = it.value();
    if (taskInfo.value("type").toString() == "video" &&
        taskInfo.value("id").toString() == storyId) {
      return true;
    }
  }
  return false;
}

QString ViewModel::getProjectVideoLocalPath(const QString &storyId) {
  if (storyId.isEmpty()) {
    return QString();
  }
  const QString basePath =
      QStandardPaths::writableLocation(QStandardPaths::MoviesLocation);
  if (basePath.isEmpty()) {
    return QString();
  }
  const QString projectFolder =
      basePath + "/StoryToVideo/Project_" + storyId;

  DataManager dm;
  const QVariantMap data = dm.loadProjectFromPath(projectFolder);
  QString localPath = data.value("videoLocalPath").toString();
  if (localPath.isEmpty()) {
    localPath = QDir(projectFolder).filePath("video.mp4");
  }
  if (!localPath.isEmpty() && QFile::exists(localPath)) {
    return localPath;
  }
  return QString();
}

void ViewModel::refreshShots(const QString &projectId) {
  const QString targetId = projectId.isEmpty() ? m_projectId : projectId;
  if (targetId.isEmpty()) {
    emit generationFailed("无法刷新分镜：项目 ID 为空。");
    return;
  }
  qDebug() << ">>> C++ 收到请求：刷新分镜列表 Project:" << targetId;
  m_refreshProjectId = targetId;
  m_forceShotListUpdate = true;
  m_networkManager->getShotListRequest(targetId);
}

void ViewModel::loadProject(const QString &folderPath) {
  qDebug() << ">>> C++ 加载项目:" << folderPath;
  DataManager dm;
  QVariantMap data = dm.loadProjectFromPath(folderPath);

  if (data.isEmpty()) {
    emit generationFailed("无法加载项目数据 (project.json 丢失或无效)");
    return;
  }

  QString cleanPath = folderPath;
  if (cleanPath.startsWith("file://")) {
#ifdef Q_OS_WIN
    cleanPath = cleanPath.mid(8);
#else
    cleanPath = cleanPath.mid(7);
#endif
  }
  m_projectFolderPath = cleanPath;
  m_currentProjectData = data;
  m_projectId = data.value("id").toString();

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
  m_autoShotPollingStarted = false;

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
  const QString apiBaseUrl = m_apiBaseUrl;

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
        shotMap["imageUrl"] = apiBaseUrl + imagePath;
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
  const QString existingVideoPath =
      m_currentProjectData.value("videoPath").toString();
  const QString existingVideoLocalPath =
      m_currentProjectData.value("videoLocalPath").toString();

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
  if (!existingVideoPath.isEmpty()) {
    storyMap["videoPath"] = existingVideoPath;
  }
  if (!existingVideoLocalPath.isEmpty()) {
    storyMap["videoLocalPath"] = existingVideoLocalPath;
  }

  const QString currentId = m_currentProjectData.value("id").toString();
  const bool isInitialLoad = m_currentProjectData.isEmpty() ||
                             currentId.isEmpty() || currentId != projectId;
  const bool forceUpdate =
      m_forceShotListUpdate &&
      (m_refreshProjectId.isEmpty() || m_refreshProjectId == projectId);

  if (forceUpdate) {
    emit shotListUpdated(QVariant::fromValue(storyMap));
    m_forceShotListUpdate = false;
    m_refreshProjectId.clear();
  } else if (isInitialLoad) {
    emit storyboardGenerated(QVariant::fromValue(storyMap));
  } else {
    emit shotListUpdated(QVariant::fromValue(storyMap));
  }

  // [新增] 持久化保存项目数据
  m_currentProjectData = storyMap;
  QString basePath =
      QStandardPaths::writableLocation(QStandardPaths::MoviesLocation);
  m_projectFolderPath = basePath + "/StoryToVideo/Project_" + projectId;

  DataManager dm;
  if (dm.saveProjectToPath(m_projectFolderPath, m_currentProjectData)) {
    qDebug() << "ViewModel: Project initial data saved to:"
             << m_projectFolderPath;
  }

  // [新增] 自动启动分镜生图任务轮询 (Stage 2)
  if (!m_autoShotPollingStarted && !m_shotTaskIds.isEmpty()) {
    const int taskCount = m_shotTaskIds.size();
    for (int i = 0; i < taskCount; ++i) {
      const QString taskId = m_shotTaskIds[i].toString();
      if (taskId.isEmpty() || m_activeTasks.contains(taskId)) {
        continue;
      }
      QVariantMap taskInfo;
      taskInfo["type"] = "shot_task";
      if (i < processedShots.size()) {
        const QVariantMap shot = processedShots[i].toMap();
        taskInfo["id"] = shot.value("shotId").toString();
      } else {
        taskInfo["id"] = QString();
      }
      m_activeTasks.insert(taskId, taskInfo);
    }
    if (!m_activeTasks.isEmpty()) {
      startPollingTimer();
    }
    m_autoShotPollingStarted = true;
  }
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

  } else if (type == "shot_task") {
    // 初始分镜生图任务完成后，刷新分镜列表获取最新 imagePath/status
    stopPollingTimer(taskId);
    m_networkManager->getShotListRequest(m_projectId);

  } else if (type == "shot") {
    // 分镜图片任务完成 (Stage 2 Done 或重生成)
    stopPollingTimer(taskId);

    // 假设这里只处理重生成任务，因为初始分镜由 GetShotListRequest 获取
    // 传递 shotId 和 resultData
    QString shotId = taskInfo["id"].toString();
    if (shotId.isEmpty()) {
      shotId = resultData.value("shot_id").toString();
    }
    if (shotId.isEmpty()) {
      shotId = resultData.value("shotId").toString();
    }
    if (!shotId.isEmpty()) {
      taskInfo["id"] = shotId;
      m_activeTasks.insert(taskId, taskInfo);
      processImageResult(shotId, resultData);
    } else {
      qDebug()
          << "Shot task finished but shotId missing; refreshing shot list.";
      m_networkManager->getShotListRequest(m_projectId);
    }

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
    qDebug() << "任务轮询请求失败 (将重试):" << taskId << errorMsg;
    // [修正] 网络波动不应直接停止轮询，仅记录日志并继续尝试
    // 如果是 404 等严重错误，应当由 NetworkManager
    // 判断或在此处细分，目前暂时保持重试策略 emit generationFailed(...) //
    // 可选：暂时不弹窗打扰用户，除非连续失败多次 stopPollingTimer(taskId); //
    // [已移除] 保持轮询
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

  const QString rawPath = imagePath;
  QString qmlUrl = rawPath;
  if (!qmlUrl.startsWith("http", Qt::CaseInsensitive)) {
    qmlUrl = m_apiBaseUrl + rawPath;
  }
  const QString sep = qmlUrl.contains('?') ? "&" : "?";
  qmlUrl += QString("%1v=%2").arg(
      sep, QString::number(QDateTime::currentMSecsSinceEpoch()));
  qDebug() << "图像重生成成功，QML URL:" << qmlUrl;
  emit imageGenerationFinished(shotId, qmlUrl);
  QTimer::singleShot(600, this, [this]() {
    if (!m_projectId.isEmpty()) {
      m_networkManager->getShotListRequest(m_projectId);
    }
  });

  // [新增] 更新本地数据并保存
  if (!m_currentProjectData.isEmpty()) {
    QVariantList shots = m_currentProjectData["shots"].toList();
    bool updated = false;
    for (int i = 0; i < shots.size(); ++i) {
      QVariantMap shot = shots[i].toMap();
      if (shot["id"].toString() == shotId ||
          shot["shotId"].toString() == shotId) {
        shot["imagePath"] = rawPath;
        shot["imageUrl"] = qmlUrl;
        shots[i] = shot;
        updated = true;
        break;
      }
    }
    if (updated) {
      m_currentProjectData["shots"] = shots;
      DataManager dm;
      dm.saveProjectToPath(m_projectFolderPath, m_currentProjectData);
      emit shotListUpdated(QVariant::fromValue(m_currentProjectData));
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
    qmlUrl = m_apiBaseUrl + videoPath;
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

  autoSaveVideoToProject(qmlUrl);

  // 发射信号给 QML
  emit compilationProgress(storyId, 100);
  emit videoGenerationFinished(storyId, qmlUrl);
  qDebug() << "C++ DEBUG: CompilationProgress signal EMITTED for ID:"
           << storyId;
}

void ViewModel::autoSaveVideoToProject(const QString &videoUrl) {
  if (videoUrl.isEmpty()) {
    return;
  }
  if (m_projectFolderPath.isEmpty()) {
    qDebug() << "Auto-save skipped: project folder path is empty.";
    return;
  }

  QDir dir(m_projectFolderPath);
  if (!dir.exists() && !dir.mkpath(".")) {
    qDebug() << "Auto-save failed: cannot create project folder:"
             << m_projectFolderPath;
    return;
  }

  const QString localPath = dir.filePath("video.mp4");
  QNetworkRequest request((QUrl(videoUrl)));
  QNetworkReply *reply = m_assetDownloader->get(request);
  QFile *file = new QFile(localPath, reply);
  if (!file->open(QIODevice::WriteOnly)) {
    qDebug() << "Auto-save failed: cannot write file:" << localPath;
    reply->abort();
    file->deleteLater();
    reply->deleteLater();
    return;
  }

  connect(reply, &QIODevice::readyRead, this,
          [reply, file]() { file->write(reply->readAll()); });

  connect(reply, &QNetworkReply::finished, this,
          [this, reply, file, localPath]() {
            if (reply->error() != QNetworkReply::NoError) {
              qDebug() << "Auto-save failed:" << reply->errorString();
              file->close();
              file->remove();
              file->deleteLater();
              reply->deleteLater();
              return;
            }

            file->flush();
            file->close();
            file->deleteLater();
            reply->deleteLater();

            if (!m_currentProjectData.isEmpty()) {
              m_currentProjectData["videoLocalPath"] = localPath;
              DataManager dm;
              dm.saveProjectToPath(m_projectFolderPath, m_currentProjectData);
            }
            qDebug() << "Auto-save complete:" << localPath;
          });
}
