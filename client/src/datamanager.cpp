#include "datamanager.h"
#include <QDebug>

#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStandardPaths>

DataManager::DataManager(QObject *parent) : QObject(parent) {}

QString DataManager::getStoragePath(const QString &fileName) {
  // 使用系统标准的应用程序数据目录 (例如: ~/Library/Application
  // Support/StoryToVideoGenerator/data/)
  QString dirPath =
      QStandardPaths::writableLocation(QStandardPaths::AppDataLocation) +
      "/data/";

  QDir dir(dirPath);
  if (!dir.exists())
    dir.mkpath(dirPath);

  return dirPath + fileName;
}

bool DataManager::saveData(const QVariantMap &storyData,
                           const QString &fileName) {
  QString path = getStoragePath(fileName);

  QJsonObject jsonObj = QJsonObject::fromVariantMap(storyData);
  QJsonDocument doc(jsonObj);

  QFile file(path);
  if (!file.open(QIODevice::WriteOnly))
    return false;

  file.write(doc.toJson(QJsonDocument::Indented));
  file.close();

  qDebug() << "保存成功:" << path;
  emit fileSaved(path);
  return true;
}

QVariantMap DataManager::loadData(const QString &fileName) {
  QString path = getStoragePath(fileName);

  QFile file(path);
  if (!file.open(QIODevice::ReadOnly)) {
    qDebug() << "加载失败，文件不存在:" << path;
    return QVariantMap();
  }

  QByteArray data = file.readAll();
  file.close();

  QJsonDocument doc = QJsonDocument::fromJson(data);
  QVariantMap map = doc.object().toVariantMap();

  qDebug() << "加载成功:" << path;
  emit fileLoaded(path);

  return map;
}

QVariantMap DataManager::loadProjectFromPath(const QString &folderPath) {
  // 处理文件协议前缀
  QString cleanPath = folderPath;
  if (cleanPath.startsWith("file://")) {
#ifdef Q_OS_WIN
    cleanPath = cleanPath.mid(8); // file:///C:/...
#else
    cleanPath = cleanPath.mid(7); // file:///Users/...
#endif
  }

  QDir dir(cleanPath);
  QString jsonPath = dir.filePath("project.json");

  QFile file(jsonPath);
  if (!file.open(QIODevice::ReadOnly)) {
    qDebug() << "loadProjectFromPath 失败，文件不存在:" << jsonPath;
    return QVariantMap();
  }

  QByteArray data = file.readAll();
  file.close();

  QJsonDocument doc = QJsonDocument::fromJson(data);
  if (doc.isNull()) {
    qDebug() << "loadProjectFromPath 失败，JSON解析错误:" << jsonPath;
    return QVariantMap();
  }

  QVariantMap map = doc.object().toVariantMap();
  qDebug() << "loadProjectFromPath 成功:" << jsonPath
           << "包含keys:" << map.keys();
  return map;
}

QString DataManager::getProjectTitle(const QString &folderPath) {
  QVariantMap data = loadProjectFromPath(folderPath);
  if (data.isEmpty()) {
    // 返回文件夹名作为备用
    QString cleanPath = folderPath;
    if (cleanPath.startsWith("file://")) {
      cleanPath = cleanPath.mid(7);
    }
    QDir dir(cleanPath);
    return dir.dirName();
  }
  QString title = data.value("title").toString();
  return title.isEmpty() ? data.value("id").toString() : title;
}

bool DataManager::clearData(const QString &fileName) {
  QString path = getStoragePath(fileName);

  if (QFile::exists(path)) {
    QFile::remove(path);
    qDebug() << "删除成功:" << path;
    emit fileCleared(path);
    return true;
  }

  qDebug() << "删除失败，文件不存在:" << path;
  return false;
}

bool DataManager::saveProjectToPath(const QString &folderPath,
                                    const QVariantMap &projectData) {
  QString cleanPath = folderPath;
  if (cleanPath.startsWith("file://")) {
    cleanPath = cleanPath.mid(7);
#ifdef Q_OS_WIN
    if (cleanPath.startsWith("/"))
      cleanPath = cleanPath.mid(1);
#endif
  }

  QDir dir(cleanPath);
  if (!dir.exists()) {
    if (!dir.mkpath(".")) {
      qDebug() << "DataManager: Failed to create directory:" << cleanPath;
      return false;
    }
  }

  QString filePath = dir.filePath("project.json");
  QFile file(filePath);
  if (!file.open(QIODevice::WriteOnly)) {
    qDebug() << "DataManager: Failed to open file for writing:" << filePath;
    return false;
  }

  QJsonObject jsonObj = QJsonObject::fromVariantMap(projectData);
  QJsonDocument doc(jsonObj);
  file.write(doc.toJson());
  file.close();
  qDebug() << "DataManager: Project saved to:" << filePath;
  return true;
}
