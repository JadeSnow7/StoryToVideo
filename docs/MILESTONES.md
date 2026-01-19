# 里程碑与周计划 (11.17 - 12.05) / Milestones & Weekly Plan

## 团队角色（待填姓名） / Roles (fill names)
- 客户端组长 (PC Lead)：Qt 基建、Create/Storyboard、网络封装。 / Qt infra, Create/Storyboard, networking.
- 客户端开发 (PC Media)：Detail/Preview、FFmpeg/文件。 / Detail/Preview, FFmpeg/files.
- 服务端组长 (Server Lead)：接口/DB/部署。 / API/DB/deploy.
- 服务端开发 (Server Logic)：队列、网关编排、存储、Webhook。 / Queue, gateway orchestration, storage, webhook.
- AI 工程师 (LLM/TTS)：Qwen2.5、JSON Prompt、CosyVoice。 / Qwen2.5, prompts, CosyVoice.
- AI 工程师 (Visual)：SD Turbo、SVD 调研/回退。 / SD Turbo, SVD research/fallback.

## Week 1: 基建与联调 (11.17-11.23) / Foundation & Integration
- Client：Qt+CMake 工程；QNetwork 封装；Create 页 UI；Assets Mock 列表。 / Qt project, network wrapper, Create UI, mock Assets.
- Server：Go/Gin 部署；MySQL/Redis/MinIO；Docker Compose 编排；API 文档。 / Deploy Go/Gin; DB/queue/storage; Docker Compose; API doc.
- AI：Qwen2.5 分镜 JSON；SD Turbo HTTP；联合调试。 / Qwen2.5 storyboard JSON; SD Turbo API; joint debug.
- 里程碑：点击新建→DB 生成记录→返回分镜列表。 / Milestone: create story -> DB row -> storyboard response.

## Week 2: 核心功能 (11.24-11.30) / Core Features
- Client：Storyboard 横滚绑定数据；Shot Detail 异步刷图；视频预览；TTS 接入。 / Storyboard horizontal binding; Detail async image; preview; TTS.
- Server：任务队列超时/重试；OSS 上传；Webhook/进度推送。 / Queue timeout/retry; OSS upload; webhook/progress push.
- AI：Prompt 优化；TTS 部署；SVD 尝试（效果差则回退平移动效）。 / Prompt tuning; TTS deploy; SVD attempt or fallback.
- 里程碑：全链路跑通（文本→视频/动态分镜）。 / Milestone: end-to-end text to video/dynamic shots.

## Week 3: 优化与交付 (12.01-12.05) / Polish & Delivery
- Client：UI/Loading/错误态；离线缓存；导出稳定。 / UI/loading/error polish; offline cache; stable export.
- Server：压力测试；日志告警。 / Stress test; logging/alerts.
- AI：固化参数；部署手册。 / Freeze params; deployment guide.
- 文档：汇总技术文档，PPT/录屏。 / Docs, slides, demo recording.
- 里程碑：Release + Code Review。 / Milestone: Release + Code Review.
