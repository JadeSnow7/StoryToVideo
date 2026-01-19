# 🎬 StoryToVideo - 故事到视频生成系统

> 一个端到端的 AI 视频生成平台：输入故事文本，自动生成分镜、图片、配音，最终合成完整视频。

[![GitHub](https://img.shields.io/badge/GitHub-JadeSnow7%2FStoryToVideo-blue)](https://github.com/JadeSnow7/StoryToVideo)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Qt](https://img.shields.io/badge/Qt-6.5+-41CD52)](https://www.qt.io/)
[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8)](https://golang.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB)](https://www.python.org/)

---

## 📖 目录

- [项目简介](#-项目简介)
- [系统架构](#-系统架构)
- [功能特性](#-功能特性)
- [目录结构](#-目录结构)
- [快速开始](#-快速开始)
- [详细部署指南](#-详细部署指南)
- [API 文档](#-api-文档)
- [技术栈](#-技术栈)
- [常见问题](#-常见问题)
- [贡献指南](#-贡献指南)

---

## 🎯 项目简介

**StoryToVideo** 是一个将文本故事自动转化为视频的 AI 创作工具。用户只需输入一段故事文本，系统将自动：

1. **分镜生成** - 利用 LLM 将故事拆解为结构化分镜脚本
2. **图像生成** - 使用 Stable Diffusion 为每个分镜生成关键帧
3. **语音合成** - 通过 TTS 模型生成配音旁白
4. **视频合成** - 将所有素材拼接为完整 MP4 视频

### 核心价值

| 特性 | 说明 |
|------|------|
| 🚀 **端到端自动化** | 从文本到视频，全流程 AI 驱动 |
| 🎨 **多风格支持** | 电影风、二次元、写实等多种预设风格 |
| ✏️ **可编辑分镜** | 支持手动调整 Prompt、旁白、转场效果 |
| 💻 **跨平台客户端** | 基于 Qt/QML 的桌面应用，支持 Windows/macOS |
| 🔧 **模块化架构** | 前后端分离，模型服务可独立部署 |

---

## 🏗 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           用户层                                         │
│                    PC 客户端 (Qt 6.5 / QML / C++)                        │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ REST API / WebSocket
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│           单机部署 (Linux + NVIDIA GPU, Docker Compose)                  │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────────────────┐  │
│  │ Go Server   │   │ Gateway      │   │ Model Node (FastAPI)         │  │
│  │ Gin :8080   │   │ FastAPI :8000│   │ LLM/txt2img/img2vid/TTS      │  │
│  └─────┬───────┘   └──────┬───────┘   └──────────────┬──────────────┘  │
│        │                  │                           │                 │
│        ├── MySQL           │                           ├── Ollama(host) │
│        ├── Redis + Asynq   │                           │   :11434       │
│        └── MinIO           │                           │                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### 数据流程

```
用户输入故事 → LLM 生成分镜 → SD 生成图片 → TTS 生成配音 → FFmpeg 合成视频 → 导出 MP4
```

---

## ✨ 功能特性

### 已实现功能 ✅

| 功能 | 描述 |
|------|------|
| **新建故事** | 输入文本(≤500字)，选择风格，一键生成分镜 |
| **分镜看板** | 横向卡片流展示，状态可视化（等待/生成中/完成/失败） |
| **分镜编辑** | 编辑 Prompt、旁白文本、选择转场效果 |
| **图片生成** | 基于 SD Turbo 的快速文生图 |
| **视频预览** | 内置播放器，支持播放/暂停/进度控制 |
| **视频导出** | 导出为 MP4 文件 |
| **项目管理** | 历史项目查看、删除 |

### 规划中功能 🚧

- [x] 图生视频 (SVD Img2Vid，可关闭并自动降级静态视频)
- [ ] 背景音乐合成
- [ ] 多语言 TTS
- [ ] 批量导出
- [ ] 云端项目同步

---

## 📁 目录结构

```
StoryToVideo/
├── 📂 client/                      # 桌面客户端 (Qt 6.5 / QML / C++)
│   └── 📂 12.2StoryToVideo/        # Qt/QML 主项目 (qmake)
│       ├── src/                    # C++ 源码/头文件
│       ├── qml/                    # QML 页面
│       ├── scripts/                # 构建/运行脚本（macOS）
│       ├── StoryToVideoGenerator.pro
│       └── qml.qrc
│
├── 📂 ios/                         # iOS 客户端 (Swift / SwiftUI)
│   ├── 📂 StoryToVideo/            # 主项目代码
│   └── project.yml                 # XcodeGen 配置
│
├── 📂 server/                      # 后端服务 (Go 1.21 / Gin)
│   ├── 📂 cmd/                     # 服务入口
│   ├── 📂 config/                  # 配置文件
│   ├── 📂 internal/                # 业务逻辑
│   └── Dockerfile                  # 容器化配置
│
├── 📂 gateway/                     # 模型网关 (Python / FastAPI)
│   ├── main.py                     # 聚合 LLM/SD/TTS 调用
│   ├── 📂 routers/                 # API 路由
│   └── 📂 services/                # 服务封装
│
├── 📂 model/                       # 模型服务 (Python)
│   └── 📂 services/                # 各模型服务
│       ├── llm.py                  # LLM 分镜生成 (Qwen2.5)
│       ├── txt2img.py              # 文生图 (SD Turbo)
│       ├── img2vid.py              # 图生视频 (SVD)
│       └── tts.py                  # 语音合成 (CosyVoice)
│
├── 📂 docs/                        # 项目文档
│   ├── ARCHITECTURE.md             # 架构设计
│   ├── apis.md                     # API 文档
│   ├── deploy.md                   # 部署指南
│   ├── releases/                   # 发布归档
│   └── ...                         # 其他文档
│
├── 📄 docker-compose.yml           # 单机 Docker 编排配置
├── 📄 deploy-server.sh             # Docker 部署脚本
├── 📄 environment.yml              # Conda 环境配置
├── 📄 start.sh                     # 快速启动脚本
├── 📄 CHANGELOG.md                 # 版本变更记录
└── 📄 README.md                    # 本文件
```

---

## 🚀 快速开始

### 环境要求

| 组件 | 版本要求 |
|------|----------|
| **操作系统** | Windows 10+ / macOS 12+ / Ubuntu 20.04+ |
| **Qt** | 6.5+ (with Qt Quick) |
| **Go** | 1.21+ |
| **Python** | 3.10+ |
| **CUDA** | 12.x (GPU 推理) |
| **GPU 显存** | ≥ 8GB (推荐 16GB+) |

### 一键启动 (单机 Docker, Linux)

```bash
# 0. 宿主机启动 Ollama（并拉取模型）
ollama serve
ollama pull qwen2.5:0.5b

# 1. 克隆仓库
git clone https://github.com/JadeSnow7/StoryToVideo.git
cd StoryToVideo

# 2. 配置环境变量（可选：SVD_ENABLED=0 关闭图生视频，自动降级静态视频）
cp .env.cloud.example .env

# 3. 启动全栈
./deploy-server.sh up

# 4. 健康检查
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8080/v1/api/health
```

---

## 📦 详细部署指南

### 1. 单机 Docker 部署（推荐）

前置条件：
- Docker + `docker compose`
- NVIDIA Driver + NVIDIA Container Toolkit
- 宿主机 Ollama 已运行（默认 `11434`）

```bash
cp .env.cloud.example .env
./deploy-server.sh up
```

服务入口：
- Gateway: `http://127.0.0.1:8000`
- Go Server: `http://127.0.0.1:8080`
- MinIO Console: `http://127.0.0.1:9001`

SVD 图生视频：
- 默认开启（`SVD_ENABLED=1`）；设置 `SVD_ENABLED=0` 将自动降级为静态视频片段并继续流程。

### 2. 配置说明
- Compose：`docker-compose.yml`
- Server 配置：`server/config/config.docker.yaml`（容器内挂载为 `/app/config/config.yaml`）
- 产出目录：Docker 卷 `data_shared` 挂载到容器 `/data`

### 3. 客户端构建

```bash
cd client/12.2StoryToVideo

# 推荐：Qt Creator 打开 StoryToVideoGenerator.pro 直接构建运行

# 命令行（qmake）
qmake StoryToVideoGenerator.pro
make -j

# macOS 打包/运行（Homebrew Qt）
./scripts/deploy.sh
./scripts/run.sh
```

---

## 📡 API 文档

### 业务 API (服务端 :8080)

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/v1/api/projects` | 创建项目并生成分镜 |
| `GET` | `/v1/api/projects/:id` | 获取项目详情 |
| `GET` | `/v1/api/projects/:id/shots` | 获取分镜列表 |
| `POST` | `/v1/api/projects/:id/shots/:shot_id` | 更新分镜 |
| `POST` | `/v1/api/projects/:id/video` | 触发视频合成 |
| `GET` | `/v1/api/tasks/:task_id` | 查询任务状态 |
| `DELETE` | `/v1/api/projects/:id` | 删除项目 |

### 示例请求

**创建项目：**
```bash
curl -X POST "http://localhost:8080/v1/api/projects?Title=测试故事&StoryText=从前有一只小猫&Style=cinematic&ShotCount=4"
```

**响应：**
```json
{
  "project_id": "proj-xxxxx",
  "text_task_id": "task-text-xxxxx",
  "shot_task_ids": ["task-shot-001", "task-shot-002", "task-shot-003", "task-shot-004"]
}
```

**查询任务状态：**
```bash
curl "http://localhost:8080/v1/api/tasks/task-text-xxxxx"
```

**响应：**
```json
{
  "task": {
    "id": "task-text-xxxxx",
    "status": "finished",
    "progress": 100,
    "result": {
      "resource_type": "storyboard",
      "resource_url": "https://minio.xxx/storyboards/xxx.json"
    }
  }
}
```

---

## 🛠 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **客户端** | Qt 6.5+ / QML / C++ | 跨平台桌面应用 |
| **服务端** | Go 1.21+ / Gin | RESTful API 服务 |
| **数据库** | MySQL | 关系型数据存储 |
| **任务队列** | Redis + Asynq | 异步任务处理 |
| **对象存储** | MinIO | 图片/视频资源存储 |
| **模型网关** | Python / FastAPI | AI 模型编排 |
| **LLM** | Qwen2.5-0.5B (Ollama) | 分镜脚本生成 |
| **文生图** | SD Turbo (diffusers) | 快速图像生成 |
| **TTS** | CosyVoice | 语音合成 |

---

## ❓ 常见问题

### Q: 图片无法显示？
**A:** 检查以下几点：
1. 确认 MinIO 服务正常运行
2. 检查 `image_path` 是否为完整 URL（MinIO 返回的是签名 URL）
3. 客户端网络是否能访问 MinIO 地址

### Q: 任务一直卡在 pending？
**A:** 
1. 检查 Redis 服务是否正常
2. 查看 server 日志是否有任务入队
3. 确认 Gateway 服务可访问

### Q: 文生图失败？
**A:**
1. 检查 GPU 显存是否充足（建议 8GB+）
2. 确认 SD Turbo 模型已下载
3. 查看 txt2img 服务日志

### Q: 如何修改 API 地址？
**A:** 设置环境变量 `STORYTOVIDEO_API_BASE_URL`（默认 `http://127.0.0.1:8080`）：

```bash
export STORYTOVIDEO_API_BASE_URL=http://your-server:8080
```

（读取逻辑见 `client/12.2StoryToVideo/src/ApiConfig.h`）

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 开源协议

本项目采用 MIT 协议开源，详见 [LICENSE](LICENSE) 文件。

---

## 👥 团队成员

| 角色 | 职责 |
|------|------|
| **客户端开发** | Qt/QML 界面、网络封装、本地存储 |
| **服务端开发** | Go API、任务队列、数据库设计 |
| **AI 工程师** | 模型部署、Prompt 优化、效果调优 |

---

## 📞 联系我们

- **GitHub Issues**: [提交问题](https://github.com/JadeSnow7/StoryToVideo/issues)
- **GitHub Discussions**: [讨论区](https://github.com/JadeSnow7/StoryToVideo/discussions)

---

> 📌 **最后更新：** 2026.01.19 | **版本：** v1.0.0
