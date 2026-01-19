#ifndef DATAMANAGER_H
#define DATAMANAGER_H

#include <QObject>
#include <QVariantMap>

class DataManager : public QObject {
  Q_OBJECT
public:
  explicit DataManager(QObject *parent = nullptr);

  Q_INVOKABLE bool saveData(const QVariantMap &storyData,
                            const QString &fileName);
  Q_INVOKABLE QVariantMap loadData(const QString &fileName);
  Q_INVOKABLE QVariantMap loadProjectFromPath(const QString &folderPath);
  Q_INVOKABLE QString
  getProjectTitle(const QString &folderPath); // [新增] 获取项目标题
  Q_INVOKABLE bool saveProjectToPath(
      const QString &folderPath,
      const QVariantMap
          &projectData); // [新增] 保存项目 // [新增] 从指定物理路径加载
  Q_INVOKABLE bool clearData(const QString &fileName);

signals:
  void fileSaved(const QString &filePath);
  void fileLoaded(const QString &filePath);
  void fileCleared(const QString &filePath);

private:
  QString getStoragePath(const QString &fileName);
};

#endif // DATAMANAGER_H
