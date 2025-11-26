#include "NetworkManager.h"
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QDebug>

// 用户定义的属性 Key，用于在 QNetworkRequest 中传递 Shot ID 和请求类型
const QNetworkRequest::Attribute ShotIdAttribute =
    (QNetworkRequest::Attribute)(QNetworkRequest::UserMax + 1);
const QNetworkRequest::Attribute RequestTypeAttribute =
    (QNetworkRequest::Attribute)(QNetworkRequest::UserMax + 2);


NetworkManager::NetworkManager(QObject *parent) : QObject(parent)
{
    m_networkManager = new QNetworkAccessManager(this);

    connect(m_networkManager, &QNetworkAccessManager::finished,
            this, &NetworkManager::onNetworkReplyFinished);

    qDebug() << "NetworkManager 实例化成功。";
}


void NetworkManager::generateStoryboardRequest(const QString &storyText, const QString &style)
{
    qDebug() << "发送 Ollama API 请求...";

    QJsonObject requestJson;
    requestJson["model"] = "qwen2.5:0.5b";

    QString prompt = QString(
        "你是一个专业的故事板设计师。请根据故事和风格，生成一个包含5个分镜的详细描述。 "
        "要求以JSON格式返回，JSON必须只包含一个名为'shots'的数组，每个元素包含'title'和'prompt'字段。"
        "故事: %1; 风格: %2"
    ).arg(storyText, style);

    requestJson["prompt"] = prompt;
    requestJson["format"] = "json";

    QJsonDocument doc(requestJson);
    QByteArray postData = doc.toJson();

    QNetworkRequest request(OLLAMA_API_URL);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    request.setAttribute(RequestTypeAttribute, NetworkManager::OllamaRequest);

    m_networkManager->post(request, postData);
}

void NetworkManager::generateImageRequest(int shotId, const QString &prompt, const QString &style)
{
    qDebug() << "发送 Stable Diffusion 请求...";

    QJsonObject requestJson;

    requestJson["prompt"] = prompt + ", " + style + ", high quality, detailed";
    requestJson["negative_prompt"] = "watermark, text, signature, blurry, worst quality, deformed";
    requestJson["sampler_name"] = "Euler a";
    requestJson["steps"] = 4;
    requestJson["cfg_scale"] = 1.0;
    requestJson["width"] = 512;
    requestJson["height"] = 512;
    requestJson["n_iter"] = 1;

    QJsonDocument doc(requestJson);
    QByteArray postData = doc.toJson();

    QNetworkRequest request(SD_API_URL);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    request.setAttribute(RequestTypeAttribute, NetworkManager::SDRequest);
    request.setAttribute(ShotIdAttribute, shotId);

    m_networkManager->post(request, postData);
}

void NetworkManager::onNetworkReplyFinished(QNetworkReply *reply)
{
    // --- 1. 检查网络错误 ---
    if (reply->error() != QNetworkReply::NoError) {
        QString errorMsg = QString("网络错误 (%1): %2").arg(reply->error()).arg(reply->errorString());
        qDebug() << errorMsg;
        emit networkError(errorMsg); // 通知 ViewModel
        reply->deleteLater();
        return;
    }

    // --- 2. 区分请求类型并处理回复 ---
    QByteArray responseData = reply->readAll();
    RequestType type = (RequestType)reply->request().attribute(RequestTypeAttribute).toInt();

    if (type == NetworkManager::OllamaRequest)
    {
        // --- 处理 Ollama 故事生成回复 ---
        QString jsonResponse = QString::fromUtf8(responseData);
        qDebug() << "Ollama 原始回复已接收。";
        emit ollamaResponseReceived(jsonResponse);
    }
    else if (type == NetworkManager::SDRequest)
    {
        // --- 处理 Stable Diffusion 图像生成回复 ---
        int shotId = reply->request().attribute(ShotIdAttribute).toInt();

        QJsonDocument jsonDoc = QJsonDocument::fromJson(responseData);
        QJsonObject jsonObj = jsonDoc.object();

        QJsonArray images = jsonObj["images"].toArray();
        if (!images.isEmpty()) {
            QString base64Image = images.first().toString();
            qDebug() << "SD Base64 图像数据已接收，Shot ID:" << shotId;
            emit imageGenerationResponse(shotId, base64Image);
        } else {
            emit networkError(QString("图像生成API返回空数据，Shot ID: %1").arg(shotId));
        }
    }

    reply->deleteLater();
}
