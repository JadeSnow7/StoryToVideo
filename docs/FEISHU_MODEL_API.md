# 飞书版模型服务 API 文档

面向“故事到视频”链路，整理了可直接在飞书文档发布的接口说明，覆盖语言模型分镜生成、文生图、图生视频以及任务查询与 WebSocket 推送。

## 基础信息
- **Base URL**：`https://api.example.com`（按部署替换）
- **版本**：`v1`
- **认证**：`Authorization: Bearer <token>`，可选 `X-Request-Id` 便于链路追踪
- **编码**：`Content-Type: application/json; charset=utf-8`
- **幂等**：推荐传 `Idempotency-Key` 防重复提交
- **默认模型**：文生图 `sd-turbo`，图生视频 `svd-img2vid`

### 通用返回格式
```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```
- `code`：0 表示成功；常见错误码：400 参数错误，401 未授权，404 不存在，429 频控，500 内部错误。

### 任务模型
- 耗时任务返回 `job_id`，通过查询接口或 WebSocket 订阅进度。
- 状态枚举：`pending` / `running` / `succeeded` / `failed` / `canceled`。

#### 通用任务查询
- `GET /v1/jobs/{job_id}`

响应示例：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "job_xxx",
    "type": "llm|t2i|i2v",
    "status": "running",
    "progress": 42,
    "result": {},
    "error": {}
  }
}
```

## 接口一览
1. 语言模型：生成分镜 `POST /v1/llm/storyboard`
2. 文生图：生成关键帧 `POST /v1/image/generate`
3. 图生视频：生成短视频片段 `POST /v1/video/generate`
4. 任务查询：`GET /v1/jobs/{job_id}`
5. WebSocket 进度推送（可选）：`GET wss://api.example.com/v1/ws`

---

## 1) 语言模型：生成分镜
- **URL**：`POST /v1/llm/storyboard`
- **功能**：将故事文本转为分镜 JSON，含标题、Prompt、旁白、BGM 建议等。

请求体：
```json
{
  "story_id": "story_001",
  "story_text": "很久以前……",
  "style": "movie",
  "target_shots": 8,
  "lang": "zh",
  "extras": {
    "tone": "warm",
    "duration_hint_sec": 60
  }
}
```

成功响应（任务创建）：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "job_llm_123",
    "status": "running"
  }
}
```

任务完成结果（经 `GET /v1/jobs/{job_id}` 获取）：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "job_llm_123",
    "status": "succeeded",
    "result": {
      "story_id": "story_001",
      "shots": [
        {
          "shot_id": "shot_001",
          "title": "清晨的街道",
          "prompt": "cinematic morning street, soft light, ...",
          "narration": "清晨，主角踏上旅程……",
          "bgm_hint": "lofi calm",
          "duration_sec": 5
        }
      ]
    }
  }
}
```

---

## 2) 文生图：生成关键帧
- **URL**：`POST /v1/image/generate`
- **功能**：基于分镜 Prompt 生成关键帧图片（默认 SD Turbo）。

请求体：
```json
{
  "shot_id": "shot_001",
  "prompt": "cinematic morning street, soft light, ...",
  "negative_prompt": "blurry, lowres",
  "style": "movie",
  "size": "1024x576",
  "model": "sd-turbo",
  "seed": 42,
  "steps": 15,
  "guidance_scale": 3.5,
  "scheduler": "euler",
  "safety_check": true
}
```

成功响应：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "job_t2i_456",
    "status": "running"
  }
}
```

任务完成结果：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "job_t2i_456",
    "status": "succeeded",
    "result": {
      "shot_id": "shot_001",
      "image_url": "https://cdn.example.com/shot_001.png",
      "meta": {
        "seed": 42,
        "size": "1024x576",
        "steps": 15,
        "model": "sd-turbo"
      }
    }
  }
}
```

---

## 3) 图生视频：生成短视频片段
- **URL**：`POST /v1/video/generate`
- **功能**：以关键帧生成短视频片段，默认 Stable Video Diffusion（Img2Vid）。

请求体：
```json
{
  "shot_id": "shot_001",
  "image_url": "https://cdn.example.com/shot_001.png",
  "duration_sec": 4,
  "fps": 24,
  "resolution": "1280x720",
  "model": "svd-img2vid",
  "transition": "kenburns",
  "motion_strength": 0.7,
  "seed": 123,
  "audio": {
    "voiceover_url": "https://cdn.example.com/vo_shot001.wav",
    "bgm_url": "https://cdn.example.com/bgm_lofi.mp3",
    "ducking": true
  }
}
```

成功响应：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "job_i2v_789",
    "status": "running"
  }
}
```

任务完成结果：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "job_i2v_789",
    "status": "succeeded",
    "result": {
      "shot_id": "shot_001",
      "video_url": "https://cdn.example.com/shot_001.mp4",
      "meta": {
        "duration_sec": 4,
        "fps": 24,
        "resolution": "1280x720",
        "model": "svd-img2vid"
      }
    }
  }
}
```

---

## 4) WebSocket 进度推送（可选）
- **URL**：`GET wss://api.example.com/v1/ws`
- **鉴权**：沿用 HTTP Header。
- **订阅**：传入 `job_id` 列表。

订阅示例：
```json
{ "action": "subscribe", "job_ids": ["job_llm_123","job_t2i_456","job_i2v_789"] }
```

推送示例：
```json
{
  "job_id": "job_i2v_789",
  "status": "running",
  "progress": 65,
  "message": "rendering frames"
}
```

---

## FAQ
- **并行与合成**：每个镜头独立 job，可并行提交；最终合成由客户端/服务端 FFmpeg 处理。
- **安全与审计**：可在文生图/图生视频前置安全审核（暴恐涉政等）。
- **失败重试**：结合 `Idempotency-Key` 识别重复请求，失败可重提或按 `job_id` 重拉结果。
