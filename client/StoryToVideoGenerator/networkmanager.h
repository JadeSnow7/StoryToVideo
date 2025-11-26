#ifndef NETWORKMANAGER_H
#define NETWORKMANAGER_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QString>
#include <QUrl>

class NetworkManager : public QObject
{
    Q_OBJECT
public:
    explicit NetworkManager(QObject *parent = nullptr);

    // 1. Ollama：发送故事生成请求
    void generateStoryboardRequest(const QString &storyText, const QString &style);

    // 2. Stable Diffusion：发送图像生成请求
    void generateImageRequest(int shotId, const QString &prompt, const QString &style);


signals:
    // 1. Ollama (故事生成) 回复信号：包含 Ollama 返回的原始 JSON 字符串
    void ollamaResponseReceived(const QString &jsonResponse);

    // 2. Stable Diffusion (图像生成) 回复信号：返回 Base64 图像数据
    void imageGenerationResponse(int shotId, const QString &base64Image);

    // 通用错误信号 (用于连接 ViewModel::handleNetworkError)
    void networkError(const QString &errorMsg);

private slots:
    // 处理所有请求的回复
    void onNetworkReplyFinished(QNetworkReply *reply);

private:
    QNetworkAccessManager *m_networkManager;

    // --- API 地址常量 ---
    const QUrl OLLAMA_API_URL = QUrl("http://localhost:11434/api/generate");
    const QUrl SD_API_URL = QUrl("http://localhost:8080/sdapi/v1/txt2img");

    // 用于区分回复是来自 Ollama 还是 SD
    enum RequestType { OllamaRequest = 1, SDRequest = 2 };
};

#endif // NETWORKMANAGER_H
