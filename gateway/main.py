"""Simple FastAPI gateway orchestrating storyboard -> frames -> clips -> narration -> final MP4."""

import asyncio
import json
import os
import subprocess
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Downstream service endpoints (can be overridden via env)
LLM_URL = os.getenv("LLM_URL", "http://127.0.0.1:8001/storyboard")
TXT2IMG_URL = os.getenv("TXT2IMG_URL", "http://127.0.0.1:8002/generate")
IMG2VID_URL = os.getenv("IMG2VID_URL", "http://127.0.0.1:8003/img2vid")
TTS_URL = os.getenv("TTS_URL", "http://127.0.0.1:8004/narration")
# Final outputs
FINAL_DIR = Path(os.getenv("FINAL_DIR", "data/final"))
TMP_DIR = FINAL_DIR / "tmp"
CLIPS_DIR = Path(os.getenv("CLIPS_DIR", "data/clips"))

# Task status constants (align with system spec)
TASK_STATUS_PENDING = "pending"
TASK_STATUS_BLOCKED = "blocked"
TASK_STATUS_PROCESSING = "processing"
TASK_STATUS_FINISHED = "finished"
TASK_STATUS_FAILED = "failed"
TASK_STATUS_CANCELLED = "cancelled"

# Task types
TASK_TYPE_STORYBOARD = "generate_storyboard"
TASK_TYPE_SHOT = "generate_shot"
TASK_TYPE_AUDIO = "generate_audio"
TASK_TYPE_VIDEO = "generate_video"

# Very small in-memory task store. For production replace with Redis/DB.
class TaskState(BaseModel):
    id: str
    project_id: Optional[str] = None
    type: Optional[str] = None
    status: str
    progress: int
    message: str = ""
    parameters: Optional[Dict] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    estimatedDuration: int = 0
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


tasks: Dict[str, TaskState] = {}
progress_subs: Dict[str, List[asyncio.Queue]] = defaultdict(list)


class RenderRequest(BaseModel):
    story: str = Field(..., description="故事文本")
    style: str = Field("", description="可选风格")
    scenes: int = Field(4, ge=1, le=20, description="分镜数量")
    width: int = Field(768, ge=256, le=2048)
    height: int = Field(512, ge=256, le=2048)
    img_steps: int = Field(4, ge=1, le=50)
    cfg_scale: float = Field(1.5, ge=0.0, le=20.0)
    fps: int = Field(12, ge=4, le=30)
    video_frames: int = Field(16, ge=8, le=64)
    speaker: Optional[str] = Field(None, description="TTS 说话人")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="TTS 语速")


class RenderResponse(BaseModel):
    job_id: str
    message: str = ""
    error: str = ""


# Schema matching Task in provided OpenAPI (response/GET)
class TaskSchema(BaseModel):
    id: str
    projectId: Optional[str] = None
    type: Optional[str] = None
    status: str
    progress: int
    message: str
    parameters: Dict = Field(default_factory=dict)
    result: Dict = Field(default_factory=dict)
    error: str = ""
    estimatedDuration: int = 0
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


def _as_task_schema(state: TaskState) -> TaskSchema:
    return TaskSchema(
        id=state.id,
        projectId=state.project_id,
        type=state.type,
        status=state.status,
        progress=state.progress,
        message=state.message,
        parameters=state.parameters or {},
        result=state.result or {},
        error=state.error or "",
        estimatedDuration=state.estimatedDuration,
        startedAt=state.startedAt,
        finishedAt=state.finishedAt,
        createdAt=state.createdAt,
        updatedAt=state.updatedAt,
    )

# ---- Compatible payload for /v1/api/generate (VI spec) ----
class ShotDefaults(BaseModel):
    shot_count: Optional[int] = None
    style: Optional[str] = None
    story_text: Optional[str] = Field(None, alias="storyText")


class ShotParam(BaseModel):
    transition: Optional[str] = None
    shot_id: Optional[str] = Field(None, alias="shotId")
    image_width: Optional[str] = None
    image_height: Optional[str] = None
    prompt: Optional[str] = None


class VideoParam(BaseModel):
    resolution: Optional[str] = None
    fps: Optional[int] = None
    format: Optional[str] = None
    bitrate: Optional[int] = None


class TTSParam(BaseModel):
    voice: Optional[str] = None
    lang: Optional[str] = None
    sample_rate: Optional[int] = None
    format: Optional[str] = None


class GenerateParameters(BaseModel):
    shot_defaults: Optional[ShotDefaults] = None
    shot: Optional[ShotParam] = None
    video: Optional[VideoParam] = None
    tts: Optional[TTSParam] = None


