cmake_minimum_required(VERSION 3.16)
project(storytovideo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 6.5 COMPONENTS Quick REQUIRED)

qt_standard_project_setup()

qt_add_executable(${PROJECT_NAME}
    MACOSX_BUNDLE
    src/main.cpp
)

target_link_libraries(${PROJECT_NAME}
    PRIVATE Qt6::Quick
)

qt_add_qml_module(${PROJECT_NAME}
    URI StoryToVideo
    VERSION 1.0
    QML_FILES
        qml/Main.qml
)

install(TARGETS ${PROJECT_NAME}
    BUNDLE DESTINATION .
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

if(APPLE)
    set_target_properties(${PROJECT_NAME} PROPERTIES
        MACOSX_BUNDLE_GUI_IDENTIFIER "com.storytovideo.app"
        MACOSX_BUNDLE_BUNDLE_NAME "StoryToVideo"
        MACOSX_BUNDLE TRUE
    )

    set(CPACK_GENERATOR "DragNDrop")
    set(CPACK_PACKAGE_NAME "StoryToVideo")
    set(CPACK_PACKAGE_FILE_NAME "StoryToVideo-macOS")
    set(CPACK_DMG_VOLUME_NAME "StoryToVideo")
    include(CPack)
endif()
