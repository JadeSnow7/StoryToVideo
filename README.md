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
│                        后端服务层 (云端)                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Go/Gin     │  │ PostgreSQL  │  │ Redis+Asynq │  │    MinIO    │    │
│  │  API 服务   │  │   数据库    │  │  任务队列   │  │  对象存储   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ FRP 内网穿透
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      模型服务层 (本地 GPU)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │    LLM      │  │  SD Turbo   │  │     SVD     │  │  CosyVoice  │    │
│  │ Qwen2.5-0.5B│  │   文生图    │  │  图生视频   │  │   TTS 语音  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                     Python FastAPI Gateway                              │
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

- [ ] 图生视频 (SVD Img2Vid)
- [ ] 背景音乐合成
- [ ] 多语言 TTS
- [ ] 批量导出
- [ ] 云端项目同步

---

## 📁 目录结构

```
StoryToVideo/
├── 📂 client/                      # 客户端代码 (Qt/QML)
│   ├── 📂 12.2StoryToVideo/        # Qt/QML 主项目
│   │   ├── main.cpp                # 程序入口
│   │   ├── main.qml                # 主界面 (StackView 导航)
│   │   ├── NetworkManager.cpp/h    # 网络请求封装
│   │   ├── ViewModel.cpp/h         # 视图模型层
│   │   ├── datamanager.cpp/h       # 本地数据管理
│   │   ├── videoexporter.cpp/h     # 视频导出 (FFmpeg)
│   │   ├── AssetsPage.qml          # 资产库/首页
│   │   ├── CreatePage.qml          # 新建故事页
│   │   ├── StoryboardPage.qml      # 分镜看板页
│   │   ├── ShotDetailPage.qml      # 分镜详情页
│   │   ├── PreviewPage.qml         # 预览导出页
│   │   └── Assets/                 # 静态资源
│   └── README.md                   # 客户端说明
│
├── 📂 server/                      # 服务端代码 (Go/Gin)
│   ├── main.go                     # 服务入口
│   ├── 📂 config/                  # 配置
│   ├── 📂 models/                  # 数据模型 (Project/Shot/Task)
│   ├── 📂 routers/                 # API 路由
│   └── 📂 service/                 # 业务逻辑 (队列/OSS/处理器)
│
├── 📂 gateway/                     # 模型网关 (Python/FastAPI)
│   └── main.py                     # 聚合 LLM/SD/TTS 调用
│
├── 📂 model/                       # 模型服务 (Python)
│   ├── 📂 services/                # 各模型服务
│   │   ├── llm.py                  # LLM 分镜生成 (Qwen2.5)
│   │   ├── txt2img.py              # 文生图 (SD Turbo)
│   │   ├── img2vid.py              # 图生视频 (SVD)
│   │   └── tts.py                  # 语音合成 (CosyVoice)
│   ├── 📂 scripts/                 # 启动脚本
│   └── requirements.txt
│
├── 📂 frp/                         # FRP 内网穿透配置
│   ├── frpc.toml                   # 本地客户端配置
│   └── frps.ini.sample             # 云端服务配置示例
│
├── 📂 docs/                        # 项目文档
│   ├── 飞书文档汇总.md              # 完整项目文档
│   └── 项目说明文档.md              # 详细说明
│
├── 📄 environment.yml              # Conda 环境配置
├── 📄 start.sh                     # 快速启动脚本
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

### 一键启动 (开发环境)

```bash
# 1. 克隆仓库
git clone https://github.com/JadeSnow7/StoryToVideo.git
cd StoryToVideo

# 2. 启动服务端 (需要配置好 config.yaml)
cd server
go run main.go

# 3. 启动模型网关 (另开终端)
cd gateway
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# 4. 构建并运行客户端 (另开终端)
cd client/12.2StoryToVideo
mkdir build && cd build
cmake .. -DCMAKE_PREFIX_PATH=/path/to/Qt/6.5.0/macos
cmake --build .
./StoryToVideoGenerator.app/Contents/MacOS/StoryToVideoGenerator
```

---

## 📦 详细部署指南

### 1. 服务端部署 (Go/Gin)

```bash
# 安装依赖
cd server
go mod tidy

