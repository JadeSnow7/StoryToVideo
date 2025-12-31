#include "VideoExporter.h"
#include <QDebug>

VideoExporter::VideoExporter(QObject *parent)
    : QObject(parent)
{
    m_manager = new QNetworkAccessManager(this);
}

void VideoExporter::exportVideo(const QString &videoUrl, const QString &saveFilePath)
{
    qDebug() << "开始下载视频: " << videoUrl;

    // Qt5.8 需要明确创建 request 对象，不能用临时变量
    QUrl url(videoUrl);
    QNetworkRequest request(url);

    QNetworkReply *reply = m_manager->get(request);

    connect(reply, &QNetworkReply::finished, [this, reply, saveFilePath]() {
        if (reply->error() != QNetworkReply::NoError) {
            emit exportFailed("下载失败: " + reply->errorString());
            reply->deleteLater();
            return;
        }

        QFile file(saveFilePath);
        if (!file.open(QIODevice::WriteOnly)) {
            emit exportFailed("无法写入文件: " + saveFilePath);
            reply->deleteLater();
            return;
        }

        file.write(reply->readAll());
        file.close();

        emit exportFinished("视频导出成功！");
        reply->deleteLater();
    });
}
