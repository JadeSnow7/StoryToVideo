# 📝 StoryToVideo Generator 项目技术文档

## 1. 项目概览与架构

本项目目标是开发一个桌面应用，实现从文本故事到视频内容的生成。核心在于解决 LLM/图像生成等耗时任务带来的前端阻塞问题，采用 **MVVM 架构** 和 **异步任务轮询机制** 实现前后端解耦。

* **客户端框架：** C++ (Qt 5.8) 和 QML。
* **服务端 API 地址：** `http://119.45.124.222:8080/v1/api/...`。
* **任务管理：** 异步任务 (Task) + `QTimer` 轮询。

### 1.1 架构分层

| 模块 | 文件 | 职责 |
| :--- | :--- | :--- |
| **视图 (View)** | `main.qml`, `AssetsPage.qml` 等 | 渲染 UI，管理页面跳转，发起业务操作。 |
| **视图模型 (ViewModel)** | `ViewModel.h`, `ViewModel.cpp` | 管理任务状态，驱动轮询，处理业务逻辑，转换数据格式。 |
| **网络管理 (Manager)** | `NetworkManager.h`, `NetworkManager.cpp` | 封装所有 API 请求细节，解析 `TaskID`，转发网络信号。 |

---

## 2. 前端 QML 文件功能与实现逻辑

前端采用 `StackView` 进行页面管理，通过 `viewModel` 对象与 C++ 逻辑通信。

### 2.1 页面结构与导航

| 文件 | 角色/功能 | 关键实现逻辑 |
| :--- | :--- | :--- |
| **`main.qml`** | **应用主入口与导航容器** | 定义 `ApplicationWindow`，使用 `StackView` (ID: `pageStack`) 作为核心导航结构。 |
| **页面跳转** | (通用逻辑) | 页面通过 `StackView.view.push()` 实现前进；通过 `StackView.view.clear()` 返回到 `AssetsPage.qml` (栈底)。|
| **交互** | (通用逻辑) | 按钮点击事件调用 C++ 暴露的 `viewModel.generateStoryboard(...)` 等方法。|

---

## 3. 服务端逻辑与客户端 C++ 驱动

### 3.1 后端 API 接口与任务流

整个流程的核心在于后端 **即时返回 `TaskID`**，将耗时操作转入后台。

| 业务功能 | 请求方法 & URL | 客户端 C++ 函数 | 后端核心动作 | 关键响应 |
| :--- | :--- | :--- | :--- | :--- |
| **创建项目 (启动分镜)** | `POST /v1/api/projects` | `createProjectDirect` | 创建项目记录，并立即启动初始分镜任务。 | 返回 `ProjectID` 和初始 **`TaskID`**. |
| **查询任务状态** | `GET /v1/api/tasks/{id}` | `pollTaskStatus` | 检查任务进度和结果是否准备就绪. | 返回 `status`, `progress` (0-100) 和 `result` (完成时). |

### 3.2 📂 `NetworkManager.cpp` (API 驱动实现)

`NetworkManager` 是所有网络请求的执行者，负责构建正确的请求并解析响应。

* **项目创建实现：** `createProjectDirect` 构造 URL Query 参数，发送 POST 请求。
* **任务轮询实现：** `pollTaskStatus` 负责拼接 `TaskID` 到 `TASK_API_BASE_URL` 并发送 GET 请求.
* **响应处理核心：**
    * 处理 `CreateProjectDirect` 响应时，解析 `ProjectID` 和 `TaskID`，并发射 `taskCreated` 信号.
    * 处理 `PollStatus` 响应时，解析 `status` 和 `progress`，并根据状态发射 `taskResultReceived` 或 `taskStatusReceived` 信号.

### 3.3 🧠 `ViewModel.cpp` (业务逻辑与状态管理实现)

`ViewModel` 是核心业务层，负责调度任务和管理异步状态。

* **任务启动 (`generateStoryboard`)：** 负责构造参数并调用 `NetworkManager::createProjectDirect` 启动流程.
* **轮询启动 (`handleTaskCreated`)：** 接收 `TaskID`，将其添加到 `QHash m_activeTasks`，并启动 `QTimer`.
* **轮询执行 (`pollCurrentTask`)：** 定时遍历 `m_activeTasks` 中的任务，调用 `NetworkManager::pollTaskStatus`.
* **进度更新 (`handleTaskStatusReceived`)：** 接收进度百分比，通过 `emit compilationProgress` 信号通知 QML 界面.
* **结果处理 (`handleTaskResultReceived`)：** 接收任务完成信号，调用 `processStoryboardResult` 或 `processImageResult` 等函数进行数据格式转换，并最终通过信号通知 QML.

---

## 4. C++ 文件功能总览

| 文件名 | 类型 | 主要功能 | 核心职责 |
| :--- | :--- | :--- | :--- |
| **`main.cpp`** | C++ | 程序入口 | 实例化 `ViewModel`，通过 `setContextProperty` 暴露给 QML. |
| **`NetworkManager.h`** | H | 接口定义 | 声明所有 API 函数和用于通知 `ViewModel` 的信号 (`taskCreated`, `taskStatusReceived`). |
| **`NetworkManager.cpp`** | C++ | API 实现 | 实现所有 HTTP/JSON 交互，包括 `POST /projects` 和 `GET /tasks/{id}` 的细节. |
| **`ViewModel.h`** | H | 逻辑模型定义 | 声明 `Q_INVOKABLE` 接口、槽函数、`QTimer` 和 `m_activeTasks`. |
| **`ViewModel.cpp`** | C++ | 业务实现 | 实现任务调度、`QTimer` 轮询、信号连接、数据格式转换和结果分发. |