class GeneratePayload(BaseModel):
    id: Optional[str] = None
    project_id: Optional[str] = Field(None, alias="projectId")
    type: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    message: Optional[str] = None
    parameters: Optional[GenerateParameters] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    estimatedDuration: Optional[int] = None
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class TaskResponse(BaseModel):
    id: str
    status: str
    progress: int
    message: str = ""
    result: Optional[Dict] = None
    error: Optional[str] = None


app = FastAPI(title="StoryToVideo Gateway", version="0.1.0")
STATIC_ROOT = Path(os.getenv("STATIC_ROOT", "data")).resolve()
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=STATIC_ROOT), name="files")


@app.get("/health")
async def health() -> Dict[str, str]:
    return {
        "status": "ok",
        "llm": LLM_URL,
        "txt2img": TXT2IMG_URL,
        "img2vid": IMG2VID_URL,
        "tts": TTS_URL,
    }


async def _call_json_api(client: httpx.AsyncClient, url: str, payload: Dict, timeout: float = 600.0) -> Dict:
    resp = await client.post(url, json=payload, timeout=timeout)
    if resp.status_code >= 400:
        raise HTTPException(status_code=500, detail=f"API {url} failed: {resp.status_code} {resp.text}")
    try:
        return resp.json()
    except json.JSONDecodeError as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"API {url} returned non-JSON: {resp.text}") from exc


def _run_ffmpeg(cmd: List[str], desc: str) -> None:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{desc} failed: {proc.stderr.strip()}")


def _update_task(task_id: str, **kwargs) -> None:
    state = tasks.get(task_id)
    if not state:
        return
    for k, v in kwargs.items():
        setattr(state, k, v)
    state.updatedAt = datetime.utcnow().isoformat()
    tasks[task_id] = state
    if progress_subs.get(task_id):
        payload = _as_task_schema(state).dict(exclude_none=True)
        for q in list(progress_subs[task_id]):
            try:
                q.put_nowait(payload)
            except Exception:
                pass


def _frame_to_video_fallback(frame_path: str, scene_id: str, fps: int, num_frames: int) -> Path:
    """If img2vid service is slow/unavailable, fallback to a static video via ffmpeg."""
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    out = CLIPS_DIR / f"{scene_id}_fallback.mp4"
    duration = max(num_frames / max(fps, 1), 0.5)
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-t",
        f"{duration:.2f}",
        "-i",
        frame_path,
        "-vf",
        f"fps={fps}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out),
    ]
    _run_ffmpeg(cmd, f"fallback video for {scene_id}")
    return out


async def _task_event_stream(task_id: str):
    queue: asyncio.Queue = asyncio.Queue()
    progress_subs[task_id].append(queue)
    # push current state immediately if exists
    current = tasks.get(task_id)
    if current:
        await queue.put(_as_task_schema(current).dict(exclude_none=True))
    try:
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {json.dumps(data)}\n\n"
            except asyncio.TimeoutError:
                # keep-alive ping
                yield "event: ping\ndata: {}\n\n"
    finally:
        if queue in progress_subs.get(task_id, []):
            progress_subs[task_id].remove(queue)


