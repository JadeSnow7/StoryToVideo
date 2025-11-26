#include "ViewModel.h"
#include "NetworkManager.h"
#include <QDebug>
#include <QDateTime>
#include <QTimer>
#include <QVariantMap>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QBuffer>
#include <QImage>
#include <QDir>
#include <QCoreApplication>
#include <QUrl>
#include <QRegularExpression>

// --- 私有辅助函数：解析 Ollama 返回的 JSON 字符串 (使用 static 解决链接错误) ---
static QJsonDocument extractCoreJson(const QString &ollamaRawResponse) {

    // 用于存储所有提取到的 'response' 片段
    QString fullResponseText;

    // 1. 将原始拼接字符串按换行符分割成单独的 JSON 块
    QStringList lines = ollamaRawResponse.split('\n', QString::SkipEmptyParts);

    for (const QString &line : lines) {
        if (line.isEmpty()) continue;

        QJsonDocument doc = QJsonDocument::fromJson(line.toUtf8());

        if (doc.isObject()) {
            QJsonObject obj = doc.object();

            // 2. 提取 'response' 字段
            if (obj.contains("response")) {
                fullResponseText += obj["response"].toString();
            }
        }
    }

    // 3. 清理和最终解析

    // Ollama/Qwen 返回的 JSON 字符串中可能包含不必要的转义符 '\"' 和换行符 '\\n'
    // 我们必须移除 JSON 字符串内部的转义符，以便 QJsonDocument 可以解析

    // 移除 JSON 字符串内部的字面量换行符 (\n)
    fullResponseText.replace(QRegularExpression("\\\\n"), "");

    // 移除 JSON 字符串内部的转义双引号 (\\")，但这不是总是必要的，取决于 LLM 的输出。
    // 暂时不移除，先尝试解析。

    // 4. 最终解析这个合并后的完整 JSON 结构
    QJsonDocument coreDoc = QJsonDocument::fromJson(fullResponseText.toUtf8());

    if (coreDoc.isNull()) {
        qDebug() << "解析失败，最终合并字符串格式错误：";
        qDebug() << fullResponseText;
    } else {
        qDebug() << "JSON 合并成功，正在返回核心文档。";
    }

    return coreDoc;
}


// ==========================================================
// C++ 实现
// ==========================================================

ViewModel::ViewModel(QObject *parent) : QObject(parent)
{
    m_networkManager = new NetworkManager(this);

    // 连接网络管理器的信号到 ViewModel 的槽函数 (确保信号名称匹配)
    connect(m_networkManager, &NetworkManager::ollamaResponseReceived,
            this, &ViewModel::handleOllamaResponse);
    connect(m_networkManager, &NetworkManager::imageGenerationResponse,
            this, &ViewModel::handleImageResponse);
    connect(m_networkManager, &NetworkManager::networkError,
            this, &ViewModel::handleNetworkError);

    qDebug() << "ViewModel 实例化成功，等待网络请求。";
}


void ViewModel::generateStoryboard(const QString &storyText, const QString &style)
{
    qDebug() << ">>> C++ 收到请求：生成故事，委托给 NetworkManager。";
    m_networkManager->generateStoryboardRequest(storyText, style);
}

void ViewModel::startVideoCompilation(const QString &storyId)
{
    qDebug() << ">>> C++ 收到请求：启动视频合成 for ID:" << storyId;

    // 模拟进度更新
    QTimer::singleShot(1000, [this, storyId]() { emit compilationProgress(storyId, 25); });
    QTimer::singleShot(2000, [this, storyId]() { emit compilationProgress(storyId, 75); });
    QTimer::singleShot(3000, [this, storyId]() { emit compilationProgress(storyId, 100); });
}

void ViewModel::generateShotImage(int shotId, const QString &prompt, const QString &transition)
{
    qDebug() << ">>> C++ 收到请求：生成单张图像 Shot:" << shotId;
    m_networkManager->generateImageRequest(shotId, prompt, transition);
}


void ViewModel::handleOllamaResponse(const QString &ollamaRawResponse)
{
    qDebug() << "ViewModel: 收到 Ollama 原始回复，尝试解析...";
    qDebug() << "--- Ollama Raw Data Start ---";
    qDebug() << ollamaRawResponse; // 临时打印原始数据
    qDebug() << "--- Ollama Raw Data End ---";

    QJsonDocument doc = extractCoreJson(ollamaRawResponse);

    if (doc.isNull() || !doc.isObject() || !doc.object().contains("shots")) {
        emit generationFailed("LLM 返回的 JSON 格式不正确，无法解析分镜。");
        return;
    }

    QJsonArray shotsArray = doc.object()["shots"].toArray();

    // --- 构造 QML 所需数据 ---
    QString newStoryId = QString("STORY-%1").arg(QDateTime::currentSecsSinceEpoch());

    QVariantMap storyMap;
    storyMap["id"] = newStoryId;
    storyMap["title"] = "LLM 生成的故事";
    storyMap["shots"] = QVariant::fromValue(shotsArray.toVariantList());

    qDebug() << "LLM 解析成功，分镜数:" << shotsArray.count();

    emit storyboardGenerated(QVariant::fromValue(storyMap));
}

void ViewModel::handleImageResponse(int shotId, const QString &base64Image)
{
    qDebug() << "ViewModel: 收到 Base64 图像数据，Shot ID:" << shotId;

    // --- 1. Base64 解码 ---
    QByteArray imageBytes = QByteArray::fromBase64(base64Image.toUtf8());

    QImage image;
    if (!imageBytes.isEmpty() && !image.loadFromData(imageBytes)) {
        emit generationFailed(QString("Shot %1: 无法解码 Base64 图像数据。").arg(shotId));
        return;
    }

    if (image.isNull()) {
        emit generationFailed(QString("Shot %1: 解码后的图像为空或无效。").arg(shotId));
        return;
    }

    // --- 2. 保存到本地文件 ---
    QDir dir("./assets/shots");
    if (!dir.exists()) {
        dir.mkpath(".");
    }
    QString fileName = QString("assets/shots/shot_%1.jpg").arg(shotId);

    QString fullPath = QCoreApplication::applicationDirPath() + "/" + fileName;

    if (image.save(fullPath, "JPG")) {
        qDebug() << "图像成功保存到:" << fullPath;

        // --- 3. 通知 QML 更新 ---
        QString qmlUrl = QUrl::fromLocalFile(fullPath).toString();

        emit imageGenerationFinished(shotId, qmlUrl);
    } else {
        emit generationFailed(QString("Shot %1: 无法保存图像到本地文件。").arg(shotId));
    }
}

void ViewModel::handleNetworkError(const QString &errorMsg)
{
    // 将网络层的错误转发给 QML
    qDebug() << "通用网络错误发生:" << errorMsg;
    emit generationFailed(QString("网络通信失败: %1").arg(errorMsg));
}
