# StoryToVideo 多模型流水线说明

## 项目概览
- 目标：本地化从故事文本到成片的视频生成流水线，复刻/对标 https://github.com/JadeSnow7/StoryToVideo/ 的流程。
- 模型：LLM(Qwen2.5-0.5B @ Ollama)、文生图(Stable Diffusion Turbo @ diffusers)、图生视频(Stable-Video-Diffusion-Img2Vid @ diffusers)、TTS(CosyVoice-mini @ FastAPI)。
- 架构：FastAPI 网关负责编排与对外 API，内部四个子服务，各自独立推理，结果通过共享存储/对象存储传递。
- 工作流：故事 → 分镜(JSON) → 关键帧(PNG) → 短片(MP4) → 旁白(WAV/MP3) → ffmpeg 合成成片。

## 服务组件
- `gateway`：FastAPI 网关/编排，暴露统一 API，做任务状态跟踪和 ffmpeg 合成。
- `llm-service`：调用 Ollama 中的 Qwen2.5-0.5B，将故事+风格转为分镜 JSON。
- `txt2img-service`：diffusers 版 Stable Diffusion Turbo，批量生成关键帧；支持分辨率、步数、CFG 等参数。
- `img2vid-service`：Stable-Video-Diffusion-Img2Vid，将单帧转为短视频片段，转场时长/拼接在编排层完成。
- `tts-service`：CosyVoice-mini 封装为 FastAPI，将旁白文本转音频；可缓存声学模型。
- 存储：本地目录 `./data/{storyboards,frames,clips,audio,final}`，可切换 MinIO/S3 兼容对象存储。

## 数据流（高层）
1) `/storyboard`：故事+风格 → 分镜 JSON（含场景标题、prompt、旁白、BGM 提示）。
2) `/frames`：分镜 prompt 批量 → PNG 关键帧。
3) `/clips`：关键帧 + 转场参数 → 短视频片段 MP4。
4) `/narration`：旁白文本 → 音频。
5) `/render`：编排一键跑全链路，ffmpeg 合成片段+音轨，可选叠加 BGM。
6) `/tasks/{id}`：异步任务状态查询。

## 目录建议
- `docs/`：中文文档（本文件、apis、pipeline、deploy、ops）。
- `gateway/`：FastAPI 网关与编排逻辑、任务表、ffmpeg 调用。
- `services/llm/`、`services/txt2img/`、`services/img2vid/`、`services/tts/`：各自的 FastAPI/推理脚本、Dockerfile。
- `data/`：默认输出；实际可挂载到持久化卷或对象存储挂载点。
- `scripts/`：启动/测试/下载模型脚本。
- `docker/`：可选 Compose 或单服务 Dockerfile。

## 开发与联调目标
- 打通 `/storyboard` → `/frames` → `/clips` → `/narration` → `/render` 的最小可用链路。
- 建立异步任务与状态查询；初期可用内存/文件表，后续换 Redis/Celery。
- 提供示例请求 JSON 与返回路径约定，确保输出可追踪与复现。
- 通过 FRP 暴露网关（或全链路）到外部测试入口。

## 依赖与要求（简表）
- OS：Linux x86_64；Python 3.10/3.11。
- GPU：建议 >=24GB 显存（SD Turbo + SVD 更稳）；可多卡分配（SD/SVD 分卡，LLM/TTS 共享）。
- CUDA/驱动：CUDA 12.x，PyTorch 2.1+；建议启用 xformers/flash-attn（可选）。
- 工具：ffmpeg、Ollama、FRP（frpc）、uvicorn/FastAPI。

## 参考执行顺序（手动验证）
1) 启动 Ollama 并拉取 Qwen2.5-0.5B；启动 `llm-service`。
2) 启动 `txt2img-service`（SD Turbo）和 `img2vid-service`（SVD Img2Vid）。
3) 启动 `tts-service`（CosyVoice-mini）。
4) 启动网关 `gateway`，调用 `/render` 做 1~2 场景小样例验证。
5) 配置 `frpc` 将网关暴露到公网测试。
