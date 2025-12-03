# 流水线与数据流说明

## 总体流程
1) Storyboard：LLM 将故事文本+风格转分镜 JSON（含 scene_id、title、prompt、narration、bgm）。
2) Frames：文生图批量生成关键帧 PNG；支持分辨率、步数、CFG、seed。
3) Clips：按分镜顺序将关键帧转换为短视频片段，支持转场和持续时长。
4) Narration：TTS 将旁白文本生成音频，按 scene_id 对齐。
5) Render：编排层用 ffmpeg 拼接视频片段、叠加旁白（可附加 BGM），输出成片 MP4。
6) Tasks：所有耗时操作返回 `task_id`，状态在网关持久或内存表中维护。

## 数据结构约定
- Scene：
  - `scene_id`: `s1`, `s2`...
  - `title`: 场景标题
  - `prompt`: 文生图提示词
  - `narration`: 旁白文本
  - `bgm`: 可选 BGM 建议
- 图像文件：`/data/frames/{scene_id}.png`；可存对象存储，返回相对路径或 URL。
- 片段文件：`/data/clips/{scene_id}.mp4`；分辨率/帧率由请求参数决定。
- 音频文件：`/data/audio/{scene_id}.wav`（或 mp3）。
- 成片：`/data/final/final.mp4`（可带时间戳/uuid 命名，如 `final_<ts>.mp4`）。

## 任务与状态
- 任务表字段示例：`task_id`, `type`, `status`, `progress`, `payload`, `result`, `error`, `created_at`, `updated_at`。
- 状态机：`pending -> running -> done | error`；`progress` 0~1 浮点。
- 初期可用内存/JSON 文件持久；生产建议 Redis + Celery/RQ/Arq。
- 可选回调：在请求中传 `callback_url`，任务完成后网关 POST 回调。

## 并发与队列建议
- 文生图与图生视频需 GPU 资源；可设队列长度上限，超过返回 429。
- 文生图批量：可按场景并行（受显存限制），或串行减少 OOM 风险。
- 图生视频：显存占用大，建议单任务串行或按 GPU ID 分配。
- TTS：CPU/GPU 均可，通常可并发。

## 容错与重试
- 每个阶段失败时记录 error 与阶段名；`/render` 需在 `result` 中给出已完成的部分。
- 可选的阶段重试：允许用户带 `resume_from`，跳过已完成阶段（如 frames 已生成）。
- 输出文件路径需幂等：若任务重复执行，使用新的 task_id 和文件名，避免覆盖。

## 文件与命名规范
- 推荐使用 UUID 或时间戳避免冲突：`frames/{scene_id}_{taskid}.png`。
- 路径中仅使用小写、数字、下划线；不含空格。
- 若启用对象存储，路径保持与本地一致，上传后返回外链/签名 URL。

## 性能提示
- 文生图：使用 fp16；启用 `xformers`；将 `num_inference_steps` 控制在 4~8；CFG 低于 2 提速。
- 图生视频：控制分辨率（如 576p/720p）和帧数；必要时降帧率到 10~12fps。
- TTS：提前预热模型；旁白批量推理。
- ffmpeg：用 `-hwaccel cuda`（若支持）加速转码；合成时统一采样率/声道。
