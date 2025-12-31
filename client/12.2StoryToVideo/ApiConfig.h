#ifndef APICONFIG_H
#define APICONFIG_H

#include <QByteArray>
#include <QString>
#include <QtGlobal>

namespace ApiConfig {
inline QString apiBaseUrl() {
  QByteArray raw = qgetenv("STORYTOVIDEO_API_BASE_URL");
  QString base = raw.isEmpty() ? QStringLiteral("http://127.0.0.1:8080")
                               : QString::fromUtf8(raw);
  while (base.endsWith('/')) {
    base.chop(1);
  }
  return base;
}
} // namespace ApiConfig

#endif // APICONFIG_H