async def _orchestrate(task_id: str, task_type: str, ctx: Dict) -> None:
    _update_task(
        task_id,
        status=TASK_STATUS_PROCESSING,
        progress=1,
        message="Start pipeline",
        startedAt=datetime.utcnow().isoformat(),
    )
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Helper to keep code compact
    render_req: RenderRequest = ctx.get("render_req")  # may be None for non-video tasks
    prompt_text: str = ctx.get("prompt_text") or ""
    story: str = ctx.get("story") or ""
    style: str = ctx.get("style") or ""
    scenes: int = ctx.get("scenes") or 1

    try:
        # --- Storyboard only ---
        if task_type == TASK_TYPE_STORYBOARD:
            async with httpx.AsyncClient() as client:
                payload_sb = {"story": story, "style": style, "scenes": scenes}
                sb_data = await _call_json_api(client, LLM_URL, payload_sb)
            storyboard = sb_data.get("storyboard") or sb_data.get("shots") or []
            _update_task(
                task_id,
                status=TASK_STATUS_FINISHED,
                progress=100,
                message="storyboard done",
                result={"storyboard": storyboard},
                finishedAt=datetime.utcnow().isoformat(),
            )
            return

        # --- Shot (txt2img) only ---
        if task_type == TASK_TYPE_SHOT:
            async with httpx.AsyncClient() as client:
                payload_img = {
                    "prompt": prompt_text or story,
                    "scene_id": "s1",
                    "style": {
                        "width": render_req.width if render_req else 768,
                        "height": render_req.height if render_req else 512,
                        "num_inference_steps": render_req.img_steps if render_req else 4,
                        "guidance_scale": render_req.cfg_scale if render_req else 1.5,
                    },
                }
                img_data = await _call_json_api(client, TXT2IMG_URL, payload_img)
            images = img_data.get("images") or []
            _update_task(
                task_id,
                status=TASK_STATUS_FINISHED,
                progress=100,
                message="shot done",
                result={"images": images},
                finishedAt=datetime.utcnow().isoformat(),
            )
            return

        # --- Audio (tts) only ---
        if task_type == TASK_TYPE_AUDIO:
            text = prompt_text or story
            async with httpx.AsyncClient() as client:
                payload_tts = {
                    "lines": [{"scene_id": "s1", "text": text}],
                    "speaker": ctx.get("speaker"),
                    "speed": ctx.get("speed") or 1.0,
                }
                tts_data = await _call_json_api(client, TTS_URL, payload_tts)
            audios = tts_data.get("audios") or []
            _update_task(
                task_id,
                status=TASK_STATUS_FINISHED,
                progress=100,
                message="audio done",
                result={"audios": audios},
                finishedAt=datetime.utcnow().isoformat(),
            )
            return

        # --- Full video pipeline (default) ---
        req = render_req
        async with httpx.AsyncClient() as client:
            # 1) Storyboard
            payload_sb = {"story": req.story, "style": req.style, "scenes": req.scenes}
            sb_data = await _call_json_api(client, LLM_URL, payload_sb)
            storyboard = sb_data.get("storyboard") or sb_data.get("shots")
            if not storyboard:
                raise RuntimeError("Storyboard empty")
            _update_task(task_id, progress=10, message="Storyboard ready")

            # 2) TXT2IMG
            frames: List[Dict] = []
            for idx, item in enumerate(storyboard):
                scene_id = item.get("scene_id") or item.get("id") or f"s{idx+1}"
                prompt = item.get("prompt") or item.get("description") or ""
                payload_img = {
                    "prompt": prompt,
                    "scene_id": scene_id,
                    "style": {
                        "width": req.width,
                        "height": req.height,
                        "num_inference_steps": req.img_steps,
                        "guidance_scale": req.cfg_scale,
                    },
                }
                img_data = await _call_json_api(client, TXT2IMG_URL, payload_img)
                images = img_data.get("images") or []
                if not images:
                    raise RuntimeError(f"No image for scene {scene_id}")
                frames.append({"scene_id": scene_id, "path": images[0]["path"]})
                _update_task(task_id, progress=20 + int(20 * (idx + 1) / len(storyboard)), message=f"Images {idx+1}/{len(storyboard)}")

            # 3) IMG2VID
            clips: List[Dict] = []
            for idx, frame in enumerate(frames):
                payload_vid = {
                    "frame": frame["path"],
                    "scene_id": frame["scene_id"],
                    "fps": req.fps,
                    "num_frames": req.video_frames,
                }
                try:
                    vid_data = await _call_json_api(
                        client,
                        IMG2VID_URL,
                        payload_vid,
                        timeout=float(os.getenv("IMG2VID_TIMEOUT", "120")),
                    )
                    video = vid_data.get("video")
                    if not video:
                        raise RuntimeError(f"No video for scene {frame['scene_id']}")
                except Exception:
                    # Fallback: generate static video locally to keep pipeline moving.
                    video = str(_frame_to_video_fallback(frame["path"], frame["scene_id"], req.fps, req.video_frames))
                clips.append({"scene_id": frame["scene_id"], "video": video})
                _update_task(task_id, progress=40 + int(20 * (idx + 1) / len(frames)), message=f"Videos {idx+1}/{len(frames)}")

            # 4) TTS
            lines = [{"scene_id": item.get("scene_id") or item.get("id") or f"s{idx+1}", "text": item.get("narration") or item.get("prompt") or ""} for idx, item in enumerate(storyboard)]
            payload_tts = {"lines": lines, "speaker": req.speaker or None, "speed": req.speed}
            tts_data = await _call_json_api(client, TTS_URL, payload_tts)
            audios = tts_data.get("audios") or []
            if len(audios) != len(lines):
                raise RuntimeError("TTS count mismatch")
            audio_map = {a["scene_id"]: a for a in audios}
            _update_task(task_id, progress=70, message="TTS ready")

        # 5) Mux clips and audio
        muxed: List[Path] = []
        for idx, clip in enumerate(clips):
            scene_id = clip["scene_id"]
            audio = audio_map.get(scene_id)
            if not audio:
                raise RuntimeError(f"Missing audio for scene {scene_id}")
            out_clip = TMP_DIR / f"{scene_id}_mux.mp4"
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                clip["video"],
                "-i",
                audio["audio"],
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
                str(out_clip),
            ]
            await asyncio.to_thread(_run_ffmpeg, cmd, f"mux {scene_id}")
            muxed.append(out_clip)
            _update_task(task_id, progress=75 + int(15 * (idx + 1) / len(clips)), message=f"Mux {idx+1}/{len(clips)}")

        # 6) Concat
        list_file = TMP_DIR / f"concat_{task_id}.txt"
        with list_file.open("w", encoding="utf-8") as f:
            for path in muxed:
                f.write(f"file '{path.resolve().as_posix()}'\n")
        final_path = FINAL_DIR / f"final_{task_id}.mp4"
        cmd_concat = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "main",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(final_path),
        ]
        await asyncio.to_thread(_run_ffmpeg, cmd_concat, "concat videos")

        _update_task(
            task_id,
            status=TASK_STATUS_FINISHED,
            progress=100,
            message="done",
            result={"video": str(final_path)},
            finishedAt=datetime.utcnow().isoformat(),
        )
    except Exception as exc:  # noqa: BLE001
        _update_task(
            task_id,
            status=TASK_STATUS_FAILED,
            message=f"failed: {exc}",
            error=str(exc),
        )


