# Model Node API Documentation

This document specifies the HTTP API exposed by the model node FastAPI service. All endpoints are JSON-based and designed to be wired to real pipelines (Qwen/Ollama, Stable Diffusion Turbo, Stable-Video-Diffusion-Img2Vid, CosyVoice-mini).

## General
- **Base URL (default docker compose)**: `http://localhost:8000`
- **Content type**: `application/json`
- **Authentication**: not required in the sample; add gateway/token in production.
- **Swagger UI**: `GET /docs`
- **OpenAPI JSON**: `GET /openapi.json`

## Health
- **Endpoint**: `GET /health`
- **Purpose**: Liveness/readiness signal.
- **Response**
  ```json
  {
    "status": "ok",
    "ts": "2024-07-01T10:00:00.000000"
  }
  ```

## Storyboard (LLM)
- **Endpoint**: `POST /llm/storyboard`
- **Description**: Convert a free-form story into structured shots.
- **Request body**
  ```json
  {
    "story": "夕阳下的海边散步",
    "style": "pixar"
  }
  ```
  - `story` (string, required): user story text.
  - `style` (string, optional): tone/visual hint.
- **Response 200**
  ```json
  {
    "shots": [
      {
        "title": "自动生成分镜",
        "prompt": "pixar | 夕阳下的海边散步",
        "narration": "夕阳下的海边散步",
        "bgm": "lofi-chill"
      }
    ],
    "generated_at": "2024-07-01T10:00:00.123456"
  }
  ```

## Text-to-Image
- **Endpoint**: `POST /sd_generate`
- **Description**: Generate a keyframe image from a prompt.
- **Request body**
  ```json
  {
    "prompt": "sunset beach cinematic",
    "style": "anime",
    "width": 1024,
    "height": 576
  }
  ```
  - `prompt` (string, required): image description.
  - `style` (string, optional): style preset/tag.
  - `width` (int, optional, default 1024)
  - `height` (int, optional, default 576)
- **Response 200**
  ```json
  {
    "url": "https://example.com/keyframe.png",
    "note": "Requested 1024x576 image in style=anime"
  }
  ```

## Image-to-Video (optional)
- **Endpoint**: `POST /img2vid`
- **Description**: Turn a keyframe into a short clip.
- **Request body**
  ```json
  {
    "image_url": "https://example.com/keyframe.png",
    "duration_seconds": 3.0,
    "transition": "dissolve"
  }
  ```
  - `image_url` (string, required): source frame.
  - `duration_seconds` (float, optional, default 3.0): clip length.
  - `transition` (string, optional): e.g., `dissolve`, `zoom`, `cut`.
- **Response 200**
  ```json
  {
    "url": "https://example.com/clip.mp4",
    "note": "duration=3.0s transition=dissolve"
  }
  ```

## Text-to-Speech
- **Endpoint**: `POST /tts`
- **Description**: Generate narration audio for a shot.
- **Request body**
  ```json
  {
    "text": "欢迎使用 StoryToVideo",
    "voice": "female"
  }
  ```
  - `text` (string, required): narration text.
  - `voice` (string, optional): speaker/voice style.
- **Response 200**
  ```json
  {
    "url": "https://example.com/narration.wav",
    "note": "voice=female"
  }
  ```

## Error model
- **Status codes**: `200` on success. FastAPI will emit `422` for validation errors.
- **Example 422 response**
  ```json
  {
    "detail": [
      {
        "loc": ["body", "story"],
        "msg": "Field required",
        "type": "value_error.missing"
      }
    ]
  }
  ```

## Quick smoke tests
- Health: `curl http://localhost:8000/health`
- Storyboard: `curl -X POST http://localhost:8000/llm/storyboard -H "Content-Type: application/json" -d '{"story":"夕阳下的海边散步","style":"pixar"}'`
- Text-to-Image: `curl -X POST http://localhost:8000/sd_generate -H "Content-Type: application/json" -d '{"prompt":"sunset beach cinematic","style":"anime"}'`
- Img2Vid: `curl -X POST http://localhost:8000/img2vid -H "Content-Type: application/json" -d '{"image_url":"https://example.com/keyframe.png"}'`
- TTS: `curl -X POST http://localhost:8000/tts -H "Content-Type: application/json" -d '{"text":"欢迎使用 StoryToVideo"}'`
