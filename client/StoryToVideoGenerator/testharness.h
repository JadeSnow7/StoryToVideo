#ifndef TESTHARNESS_H
#define TESTHARNESS_H

#include <QObject>
#include <QString>
#include "ViewModel.h"

class TestHarness : public QObject
{
    Q_OBJECT
public:
    explicit TestHarness(ViewModel *vm, QObject *parent = nullptr);

    void startStoryboardTest();

private slots:
    // 接收 ViewModel 信号的槽函数
    void handleJobSubmitted(const QString &jobId, const QString &jobType);
    void handleJobStatusUpdated(const QVariant &jobData);
    void handleGenerationFailed(const QString &errorMsg);

private:
    ViewModel *m_viewModel;
    QString m_testJobId;
    QString m_testStoryId;
};

#endif // TESTHARNESS_H
