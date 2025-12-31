#ifndef VIDEOEXPORTER_H
#define VIDEOEXPORTER_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QFile>

class VideoExporter : public QObject
{
    Q_OBJECT
public:
    explicit VideoExporter(QObject *parent = nullptr);

    // QML 调用的方法
    Q_INVOKABLE void exportVideo(const QString &videoUrl, const QString &saveFilePath);

signals:
    void exportFinished(const QString &msg);
    void exportFailed(const QString &error);

private:
    QNetworkAccessManager *m_manager;
};

#endif // VIDEOEXPORTER_H
