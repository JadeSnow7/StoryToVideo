#include "TestHarness.h"
#include <QDebug>
#include <QTimer>
#include <QCoreApplication>
#include <QDateTime>
TestHarness::TestHarness(ViewModel *vm, QObject *parent)
    : QObject(parent), m_viewModel(vm)
{
    // 连接 ViewModel 的所有信号到 TestHarness 的槽函数
    connect(m_viewModel, &ViewModel::jobSubmitted,
            this, &TestHarness::handleJobSubmitted);
    connect(m_viewModel, &ViewModel::jobStatusUpdated,
            this, &TestHarness::handleJobStatusUpdated);
    connect(m_viewModel, &ViewModel::generationFailed,
            this, &TestHarness::handleGenerationFailed);
}

void TestHarness::startStoryboardTest()
{
    m_testStoryId = QString("TEST-%1").arg(QDateTime::currentSecsSinceEpoch());
    QString storyText = "一个在雨中奔跑的侦探。请生成五个分镜。";
    QString style = "movie";

    qDebug() << "--- 提交故事生成任务 ---";

    // 模拟 QML 调用 ViewModel
    m_viewModel->generateStoryboard(m_testStoryId, storyText, style);
}

void TestHarness::handleJobSubmitted(const QString &jobId, const QString &jobType)
{
    if (jobType == "llm") {
        m_testJobId = jobId;
        qDebug() << QString(">>> 任务提交成功！ Job ID: %1. 开始等待轮询结果...").arg(jobId);

        // 由于 ViewModel 内部已经启动了定时器，我们只需要等待 jobStatusUpdated 信号即可。
    }
}

void TestHarness::handleJobStatusUpdated(const QVariant &jobData)
{
    QVariantMap dataMap = jobData.toMap();
    QString jobId = dataMap["job_id"].toString();
    QString status = dataMap["status"].toString();
    int progress = dataMap["progress"].toInt();

    if (jobId == m_testJobId) {
        qDebug() << QString(">>> Job ID: %1 | 状态: %2 | 进度: %3%").arg(jobId, status).arg(progress);

        if (status == "succeeded") {
            // 任务完成，解析结果
            QVariantMap result = dataMap["result"].toMap();
            QVariantList shots = result["shots"].toList();

            qDebug() << "!!! LLM 故事生成任务成功 !!!";
            qDebug() << QString("总分镜数: %1").arg(shots.count());

            // 结束程序
            QCoreApplication::quit();
        } else if (status == "failed") {
            QVariantMap error = dataMap["error"].toMap();
            qDebug() << QString("!!! LLM 任务失败 !!! 错误: %1").arg(error["message"].toString());
            // 结束程序
            QCoreApplication::quit();
        }
    }
}

void TestHarness::handleGenerationFailed(const QString &errorMsg)
{
    qDebug() << QString("!!! 网络/API 致命错误 !!! 错误信息: %1").arg(errorMsg);
    // 结束程序
    QCoreApplication::quit();
}
