# StoryToVideo 代码规范（重构版）

本文基于当前仓库结构（`server/` Go + `gateway/`/`model/` Python + `client/` Qt/QML），面向重构后的统一规范。对既有代码允许渐进迁移，但新增/修改代码必须遵守。

## 0. 适用范围与现状
- 适用范围：`server/`（Gin + Asynq）、`gateway/`（FastAPI 编排）、`model/`（LLM/T2I/I2V/TTS）、`client/`（Qt/QML）、后续 `client/ios/`。
- 现状要点：Qt 客户端走 Go Server；Go Server 再调用 Gateway；任务状态由 DB + 轮询/WS 推送。命名与 JSON 字段存在 camelCase/snake_case 混用，需要统一。

## 1. 命名规范
### 1.1 文件命名
- 源码文件默认使用 `kebab-case`：`task-scheduler.go`、`model-gateway.py`。
- 例外（工具/语言约束）：
  - Python 模块文件：`snake_case.py`（避免导入问题）。
  - QML/Qt UI 文件：保持 `PascalCase.qml` 与组件名一致。
  - C++ 头/源文件：与类名一致（`ViewModel.h/.cpp`）。
  - Swift 文件：与类型名一致（`ProjectViewModel.swift`）。
- 数据输出文件/路径遵循现有流水线规范（小写+数字+下划线），不强制使用 `kebab-case`。

### 1.2 变量/函数/类型命名
- 通用规则：变量/函数使用 `lowerCamelCase`，类型/接口使用 `PascalCase`。
- Go：导出符号使用 `PascalCase`，包内私有使用 `lowerCamelCase`。
- Swift/C++/QML：同上。
- Python：遵循 `snake_case`（函数/变量）+ `PascalCase`（类），仅对外 JSON 字段统一为 `lowerCamelCase`。
- JSON 字段统一 `lowerCamelCase`（如 `projectId`、`shotId`、`taskId`），禁止同一层混用 `project_id`/`projectId`。

### 1.3 常量命名
- 跨模块/配置/错误码常量统一 `UPPER_SNAKE_CASE`：`MAX_TASK_COUNT`、`TASK_STATUS_PENDING`。
- 语言例外：若语言强约束无法采用大写命名，使用 `UPPER_SNAKE_CASE` 作为字符串值或序列化值。

## 2. 代码结构
### 2.1 文件组织
- 单一职责：每个文件只负责一类功能，避免超大文件。
- 推荐重构结构（示例）：
  - `server/cmd/api/main.go`
  - `server/internal/{config,models,service,queue,routers}`
  - `gateway/{routers,services,store,schemas}`
  - `model/services/{llm,txt2img,img2vid,tts}.py`
  - `client/qt`（现有）、`client/ios`（新增）

### 2.2 解耦设计
- API 层 → Service → Repository/Client 三层分离，禁止跨层直接调用具体实现。
- 用接口（Go interface/Python Protocol/Swift protocol）隔离实现细节。
- 任务编排与状态更新必须集中在 `service/orchestrator` 类模块中。

### 2.3 注释和文档
- 文件顶部增加简短模块说明。
- 导出函数/公开方法必须写简短注释，说明用途与关键参数。
- API 接口注释需包含请求/响应结构和状态码。

## 3. 代码风格
### 3.1 代码布局
- 函数长度建议 20–40 行，超出需拆分。
- 格式化统一：
  - Go：`gofmt`
  - Python：`black` + `ruff`（或等价）
  - C++：`clang-format`
  - Swift：`swift-format`（可选）
- 行宽建议 100 字符；禁止混用 tab/space。

### 3.2 错误处理
- 早返回：错误检查在函数开头完成。
- Go 使用 `fmt.Errorf("...: %w", err)` 进行错误包装。
- API 统一错误响应结构：
  - `{"error":"...","code":"...","requestId":"..."}`

### 3.3 并发控制
- Go：共享资源使用 `sync.Mutex/RWMutex`；并发任务使用 `goroutines + channels`，必须携带 `context`。
- Python：使用 `asyncio` + `Semaphore/Lock` 控制并发。
- C++/Qt：使用 `QMutex/QReadWriteLock`；跨线程 UI 更新需通过信号/槽。
- Swift：使用 `actor` 或 `@MainActor` 管理状态，必要时 `TaskGroup` 控制并发。

## 4. 状态管理与异步模型
### 4.1 状态模型
- 统一 Task 状态集合：
  - `pending | blocked | processing | finished | failed | cancelled`
- 只有状态管理模块可以更新状态；其他模块通过接口提交变更请求。
- 允许的状态迁移需在代码中显式检查（提交/回滚）。

### 4.2 异步任务调度
- 统一使用 Redis + Asynq（Go 端）调度任务；Gateway 负责调用模型并回写结果。
- 任务必须携带 `projectId`、`shotId`、`traceId`；结果写入 DB 并落盘/OSS。
- 客户端优先使用 WebSocket `/tasks/:task_id/wss`，轮询 `/v1/api/tasks/:task_id` 作为兜底。

## 5. 代码质量与安全
### 5.1 安全性
- 文件写入/外部调用必须做权限与路径校验。
- 接口参数必须校验与限流；敏感操作需鉴权（`X-API-Key` 或等价）。
- iOS 端避免使用私有 API，遵循 App Store 审核规范。

### 5.2 单元测试
- Go：`testing` + `httptest` + `sqlmock`。
- Python：`pytest` + `respx`/`responses`。
- C++/Qt：`QtTest`。
- Swift：`XCTest` + `URLProtocol` Mock。

### 5.3 性能优化
- 先 Profile 再优化：Go `pprof`、Python `py-spy`/`cProfile`、iOS Instruments。
- GPU 任务需设置并发上限；热点路径使用缓存与分片并行。

## 6. 迁移与兼容策略
- 新代码必须遵守此规范；旧代码在“被修改时”逐步迁移。
- API 字段命名变更必须兼容旧字段，提供过渡期并记录废弃计划。
