# StoryToVideo 启动指南与 API 快速参考

## 推荐启动方式（单机 Docker）
```bash
# 0) 宿主机启动 Ollama（并拉取模型）
ollama serve
ollama pull qwen2.5:0.5b

# 1) 启动全栈
cd StoryToVideo
cp .env.cloud.example .env
./deploy-server.sh up
```

## 服务列表（默认端口）
- Go Server：`8080`（对外业务 API）
- Gateway：`8000`（编排入口 + `/files/...` 静态资源）
- MinIO：`9000`（S3 API），Console：`9001`
- MySQL：`3306`
- Redis：`6379`

## 健康检查
```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8080/v1/api/health
```

## API 快速参考

### Gateway（127.0.0.1:8000）
健康检查：
```bash
curl -fsS http://127.0.0.1:8000/health
```

创建任务（`/v1/generate`）：
```bash
curl -X POST http://127.0.0.1:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "type": "generate_shot",
    "parameters": {
      "shot": {
        "prompt": "red apple on white background, simple, clean",
        "image_width": "512",
        "image_height": "384"
      }
    }
  }'
```

查询任务状态：
```bash
curl http://127.0.0.1:8000/v1/jobs/<JOB_ID>
```

返回结果中的 `result.resource_url` 指向 `/files/...` 静态资源。

### Go Server（127.0.0.1:8080）

创建项目（Query 参数）：
```bash
curl -X POST "http://127.0.0.1:8080/v1/api/projects?Title=test&StoryText=一只猫在窗边&Style=电影&ShotCount=4"
```

获取分镜列表：
```bash
curl http://127.0.0.1:8080/v1/api/projects/<PROJECT_ID>/shots
```

重新生成分镜图片（注意：服务端使用 Query 绑定）：
```bash
curl -X POST "http://127.0.0.1:8080/v1/api/projects/<PROJECT_ID>/shots/<SHOT_ID>?prompt=new+prompt&transition=cut"
```

查询任务状态：
```bash
curl http://127.0.0.1:8080/v1/api/tasks/<TASK_ID>
```

生成视频：
```bash
curl -X POST "http://127.0.0.1:8080/v1/api/projects/<PROJECT_ID>/video" \
  -H "Content-Type: application/json" \
  -d '{"shot_id": "", "fps": 12}'
```

`shot_id` 为空表示走整项目全链路生成。

## 检查中发现的问题（客户端图片显示）

1) **图片不刷新/显示旧图**
- `ShotDetailPage.qml` 绑定 `shotData.imageUrl`，但重生成后 `ViewModel::processImageResult` 只更新本地 `imagePath`，页面数据未必刷新。
- QML `Image` 默认缓存，URL 不变时不会强制刷新。
- 建议：重生成后更新 `shotData.imageUrl`，或加缓存参数 `?v=<task_id>`，或重新拉取分镜列表。

2) **UpdateShot 参数未生效**
- 服务端 `UpdateShot` 使用 `ShouldBindQuery` 读取参数，客户端目前发送 JSON body，会导致 prompt/transition 为空。
- 建议：客户端改为 query 参数，或服务端改为 `ShouldBindJSON`。

3) **API Base URL 混用**
- `NetworkManager.h` 使用 `127.0.0.1`，但 `ViewModel.cpp` 拼图像 URL 使用 `119.45.124.222`。
- 建议统一到同一 host，避免跨域与资源取错。

4) **初始分镜任务轮询未启动**
- `ViewModel` 中有 TODO，文本任务完成后未自动轮询 `shot_task_ids`，可能导致首批图片不更新。

5) **视频预览 URL 仍为占位路径**
- `StoryboardPage.qml` 中 `videoUrl` 为固定示例路径，未使用真实任务结果。