@app.post("/render", response_model=RenderResponse)
async def render(req: RenderRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    tasks[task_id] = TaskState(
        id=task_id,
        status=TASK_STATUS_PENDING,
        progress=0,
        message="queued",
        parameters={},
        result={},
        error="",
        createdAt=now,
        updatedAt=now,
        type=TASK_TYPE_VIDEO,
    )
    background_tasks.add_task(
        _orchestrate,
        task_id,
        TASK_TYPE_VIDEO,
        {
            "render_req": req,
            "story": req.story,
            "style": req.style,
            "scenes": req.scenes,
            "prompt_text": "",
            "speaker": req.speaker,
            "speed": req.speed,
        },
    )
    return RenderResponse(job_id=task_id, message="accepted", error="")


@app.post("/v1/api/generate", response_model=RenderResponse)
async def generate_vi(req: GeneratePayload, background_tasks: BackgroundTasks):
    params = req.parameters or GenerateParameters()
    shot_defaults = params.shot_defaults or ShotDefaults()
    shot = params.shot or ShotParam()
    video = params.video or VideoParam()
    tts = params.tts or TTSParam()

    # Map incoming payload to internal RenderRequest
    story = shot_defaults.story_text or shot.prompt or req.message or "story"
    style = shot_defaults.style or ""
    scenes = shot_defaults.shot_count or 1
    prompt_text = shot.prompt or shot_defaults.story_text or req.message or story

    def _to_int(val: Optional[str], default: int) -> int:
        try:
            return int(val) if val is not None else default
        except Exception:
            return default

    width = _to_int(shot.image_width, 768)
    height = _to_int(shot.image_height, 512)
    fps = video.fps or 12
    render_req = RenderRequest(
        story=story,
        style=style,
        scenes=scenes,
        width=width,
        height=height,
        img_steps=4,
        cfg_scale=1.5,
        fps=fps,
        video_frames=16,
        speaker=tts.voice,
        speed=1.0,
    )
    task_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    tasks[task_id] = TaskState(
        id=task_id,
        project_id=req.project_id,
        type=req.type or TASK_TYPE_VIDEO,
        status=TASK_STATUS_PENDING,
        progress=0,
        message=req.message or "queued",
        parameters=params.model_dump(by_alias=True, exclude_none=True) if hasattr(params, "model_dump") else {},
        result=req.result or {},
        error=req.error or "",
        estimatedDuration=req.estimatedDuration or 0,
        createdAt=now,
        updatedAt=now,
    )
    background_tasks.add_task(
        _orchestrate,
        task_id,
        req.type or TASK_TYPE_VIDEO,
        {
            "render_req": render_req,
            "story": story,
            "style": style,
            "scenes": scenes,
            "speaker": tts.voice,
            "speed": 1.0,
        },
    )
    return RenderResponse(job_id=task_id, message="accepted", error="")


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def task_status(task_id: str):
    state = tasks.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="task not found")
    return state


@app.get("/tasks/{task_id}/stream")
async def task_stream(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="task not found")
    return StreamingResponse(_task_event_stream(task_id), media_type="text/event-stream")


@app.get("/v1/api/jobs/{job_id}", response_model=TaskSchema)
async def job_status(job_id: str):
    state = tasks.get(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="task not found")
    return _as_task_schema(state)


@app.delete("/v1/api/jobs/{job_id}")
async def stop_job(job_id: str):
    state = tasks.get(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="task not found")
    now = datetime.utcnow().isoformat()
    _update_task(job_id, status=TASK_STATUS_CANCELLED, message="stopped by user", finishedAt=now)
    return {}


# CLI entry: uvicorn gateway.main:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("gateway.main:app", host="0.0.0.0", port=8000, reload=False)
