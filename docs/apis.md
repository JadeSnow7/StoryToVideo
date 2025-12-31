# API 设计（草案）

## 约定
- 所有接口使用 HTTP JSON；默认 `application/json; charset=utf-8`。
- 路径基于网关 FastAPI；子服务内部接口不直接对外。
- 任务型接口返回 `task_id`，需用 `GET /tasks/{id}` 轮询获取最终结果。
- 路径字段返回相对路径（默认根 `./data`），对外暴露时可映射为签名 URL。

## 接口列表

### POST /storyboard
- 入参示例：
```json
{
  "story": "一位独行武者穿越废土城市寻找真相",
  "style": "赛博朋克，冷色光影",
  "scenes": 6
}
```
- 返回示例：
```json
{
  "task_id": "task_storyboard_001",
  "storyboard": [
    {
      "scene_id": "s1",
      "title": "荒城入口",
      "prompt": "cyberpunk ruined gate, neon mist, lone warrior",
      "narration": "他踏入荒城，霓虹被尘土掩埋。",
      "bgm": "low synth pad"
    }
  ]
}
```

### POST /frames
- 入参示例：
```json
{
  "storyboard": [
    {
      "scene_id": "s1",
      "prompt": "cyberpunk ruined gate, neon mist, lone warrior",
      "narration": "他踏入荒城，霓虹被尘土掩埋。"
    }
  ],
  "image_style": {
    "resolution": "768x512",
    "num_steps": 4,
    "cfg_scale": 1.5,
    "seed": 123
  }
}
```
- 返回示例：
```json
{
  "task_id": "task_frames_001",
  "frames": [
    {
      "scene_id": "s1",
      "frame": "/data/frames/s1.png"
    }
  ]
}
```

### POST /clips
- 入参示例：
```json
{
  "frames": [
    { "scene_id": "s1", "frame": "/data/frames/s1.png", "duration": 2.0, "transition": "crossfade" }
  ],
  "video": {
    "fps": 12,
    "resolution": "720p",
    "transition_duration": 0.6
  }
}
```
- 返回示例：
```json
{
  "task_id": "task_clips_001",
  "clips": [
    { "scene_id": "s1", "clip": "/data/clips/s1.mp4" }
  ]
}
```

### POST /narration
- 入参示例：
```json
{
  "lines": [
    { "scene_id": "s1", "text": "他踏入荒城，霓虹被尘土掩埋。" }
  ],
  "voice": "cosyvoice-mini",
  "speed": 1.0,
  "format": "wav"
}
```
- 返回示例：
```json
{
  "task_id": "task_tts_001",
  "audios": [
    { "scene_id": "s1", "audio": "/data/audio/s1.wav" }
  ]
}
```

### POST /render
- 功能：一键从故事文本到成片，内部顺序调用 storyboard → frames → clips → narration → 合成。
- 入参示例：
```json
{
  "story": "一位独行武者穿越废土城市寻找真相",
  "style": "赛博朋克",
  "options": {
    "scene_count": 6,
    "image": { "resolution": "768x512", "num_steps": 4 },
    "video": { "fps": 12, "resolution": "720p" },
    "voice": "cosyvoice-mini",
    "music": true
  }
}
```
- 返回示例：
```json
{
  "task_id": "task_render_001",
  "video": "/data/final/final.mp4"
}
```
- 状态查询：需搭配 `GET /tasks/{id}` 获取进度。

### GET /tasks/{id}
- 用于查询异步任务状态。
- 返回示例：
```json
{
  "task_id": "task_render_001",
  "status": "running",
  "progress": 0.42,
  "result": null,
  "error": null
}
```
- `status` 取值：`pending | running | done | error`；`result` 结构随任务类型返回。

## 错误码建议
- 400：参数缺失/格式错误。
- 404：任务不存在或资源未找到。
- 429：并发/队列繁忙，稍后重试。
- 500：内部错误；`error` 字段包含简要描述。

## 认证与限流（可选）
- 内网默认无鉴权；对公网可加简单 Token（Header `X-API-Key`）。
- 基于网关对接口做 QPS 限流，关键推理接口可按任务队列长度返回 429。 
