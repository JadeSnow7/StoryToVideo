# API Draft (MVP) / API 草案（MVP）

Base URL: `/v1` / 基础路径：`/v1`

## Conventions / 约定
- Auth: Bearer Token（后续可换 JWT/OAuth2）。/ 认证：Bearer Token。
- Content-Type: `application/json`
- Status enum: `PENDING` | `RUNNING` | `SUCCESS` | `FAILED` （含 `error` 字段）。/ 状态枚举。
- Pagination: `page`, `page_size`（可选）。/ 可选分页。

## Entities / 数据结构
- Project: `{ id, title, story_text?, style, created_at, cover_url?, status }`
- Shot: `{ id, project_id, order, prompt, narration, transition?, image_url?, video_url?, status, task_id? }`
- Task: `{ id, type (LLM|SD|TTS|SVD), status, progress, result, error }`

## Project / 项目
- POST `/projects/create`  
  Request: `{ title: string, story_text: string, style: "Cinematic"|"Anime"|"Realistic" }`  
  Response: `{ project_id, storyboard: Shot[] }`

- GET `/projects`  
  Query: `q` (title), `sort` (created_at desc/default)  
  Response: `{ items: Project[] }`

- GET `/projects/{id}/storyboard`  
  Response: `{ project_id, shots: Shot[] }`

## Shot / 分镜
- POST `/shots/{id}/update_prompt`  
  Request: `{ prompt?, narration?, transition? }`  
  Response: `Shot`

- POST `/shots/{id}/generate_image`  
  Request: `{ prompt?, style? }`  
  Response: `{ task_id }`

- POST `/shots/{id}/generate_video` (optional 可选)  
  Request: `{ image_url, transition? }`  
  Response: `{ task_id }`

## Tasks / 任务
- GET `/tasks/{task_id}/status`  
  Response: `Task`

- POST `/webhook/task_complete`  
  Request: `{ task_id, status, result_url?, error? }`  
  Response: `{ ok: true }`

## Auth (placeholder) / 鉴权（占位）
- POST `/auth/login` (mock)  
  Request: `{ username, password }`  
  Response: `{ token }`
- Header: `Authorization: Bearer <token>`

## Example payloads / 示例
### Create project / 新建项目
Request:
```json
{
  "title": "Moon Walk",
  "story_text": "A kid walks on the moon...",
  "style": "Cinematic"
}
```
Response:
```json
{
  "project_id": "abc-123",
  "storyboard": [
    { "id": "s1", "order": 0, "prompt": "Shot 1", "status": "PENDING" }
  ]
}
```

### Task status / 任务状态
Response:
```json
{
  "id": "t1",
  "type": "SD",
  "status": "RUNNING",
  "progress": 35,
  "result": null,
  "error": null
}
```
