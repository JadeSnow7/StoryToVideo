# 📽️ 故事到视频生成器 (Story-to-Video Generator)

这是一个基于 Qt C++ 和 QML 的练手项目，旨在实现一个完整的“故事到视频”内容生成链路。项目通过 LLM（Ollama）生成分镜描述，通过 Stable Diffusion (SD Turbo) 生成关键帧图像，并最终合成视频。

## ✨ 核心功能与技术栈

本项目兼容 **Qt 6.5+**（macOS/Windows，CMake 构建）环境，并实现了与外部 AI 服务的异步通信。

| 模块 | 技术栈 / API | 状态 | 职责 |
| :--- | :--- | :--- | :--- |
| **前端 UI** | Qt QML (兼容 5.8 / Controls 2.1) | ✅ 完成 | 提供五大页面和交互逻辑。 |
| **LLM 集成** | C++ Qt Network / Ollama (Qwen2.5) | ✅ 完成 | 异步调用 LLM API，生成并解析流式 JSON 分镜。 |
| **图像生成** | C++ Qt Network / SD Turbo (REST API) | ✅ 完成 | Base64 解码并保存关键帧图像到本地。 |
| **核心逻辑** | C++ ViewModel | ✅ 完成 | 统一状态管理、QML/C++ 双向通信。 |
| **视频处理** | FFmpeg / OpenGL | ⏳ 待实现 | 负责最终的视频合成和转场效果。 |

---

## 🏗️ 项目架构分层

项目采用标准的 Qt C++/QML 架构，确保前后端分离：

### I. C++ 后端层 (Business Logic)

| 文件名 | 职责说明 | 关键功能 |
| :--- | :--- | :--- |
| `ViewModel.h/cpp` | **状态与逻辑核心。** | 暴露供 QML 调用的函数 (`Q_INVOKABLE`)；解析 LLM JSON；协调网络请求。 |
| `NetworkManager.h/cpp`| **网络通信层。** | 封装 Ollama 和 Stable Diffusion 的 API 请求，处理异步回复和错误转发。 |
| `main.cpp` | **程序入口。** | 启动 QML 引擎；实例化并暴露 `viewModel` 对象。 |

### II. QML 前端层 (User Interface)

所有 QML 文件位于 `/qml` 目录下，通过 `StackView` 管理导航。

| 页面文件 | 职责说明 |
| :--- | :--- |
| `main.qml` | 启动与导航框架 (`StackView`)。 |
| `CreatePage.qml` | 故事文本输入，调用 LLM 生成分镜。 |
| `StoryboardPage.qml` | 展示 LLM 分镜结果，并提供【一键生成视频】入口。 |
| `ShotDetailPage.qml` | 编辑单个分镜的 Prompt/Narration，并触发 SD 图像生成。 |
| `AssetsPage.qml` | 资产库和项目列表。 |
| `PreviewPage.qml` | 视频预览和导出功能。 |

---

## ✅ 当前开发状态与成就

当前代码库已实现以下关键链路：

1.  **QML ↔ C++ 通信链路完整：** QML 可以调用 C++ 函数，C++ 可以通过信号返回数据和状态。
2.  **LLM 分镜生成成功：** 成功解决了 Ollama **模型名称**和 **流式 JSON 解析**难题，程序能稳定获取 LLM 返回的 5 个分镜数据。
3.  **分镜数据绑定：** LLM 生成的分镜数据成功传递并绑定到 `StoryboardPage`，实现了列表展示。
4.  **图像生成链路就绪：** `ShotDetailPage` 可调用 C++ 向 SD API 发送请求，C++ 端已集成 **Base64 解码**和**本地文件保存**逻辑。

### 待办事项 (TODOs)

1.  **启动 SD API 服务：** 必须手动启动 Stable Diffusion API 服务（如 Python Flask/FastAPI 监听 `http://localhost:5000`），否则图像生成将返回 **"连接被拒绝"** 错误。
2.  **视频合成：** 实现 `VideoProcessor` 类，集成 FFmpeg 库，完成视频合成和转场逻辑。
3.  **数据持久化：** 集成 SQLite，实现项目数据的离线存储。
4.  **修复视频预览：** 解决 Qt Multimedia 插件缺失问题，以启用 `Video` 元素。

## 🍎 macOS 本地构建步骤 (Qt 6 + CMake)

1) 安装依赖（Homebrew）：`brew install qt cmake ninja`  
2) 配置（以仓库根目录为起点）：  
   ```
   cd client
   cmake -S . -B build -G Ninja -DCMAKE_PREFIX_PATH=$(brew --prefix qt)
   ```
3) 编译并运行：  
   ```
   cmake --build build
   ./build/storytovideo.app/Contents/MacOS/storytovideo
   ```

> 说明：
> - CMake 已切换到 `StoryToVideoGenerator` 源码（QML + C++），无需再使用 qmake。  
> - macOS 使用 `AVFoundation` 多媒体后端；生成的图像保存到 `~/Library/Application Support/<app>/shots` 目录，避免写入 .app 内部。
