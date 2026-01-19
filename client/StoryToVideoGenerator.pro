
TEMPLATE = app

CONFIG += c++11
QT += core gui qml quick quickcontrols2 network multimedia sql

SOURCES += src/main.cpp \
    src/ViewModel.cpp \
    src/NetworkManager.cpp \
    src/datamanager.cpp \
    src/videoexporter.cpp
# C++ 头文件
HEADERS += src/ViewModel.h \
    src/ApiConfig.h \
    src/NetworkManager.h \
    src/datamanager.h \
    src/videoexporter.h

RESOURCES += qml.qrc

INCLUDEPATH += $$PWD/src

# Additional import path used to resolve QML modules in Qt Creator's code model
QML_IMPORT_PATH =

# Additional import path used to resolve QML modules just for Qt Quick Designer
QML_DESIGNER_IMPORT_PATH =

# The following define makes your compiler emit warnings if you use
# any feature of Qt which as been marked deprecated (the exact warnings
# depend on your compiler). Please consult the documentation of the
# deprecated API in order to know how to port your code away from it.
DEFINES += QT_DEPRECATED_WARNINGS

# You can also make your code fail to compile if you use deprecated APIs.
# In order to do so, uncomment the following line.
# You can also select to disable deprecated APIs only up to a certain version of Qt.
#DEFINES += QT_DISABLE_DEPRECATED_BEFORE=0x060000    # disables all the APIs deprecated before Qt 6.0.0

# Default rules for deployment.
qnx: target.path = /tmp/$${TARGET}/bin
else: unix:!android: target.path = /opt/$${TARGET}/bin
!isEmpty(target.path): INSTALLS += target

# 确保链接器包含 Homebrew 的库路径，帮助 macdeployqt 解析依赖
QMAKE_LFLAGS += -Wl,-rpath,/opt/homebrew/lib
