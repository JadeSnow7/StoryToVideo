# StoryToVideo iOS 客户端实现方案（SwiftUI）

本方案基于当前仓库实际架构：`Qt Client → Go Server (:8080) → Gateway (:8000) → Model Services`（详见 `docs/three-tier-startup-api.md`）。iOS 客户端对接 Go Server 的 `/v1/api` 接口，Gateway 作为后端编排层无需 iOS 直连。

## 1. iOS 客户端基本架构
```
iOS App
├── View (SwiftUI)
├── ViewModel (@MainActor)
├── StateStore (ObservableObject/Actor)
├── APIClient (URLSession)
├── Orchestrator (JobState + TaskScheduler)
├── MediaCache (FileManager/CoreData)
└── Player (AVPlayer)
```

## 2. 状态与任务分离
- StateStore：只存储/发布状态，线程安全（`actor` 或 `@MainActor`）。
- Orchestrator：负责任务调度、依赖顺序、任务取消/重试策略。
- ViewModel：订阅 StateStore，仅触发业务动作，UI 只消费状态。

### 2.1 状态模型
后端 TaskStatus 统一为：
`pending | blocked | processing | finished | failed | cancelled`

iOS 侧映射：
- `.idle` → 未开始
- `.submitting` → pending/blocked
- `.running` → processing
- `.done` → finished
- `.error` → failed/cancelled

## 3. API 设计与对接（Go Server）
### 3.1 基础配置
- Base URL 来自 `STORYTOVIDEO_API_BASE_URL`（默认 `http://127.0.0.1:8080`）。
- API 版本：`/v1/api`.

### 3.2 主要接口
- 创建项目（Query 参数）  
  `POST /v1/api/projects?Title=&StoryText=&Style=&ShotCount=`
- 获取项目详情  
  `GET /v1/api/projects/:project_id`
- 获取分镜列表  
  `GET /v1/api/projects/:project_id/shots`
- 更新分镜并触发生成  
  `POST /v1/api/projects/:project_id/shots/:shot_id`（JSON）
- 生成视频  
  `POST /v1/api/projects/:project_id/video`（JSON）
- 生成整项目 TTS  
  `POST /v1/api/projects/:project_id/tts`
- 任务查询（轮询兜底）  
  `GET /v1/api/tasks/:task_id`
- 任务进度 WebSocket  
  `GET /tasks/:task_id/wss`

### 3.3 数据模型与 JSON 命名
后端现有字段存在 `snake_case` 与 `camelCase` 混用（如 `project_id` 与 `projectId`）。iOS 端需用 `CodingKeys` 精确映射，避免依赖 `keyDecodingStrategy`。

#### 3.3.1 完整 Swift 模型示例

```swift
// MARK: - CreateProject Response
struct CreateProjectResponse: Decodable {
    let projectId: String
    let textTaskId: String
    let shotTaskIds: [String]

    enum CodingKeys: String, CodingKey {
        case projectId = "project_id"
        case textTaskId = "text_task_id"
        case shotTaskIds = "shot_task_ids"
    }
}

// MARK: - GetShots Response (wrapped)
struct GetShotsResponse: Decodable {
    let shots: [Shot]
    let projectId: String
    let totalShots: Int

    enum CodingKeys: String, CodingKey {
        case shots
        case projectId = "project_id"
        case totalShots = "total_shots"
    }
}

// MARK: - Task (matches Go models/task.go)
struct Task: Decodable {
    let id: String
    let projectId: String          // JSON: "projectId" (camelCase)
    let shotId: String?            // JSON: "shotId"
    let type: String?
    let status: String
    let progress: Int
    let message: String
    let parameters: TaskParameters?
    let result: TaskResult?
    let error: String
    let estimatedDuration: Int     // JSON: "estimatedDuration"
    let startedAt: Date?           // JSON: "startedAt"
    let finishedAt: Date?          // JSON: "finishedAt"
    let createdAt: Date?           // JSON: "createdAt"
    let updatedAt: Date?           // JSON: "updatedAt"
}

// MARK: - GetTaskStatus Response (REST API - wrapped)
struct TaskStatusResponse: Decodable {
    let task: Task
}

// MARK: - GetProject Response
struct GetProjectResponse: Decodable {
    let projectDetail: Project
    let shots: [Shot]
    let recentTask: Task?

    enum CodingKeys: String, CodingKey {
        case projectDetail = "project_detail"
        case shots
        case recentTask = "recent_task"
    }
}
```