# 配置数据库和 Redis
cp config/config.yaml.example config/config.yaml
vim config/config.yaml

# 运行
go run main.go
# 或构建后运行
go build -o server && ./server
```

**config.yaml 示例：**
```yaml
server:
  port: ":8081"

database:
  host: "localhost"
  port: 5432
  user: "postgres"
  password: "your_password"
  dbname: "storytovideo"

redis:
  addr: "localhost:6379"
  password: ""

minio:
  endpoint: "localhost:9000"
  access_key: "minioadmin"
  secret_key: "minioadmin"
  bucket: "storytovideo"
  use_ssl: false

worker:
  endpoint: "http://localhost:8000"  # Gateway 地址
```

### 2. 模型网关部署 (FastAPI)

```bash
cd gateway
pip install -r requirements.txt

# 配置环境变量
export LLM_URL="http://localhost:11434/api/chat"
export TXT2IMG_URL="http://localhost:8002/generate"
export IMG2VID_URL="http://localhost:8003/generate"
export TTS_URL="http://localhost:8004/narration"

# 启动
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. 模型服务部署

#### LLM (Ollama + Qwen2.5)
```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 拉取模型
ollama pull qwen2.5:0.5b-instruct

# 启动服务
ollama serve
```

#### 文生图 (SD Turbo)
```bash
cd model
pip install diffusers transformers accelerate torch

# 启动服务
uvicorn services.txt2img:app --host 0.0.0.0 --port 8002
```

#### TTS (CosyVoice)
```bash
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
pip install -r requirements.txt

# 启动服务
cd runtime/python/fastapi
python server.py --model_dir ../../pretrained_models/CosyVoice2-0.5B --port 8004
```

### 4. FRP 内网穿透配置

**云端 (frps):**
```ini
[common]
bind_port = 7000
```

**本地 (frpc.toml):**
```toml
serverAddr = "your.server.ip"
serverPort = 7000

[[proxies]]
name = "gateway"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8000
remotePort = 8000
```

### 5. 客户端构建

```bash
cd client/12.2StoryToVideo
mkdir build && cd build

# macOS
cmake .. -DCMAKE_PREFIX_PATH=/path/to/Qt/6.5.0/macos
cmake --build .

# Windows (使用 Qt Creator 或 CMake)
cmake .. -G "Visual Studio 17 2022" -DCMAKE_PREFIX_PATH=C:/Qt/6.5.0/msvc2019_64
cmake --build . --config Release
```

---

## 📡 API 文档

### 业务 API (服务端 :8081)

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
curl -X POST "http://localhost:8081/v1/api/projects?Title=测试故事&StoryText=从前有一只小猫&Style=cinematic&ShotCount=4"
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
curl "http://localhost:8081/v1/api/tasks/task-text-xxxxx"
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
| **数据库** | PostgreSQL | 关系型数据存储 |
| **任务队列** | Redis + Asynq | 异步任务处理 |
| **对象存储** | MinIO | 图片/视频资源存储 |
| **模型网关** | Python / FastAPI | AI 模型编排 |
| **LLM** | Qwen2.5-0.5B (Ollama) | 分镜脚本生成 |
| **文生图** | SD Turbo (diffusers) | 快速图像生成 |
| **TTS** | CosyVoice | 语音合成 |
| **内网穿透** | FRP | 本地 GPU 远程调用 |

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
**A:** 修改 `client/12.2StoryToVideo/NetworkManager.h` 中的常量：
```cpp
const QUrl PROJECT_API_URL = QUrl("http://your-server:8081/v1/api/projects");
```

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

> 📌 **最后更新：** 2025.12.06 | **版本：** v1.0.0
