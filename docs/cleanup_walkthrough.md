# StoryToVideo 清理与收敛记录（walkthrough）

目标：整理项目文件夹，删除冗余/过时文件，收敛为**单机 Linux + NVIDIA GPU** 的一致部署方式（宿主机跑 Ollama），并保持文档/脚本引用一致。

## 1) Docker 收敛
- 保留：`docker-compose.yml`（单机全栈：model/gateway/server/mysql/redis/minio）
- 删除：`docker-compose.local.yml`、`docker-compose.server.yml`、`docker-compose.cloud.yml`、`model/docker-compose.gpu.yml`
- 约定：
  - Ollama **运行在宿主机**（默认 `11434`），容器通过 `OLLAMA_HOST=http://host.docker.internal:11434` 访问
  - SVD 默认开启：`SVD_ENABLED=1`（可在 `.env` 中设置为 `0` 关闭）

## 2) 部署脚本收敛
- 保留并更新：`deploy-server.sh`（统一使用 `docker compose -f docker-compose.yml`）
- 删除：`deploy-wsl.sh`、`deploy-windows.ps1`

## 3) 发布文档归档
- 新增目录：`docs/releases/`
- 移动：
  - `RELEASE_NOTES_v1.0.0.md` → `docs/releases/RELEASE_NOTES_v1.0.0.md`
  - `RELEASE_v1.0.0_CHECKLIST.md` → `docs/releases/RELEASE_v1.0.0_CHECKLIST.md`
  - `RELEASE_COMPLETION_REPORT.md` → `docs/releases/RELEASE_COMPLETION_REPORT.md`
- 删除：`RELEASE_NOTES.md`、`QUICKSTART.md`

## 4) 删除过时脚本与产物
- 删除根目录临时/调试脚本（代理/Clash/GPU 部署/模型下载等）
- 删除构建产物与日志：
  - `client/12.2StoryToVideo/*.o.tmp`
  - `client/12.2StoryToVideo/client.log`
- 删除：`mock-server/`
- FRP 暂时弃用：删除 `frp/`

## 5) 环境变量与文档一致性
- `.env.cloud.example`：
  - 去除敏感 key 示例值（全部改为占位/空值）
  - 默认改为宿主机 Ollama（`LLM_PROVIDER=ollama`）
  - 增加 img2vid 智能降级相关 `IMG2VID_*` 变量
- `.gitignore`：
  - 增加 `.env`、`svd_model/`、`*.o.tmp`、`client/*/client.log` 等忽略规则
- 文档更新：移除 FRP 与多套 Compose 的引用，统一指向 `docker-compose.yml` 与 `deploy-server.sh`

## 6) Img2Vid 智能降级
- `gateway/main.py`：在 img2vid 失败/超时或输出异常时，自动生成静态视频片段作为 fallback；并可在失败后对后续场景直接 fallback（由 `IMG2VID_*` 环境变量控制）。