#### 3.3.2 API 响应结构注意事项

| 接口 | 响应格式 | 备注 |
|------|----------|------|
| `GET /v1/api/tasks/:id` | `{"task": {...}}` | 包装在 `task` 字段内 |
| `GET /v1/api/projects/:id/shots` | `{"shots": [...], "project_id": "...", "total_shots": n}` | 包装对象，**非**纯数组 |
| `GET /v1/api/projects/:id` | `{"project_detail": {...}, "shots": [...], "recent_task": {...}}` | 复合响应 |
| `WS /tasks/:id/wss` | 裸 Task 对象 | **不在 /v1/api 下**，**无** wrapper |

#### 3.3.3 WebSocket 注意
- WebSocket 路径是 `/tasks/:id/wss`（**不是** `/v1/api/tasks/:id/wss`）
- WebSocket 推送的是**裸 Task 对象**，不是 `{"task": ...}` 包装
- iOS 端需单独定义 WebSocket 解码模型或复用 `Task` 直接解码

## 4. 异步状态管理与并发控制
### 4.1 Orchestrator 任务流程
1) 创建项目 → 获取 `text_task_id` + `shot_task_ids`
2) 订阅 text task（WS 优先，轮询兜底）
3) text 完成后拉取 shots 列表
4) 并发订阅 `shot_task_ids`，完成后更新 UI 与缓存

### 4.2 并发与取消
- 使用 `TaskGroup` 控制并发轮询数量（防止过多请求）。
- 取消任务：iOS 端可停止订阅与轮询；如后端新增取消接口，可同步触发后端取消。

示例：
```swift
func observeTasks(_ taskIds: [String]) async {
    await withTaskGroup(of: Void.self) { group in
        for taskId in taskIds {
            group.addTask {
                await self.observeTask(taskId)
            }
        }
        await group.waitForAll()
    }
}
```

## 5. UI 结构（SwiftUI）
### 5.1 页面建议
- ProjectListView：项目列表与状态。
- CreateProjectView：输入故事与风格。
- StoryboardView：分镜列表与缩略图。
- ShotDetailView：编辑 prompt/transition、触发重生。
- PreviewView：播放合成视频。

### 5.2 状态驱动渲染
UI 只关心状态变化，不直接处理后台任务。对每个任务展示 `ProgressView` 与错误提示。

## 6. 缓存与本地存储
- 图片/视频下载到 `Application Support/StoryToVideo/`。
- 项目与分镜元数据使用 CoreData（或轻量 SQLite）。
- 资源 URL 变更时增加 cache-bust（如 `?v=<task_id>`）。

## 7. 安全与审核
- ATS 白名单配置，仅允许必要域名。
- 避免私有 API；仅使用 `AVFoundation`、`URLSession` 等官方 SDK。
- 网络超时、断网恢复、后台切换需有友好提示。

## 8. 落地步骤（里程碑）
1) App 初始化 + APIClient + 数据模型
2) 创建项目 + Task 状态订阅
3) 分镜列表与分镜编辑
4) 视频生成与预览
5) 缓存/离线浏览
6) XCTest 覆盖与性能优化

## 9. 已知问题与兼容性说明

> [!IMPORTANT]
> 以下 API 响应结构问题需在 iOS 端特别处理：

1. **JSON 字段命名混用**：Go Server 混用 `snake_case`（响应键）和 `camelCase`（Task 模型字段）
2. **TTS 参数不生效**：当前 TTS 接口忽略请求体，使用默认参数
3. **Task 状态值**：后端同时使用 `finished` 和 `success` 表示完成，iOS 需兼容

详见实现计划（待补充）。
