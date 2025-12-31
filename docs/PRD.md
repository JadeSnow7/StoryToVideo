# 产品需求文档 (PRD) - StoryToVideo PC / Product Requirements

版本：v1.0 / Version: v1.0  
日期：2025.11.17 / Date: 2025.11.17  
修改人：PM / Author: PM  
描述：MVP 核心功能定义 / MVP scope definition

## 1. 背景与定位 / Background & Positioning
- 名称：StoryToVideo (PC Client) / Name: StoryToVideo (PC Client)
- 定位：极简“故事到视频”练手项目，强调功能跑通与扩展性。 / Minimal practice project, focus on end-to-end and extensibility.
- 核心目标：19 天跑通完整链路（故事输入→分镜→生成→预览导出）。 / Goal: finish E2E in 19 days.
- 用户：需要快速将文本创意可视化的创作者。 / Users: creators needing quick text-to-visual.
- 环境：Windows/macOS，Qt/QML。 / Environment: Windows/macOS, Qt/QML.

## 2. 功能需求 (MVP) / Functional Scope
### 2.1 核心流程 / Core flow
- 新建故事：文本输入→AI 结构分析→生成分镜列表。 / Create story: text in → AI parses → storyboard list.
- 分镜编辑：可调 Prompt，AI 生图。 / Shot edit: tweak prompt, AI generates image.
- 视频合成：可选图生视频→拼接片段→导出 MP4。 / Video: optional img2vid → stitch → export MP4.

### 2.2 功能列表 / Features
- **F1 新建故事**：≤500 字文本；3+ 风格预设（电影/二次元/写实）；点击生成调用 LLM；超时/失败可重试。 / F1 Create: text ≤500 words; 3+ styles; call LLM; retry on timeout/fail.
- **F2 Storyboard**：横向卡片流；缩略图/序号/描述；状态标签（等待/进行/完成/失败）；点击进详情。 / F2 Storyboard: horizontal cards with thumbnail/index/desc; statuses; open detail.
- **F3 Shot Detail**：Prompt/Narration 可编辑；\"Generate Image\" 触发 SD；转场 P1：Crossfade；状态流转；可重新生成。 / F3 Detail: edit prompt/narration; Generate Image (SD); transition P1 Crossfade; state changes; regenerate.
- **F4 Preview**：顺序播放片段；音量/进度；导出 MP4（文件对话框+Toast）。 / F4 Preview: play sequence; volume/seek; export MP4 with dialog+toast.
- **F5 Assets**：历史列表网格；按标题/时间过滤；hover 显示打开/删除；新建跳转 Create。 / F5 Assets: grid history; filter by title/time; hover open/delete; new -> Create.

## 3. 非功能需求 / Non-functional
- 性能：UI 60fps；所有网络异步，禁止阻塞 UI 线程。 / Performance: 60fps UI; async network, no UI blocking.
- 持久化：SQLite + 本地文件缓存，离线可读已生成内容。 / Persistence: SQLite + file cache; offline readable.
- 部署：PC 客户端 + 云服务端（业务逻辑）+ 本地算力节点（模型，FRP 穿透）。 / Deployment: PC client + cloud server + local model node via FRP.

## 4. 设计规范 / Design system
- 分辨率：基准 1280x720，自适应 1920x1080。 / Resolution: base 1280x720, adaptive to 1920x1080.
- 主题：Dark；背景 #1E1E1E；主色 #3B82F6；文本 #FFFFFF/#9CA3AF；字体 微软雅黑/Roboto。 / Dark theme; background #1E1E1E; primary #3B82F6; text #FFFFFF/#9CA3AF; fonts Microsoft YaHei/Roboto.

## 5. 页面流转 (User Flow) / Navigation
```
graph LR
    A[Splash/Login] --> B[Assets/Home]
    B -->|新建 / New| C[Create]
    C -->|生成成功 / Success| D[Storyboard]
    B -->|历史项目 / History| D
    D -->|卡片 / Card| E[Shot Detail]
    E -->|返回 / Back| D
    D -->|合成视频 / Compose| F[Preview]
    F -->|导出 / Export| G[Local File]
```

## 6. 交互要点 / Interaction highlights
- **Assets**：网格；hover 显示打开/删除；点击新建进入 Create。 / Grid; hover open/delete; new -> Create.
- **Create**：左右分栏；生成时按钮禁用+loading；长耗时用 WS/轮询。 / Split view; disable button + loading; WS/poll for long task.
- **Storyboard**：底部横向 timeline；卡片高亮选中；双击进详情；Action Bar：生成全部、合成预览。 / Bottom horizontal timeline; highlight selection; double-click detail; actions: generate all, preview compose.
- **Shot Detail**：左图右表单；未生成占位，生成中遮罩+进度，完成显示重生按钮。 / Left image, right form; placeholder → loading overlay → regenerate button.
- **Preview**：标准播放器；Export 弹文件对话框，成功 Toast。 / Standard player; export dialog + toast on success.

## 7. 技术架构摘要 / Tech overview
- 客户端：Qt 6.5+ QML + C++；QNetwork (REST/WS)；ViewModel + SQLite；FFmpeg+OpenGL 播放/合成。 / Client: Qt 6.5+ QML/C++; QNetwork REST/WS; ViewModel+SQLite; FFmpeg+OpenGL.
- 服务端：推荐 Django/DRF + Nginx/Gunicorn；PostgreSQL；任务队列；OSS/TOS；FRP 连接本地模型。 / Server: Django/DRF + Nginx/Gunicorn; PostgreSQL; task queue; OSS/TOS; FRP to local models.
- 模型节点：FastAPI 封装；Qwen2.5-0.5B（分镜/Narration）；SD Turbo（文生图）；SVD Img2Vid（可选）；CosyVoice-mini（TTS）。 / Model node: FastAPI; Qwen2.5-0.5B; SD Turbo; SVD Img2Vid optional; CosyVoice-mini TTS.

## 8. 数据与 API 草案 / Data & API draft
- 状态枚举：PENDING/RUNNING/SUCCESS/FAILED（含错误信息）。 / Status enum with error info.
- 数据模型 / Data models:
  - Project(id,title,style,created_at)
  - Shot(id,project_id,order,prompt,narration,image_url,status)
  - Task(id,type,payload,status,result_data,err_msg)
- API 示例 / API sample:
  - POST `/api/projects/create`
  - GET `/api/projects/{id}/storyboard`
  - POST `/api/shots/{id}/update_prompt`
  - POST `/api/shots/{id}/generate_image`
  - GET `/api/tasks/{task_id}/status`
  - POST `/api/webhook/task_complete`

## 9. 里程碑 / Milestones
- 11.23：前后端联调，点击新建→DB 记录→返回分镜列表。 / FE-BE integration; create story returns storyboard.
- 11.30：Storyboard 绑定；Shot Detail 生图；预览可用；TTS 接通；全链路跑通。 / Storyboard wired; shot image gen; preview; TTS; end-to-end.
- 12.02：UI/Loading/错误态；异常/重试/断线重连；导出稳定。 / Polish UI/loading/errors; retry/reconnect; stable export.
- 12.04：文档/PPT/录屏；12.05 Release。 / Docs/PPT/demo recording; 12.05 release.
