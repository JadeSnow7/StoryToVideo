#ifndef VIEWMODEL_H
#define VIEWMODEL_H

#include <QHash>
#include <QObject>
#include <QString>
#include <QTimer>
#include <QVariant>
#include <QVariantList> // [新增]
#include <QVariantMap>

class NetworkManager;
class QNetworkAccessManager;

class ViewModel : public QObject {
  Q_OBJECT

public:
  explicit ViewModel(QObject *parent = nullptr);

  Q_PROPERTY(QString apiBaseUrl READ apiBaseUrl CONSTANT)

  Q_INVOKABLE void generateStoryboard(const QString &storyText,
                                      const QString &style,
                                      const QString &projectName = "");
  Q_INVOKABLE void startVideoCompilation(const QString &storyId);
  Q_INVOKABLE void generateShotImage(const QString &shotId,
                                     const QString &prompt,
                                     const QString &transition);
  Q_INVOKABLE void refreshShots(const QString &projectId);
  Q_INVOKABLE void
  loadProject(const QString &folderPath); // [新增] 加载现有项目

  Q_INVOKABLE bool isGenerationInProgress(const QString &storyId);
  Q_INVOKABLE QString getProjectVideoLocalPath(const QString &storyId);

  QString apiBaseUrl() const;

signals:
  void storyboardGenerated(const QVariant &storyData);
  void shotListUpdated(const QVariant &storyData);
  void generationFailed(const QString &errorMsg);
  void imageGenerationFinished(const QString &shotId, const QString &imageUrl);
  void videoGenerationFinished(const QString &storyId, const QString &videoUrl);
  void compilationProgress(const QString &storyId, int percent);

private slots:
  // [新增] 处理文本任务创建成功，启动文本任务轮询
  void handleTextTaskCreated(const QString &projectId,
                             const QString &textTaskId,
                             const QVariantList &shotTaskIds);

  // [修改/通用] 任务状态管理槽函数
  void handleTaskCreated(const QString &taskId, const QString &shotId);
  void handleTaskStatusReceived(const QString &taskId, int progress,
                                const QString &status, const QString &message);
  void handleTaskResultReceived(const QString &taskId,
                                const QVariantMap &resultData);
  void handleTaskRequestFailed(const QString &taskId, const QString &errorMsg);

  // [新增] 处理分镜列表获取成功
  void handleShotListReceived(const QString &projectId,
                              const QVariantList &shots);

  // 定时器相关
  void startPollingTimer();
  void stopPollingTimer(const QString &taskId);
  void pollCurrentTask();

  void handleNetworkError(const QString &errorMsg);

private:
  NetworkManager *m_networkManager;
  QTimer *m_pollingTimer;

  // --- [新增] 状态存储 ---
  QString m_projectId;        // 当前项目的 ID
  QString m_textTaskId;       // 当前文本任务的 ID (用于轮询 Stage 1)
  QVariantList m_shotTaskIds; // 依赖于文本任务的 Shot Task IDs 列表
  bool m_autoShotPollingStarted = false;

  // 存储所有正在轮询的任务 ID -> 对应的 QML ID (用于 Stage 1, 2, 视频)
  QHash<QString, QVariantMap> m_activeTasks;

  // [新增] 用于持久化存储的项目数据
  QVariantMap m_currentProjectData;
  QString m_projectFolderPath;
  QString m_apiBaseUrl;
  QNetworkAccessManager *m_assetDownloader;
  QString m_refreshProjectId;
  bool m_forceShotListUpdate = false;

  // 私有辅助函数
  void processStoryboardResult(const QString &taskId,
                               const QVariantMap &resultData);
  void processImageResult(const QString &shotId, const QVariantMap &resultData);
  void processVideoResult(const QString &storyId,
                          const QVariantMap &resultData);
  void autoSaveVideoToProject(const QString &videoUrl);
};

#endif // VIEWMODEL_H
