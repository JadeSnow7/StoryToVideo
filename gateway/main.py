"""Simple FastAPI gateway orchestrating storyboard -> frames -> clips -> narration -> final MP4."""

import asyncio
import copy
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
STORYBOARD_DIR = Path(os.getenv("STORYBOARD_DIR", "data/storyboard"))

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
    shot_id: Optional[str] = None
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
# Very small in-memory project/shot store to satisfy spec endpoints
projects: Dict[str, Dict] = {}
project_shots: Dict[str, Dict[str, Dict]] = defaultdict(dict)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _make_shot(project_id: str, order: int, shot_id: Optional[str] = None, title: str = "", prompt: str = "", transition: str = "") -> Dict:
    shot_id = shot_id or str(uuid.uuid4())
    now = _now_iso()
    return {
        "id": shot_id,
        "projectId": project_id,
        "order": order,
        "title": title or f"Shot {order}",
        "description": "",
        "prompt": prompt or "",
        "negativePrompt": "",
        "narration": "",
        "bgm": "",
        "status": "created",
        "imagePath": "",
        "audioPath": "",
        "videoPath": "",
        "duration": 0.0,
        "transition": transition or "",
        "createdAt": now,
        "updatedAt": now,
    }


class RenderRequest(BaseModel):
    story: str = Field(..., description="故事文本")
    style: str = Field("", description="可选风格")
    scenes: int = Field(4, ge=1, le=20, description="分镜数量")
    width: int = Field(768, ge=256, le=2048)
    height: int = Field(512, ge=256, le=2048)
    img_steps: int = Field(4, ge=1, le=50)
    cfg_scale: float = Field(1.5, ge=0.0, le=20.0)
    images_per_scene: int = Field(1, ge=1, le=3, description="每个分镜生成的图片数量，取首张做视频，其余留作补充")
    fps: int = Field(12, ge=4, le=30)
    clip_seconds: float = Field(5.0, ge=1.0, le=30.0, description="单个分镜时长（秒）")
    video_frames: int = Field(60, ge=8, le=480, description="单个分镜帧数（优先于 clip_seconds）")
    speaker: Optional[str] = Field(None, description="TTS 说话人")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="TTS 语速")


class RenderResponse(BaseModel):
    job_id: str
    message: str = ""
    error: str = ""


class TaskShotParameters(BaseModel):
    style: str = ""
    text_llm: str = ""
    image_llm: str = ""
    generate_tts: bool = False
    shot_count: int = 0
    image_width: int = 0
    image_height: int = 0


class TaskVideoParameters(BaseModel):
    format: str = ""
    resolution: str = ""
    fps: str = ""
    transition_effects: str = ""


class TaskParameters(BaseModel):
    shot: TaskShotParameters = Field(default_factory=TaskShotParameters)
    video: TaskVideoParameters = Field(default_factory=TaskVideoParameters)


class TaskShotsResult(BaseModel):
    generated_shots: List[Dict] = Field(default_factory=list)
    total_shots: int = 0
    total_time: float = 0.0


class TaskAudioResult(BaseModel):
    generated_audios: List[Dict] = Field(default_factory=list)
    total_audios: int = 0
    total_time: float = 0.0


class TaskVideoResult(BaseModel):
    path: str = ""
    duration: str = ""
    fps: str = ""
    resolution: str = ""
    format: str = ""
    total_time: str = ""
    clips: List[Dict] = Field(default_factory=list)


class TaskResult(BaseModel):
    task_shots: TaskShotsResult = Field(default_factory=TaskShotsResult)
    task_audio: TaskAudioResult = Field(default_factory=TaskAudioResult)
    task_video: TaskVideoResult = Field(default_factory=TaskVideoResult)


class ShotSchema(BaseModel):
    id: str
    projectId: str
    order: int
    title: str
    description: str = ""
    prompt: str = ""
    negativePrompt: str = ""
    narration: str = ""
    bgm: str = ""
    status: str = "created"
    imagePath: str = ""
    audioPath: str = ""
    videoPath: str = ""
    duration: float = 0.0
    transition: str = ""
    createdAt: str
    updatedAt: str


# Schema matching Task in provided OpenAPI (response/GET)
class TaskSchema(BaseModel):
    id: str
    projectId: Optional[str] = None
    shotId: Optional[str] = None
    type: Optional[str] = None
    status: str
    progress: int
    message: str
    parameters: TaskParameters = Field(default_factory=TaskParameters)
    result: Dict = Field(default_factory=dict)
    error: str = ""
    estimatedDuration: int = 0
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


def _deep_merge_dict(base: Dict, updates: Dict) -> Dict:
    if hasattr(base, "model_dump"):
        base = base.model_dump()
    if hasattr(updates, "model_dump"):
        updates = updates.model_dump()
    merged = copy.deepcopy(base if isinstance(base, dict) else {})
    if not isinstance(updates, dict):
        return merged
    for key, val in updates.items():
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged.get(key, {}), val)
        else:
            merged[key] = val
    return merged


def _default_parameters() -> Dict:
    return {
        "shot": {
            "style": "",
            "text_llm": "",
            "image_llm": "",
            "generate_tts": False,
            "shot_count": 0,
            "image_width": 0,
            "image_height": 0,
        },
        "video": {
            "format": "",
            "resolution": "",
            "fps": "",
            "transition_effects": "",
        },
    }


def _default_result() -> Dict:
    return {
        "resource_type": "",
        "resource_id": "",
        "resource_url": "",
        "resources": [],
        "legacy": {
            "task_shots": {"generated_shots": [], "total_shots": 0, "total_time": 0.0},
            "task_audio": {"generated_audios": [], "total_audios": 0, "total_time": 0.0},
            "task_video": {"path": "", "duration": "", "fps": "", "resolution": "", "format": "", "total_time": "", "clips": []},
        },
    }


def _normalize_parameters(params: Optional[Dict]) -> Dict:
    return _deep_merge_dict(_default_parameters(), params or {})


def _normalize_result(result: Optional[Dict]) -> Dict:
    base = _default_result()
    if result is None:
        return base
    merged = _deep_merge_dict(base, result)
    # Ensure required keys exist
    merged.setdefault("resources", [])
    merged.setdefault("legacy", _default_result().get("legacy", {}))
    return merged


def _as_task_schema(state: TaskState) -> TaskSchema:
    return TaskSchema(
        id=state.id,
        projectId=state.project_id,
        shotId=state.shot_id,
        type=state.type,
        status=state.status,
        progress=state.progress,
        message=state.message,
        parameters=_normalize_parameters(state.parameters),
        result=_normalize_result(state.result),
        error=state.error or "",
        estimatedDuration=state.estimatedDuration,
        startedAt=state.startedAt,
        finishedAt=state.finishedAt,
        createdAt=state.createdAt,
        updatedAt=state.updatedAt,
    )


# Build parameter payloads that align with server/gin-server/models/task.go
def _parameters_from_render(req: RenderRequest) -> Dict:
    return _normalize_parameters(
        {
            "shot": {
                "style": req.style or "",
                "shot_count": req.scenes,
                "image_count": req.images_per_scene,
                "image_width": req.width,
                "image_height": req.height,
            },
            "video": {
                "resolution": f"{req.width}x{req.height}",
                "fps": str(req.fps),
                "format": "mp4",
            },
        }
    )


def _parameters_from_generate(params: "GenerateParameters", shot_defaults: "ShotDefaults", shot: "ShotParam", video: "VideoParam", tts: "TTSParam") -> Dict:
    def _to_int(val: Optional[str], default: int) -> int:
        try:
            return int(val) if val is not None else default
        except Exception:
            return default

    width = _to_int(shot.image_width, 0)
    height = _to_int(shot.image_height, 0)
    resolution = video.resolution or (f"{width}x{height}" if width and height else "")
    fps_str = str(video.fps) if video.fps is not None else ""
    return _normalize_parameters(
        {
            "shot": {
                "style": shot_defaults.style or "",
                "shot_count": shot_defaults.shot_count or 0,
                "image_width": width,
                "image_height": height,
            },
            "video": {
                "format": video.format or "",
                "resolution": resolution,
                "fps": fps_str,
                "transition_effects": shot.transition or "",
            },
        }
    )


def _parameters_from_task_envelope(raw: Dict) -> Dict:
    shot_defaults = (raw.get("shot_defaults") if isinstance(raw, dict) else {}) or {}
    shot = (raw.get("shot") if isinstance(raw, dict) else {}) or {}
    video = (raw.get("video") if isinstance(raw, dict) else {}) or {}

    def _to_int(val: Optional[str], default: int) -> int:
        try:
            return int(val) if val not in (None, "") else default
        except Exception:
            return default

    width = _to_int(shot.get("image_width"), 0)
    height = _to_int(shot.get("image_height"), 0)
    resolution = video.get("resolution") or (f"{width}x{height}" if width and height else "")
    fps_raw = video.get("fps")
    fps = str(fps_raw) if fps_raw not in (None, "") else ""
    style = shot.get("style") or shot_defaults.get("style") or ""
    shot_count = shot_defaults.get("shot_count") or shot_defaults.get("shotCount") or 0
    return _normalize_parameters(
        {
            "shot": {
                "style": style,
                "text_llm": shot.get("text_llm", ""),
                "image_llm": shot.get("image_llm", ""),
                "generate_tts": bool(shot.get("generate_tts")) if isinstance(shot, dict) and "generate_tts" in shot else False,
                "shot_count": shot_count,
                "image_width": width,
                "image_height": height,
            },
            "video": {
                "format": video.get("format", ""),
                "resolution": resolution,
                "fps": fps,
                "transition_effects": shot.get("transition", ""),
            },
        }
    )

# ---- Compatible payload for /v1/generate (VI spec) ----
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
    format: Optional[str] = Field("wav", description="audio format")  # spec requires format


class GenerateTaskPayload(BaseModel):
    task: Dict


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


def _to_file_url(path: str) -> str:
    """Convert a local path to /files/... url if under STATIC_ROOT, else return posix path."""
    if not path:
        return ""
    p = Path(path).resolve()
    try:
        rel = p.relative_to(STATIC_ROOT)
        return f"/files/{rel.as_posix()}"
    except Exception:
        return p.as_posix()


def _resource(url: str, rtype: str, rid: Optional[str] = None, meta: Optional[Dict] = None) -> Dict:
    rid_val = rid or Path(url).stem if url else (rid or str(uuid.uuid4()))
    res = {"resource_type": rtype, "resource_id": rid_val, "resource_url": url}
    if meta:
        res["meta"] = meta
    return res


def _update_task(task_id: str, **kwargs) -> None:
    state = tasks.get(task_id)
    if not state:
        return
    if "parameters" in kwargs:
        raw_params = kwargs.pop("parameters")
        state.parameters = _normalize_parameters(_deep_merge_dict(state.parameters or _default_parameters(), raw_params or {}))
    if "result" in kwargs:
        raw_result = kwargs.pop("result")
        state.result = _normalize_result(_deep_merge_dict(state.result or _default_result(), raw_result or {}))
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


def _compute_clip_frames(req: RenderRequest) -> int:
    """Determine how many frames to request per clip, favoring duration when provided."""
    fps = max(req.fps, 1)
    frames_from_duration = int(fps * (getattr(req, "clip_seconds", 0) or 0))
    num_frames = req.video_frames or 0
    if frames_from_duration > 0:
        num_frames = max(num_frames, frames_from_duration)
    if num_frames <= 0:
        num_frames = fps * 5  # sensible default ~5s
    return max(num_frames, 8)


def _save_storyboard(task_id: str, storyboard: List[Dict]) -> str:
    STORYBOARD_DIR.mkdir(parents=True, exist_ok=True)
    path = STORYBOARD_DIR / f"storyboard_{task_id}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(storyboard, f, ensure_ascii=False, indent=2)
    return str(path)


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
    STORYBOARD_DIR.mkdir(parents=True, exist_ok=True)

    # Helper to keep code compact
    render_req: RenderRequest = ctx.get("render_req")  # may be None for non-video tasks
    prompt_text: str = ctx.get("prompt_text") or ""
    story: str = ctx.get("story") or ""
    style: str = ctx.get("style") or ""
    scenes: int = ctx.get("scenes") or 1
    resources: List[Dict] = []
    legacy = copy.deepcopy(_default_result().get("legacy", {}))

    try:
        # --- Storyboard only ---
        if task_type == TASK_TYPE_STORYBOARD:
            async with httpx.AsyncClient() as client:
                payload_sb = {"story": story, "style": style, "scenes": scenes}
                sb_data = await _call_json_api(client, LLM_URL, payload_sb)
            storyboard = sb_data.get("storyboard") or sb_data.get("shots") or []
            sb_path = _save_storyboard(task_id, storyboard)
            sb_res = _resource(_to_file_url(sb_path), "storyboard", f"sb_{task_id}")
            resources.append(sb_res)
            legacy["storyboard"] = storyboard
            _update_task(
                task_id,
                status=TASK_STATUS_FINISHED,
                progress=100,
                message="storyboard done",
                result={"resource_type": "storyboard", "resource_id": sb_res["resource_id"], "resource_url": sb_res["resource_url"], "resources": resources, "legacy": legacy},
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
            img_resources = []
            for img in images:
                url = _to_file_url(img.get("path") or img.get("url") or img.get("image") or "")
                img_resources.append(_resource(url, "image", img.get("scene_id") or "s1", meta={"raw": img}))
            primary_res = img_resources[0] if img_resources else _resource("", "image", "s1")
            _update_task(
                task_id,
                status=TASK_STATUS_FINISHED,
                progress=100,
                message="shot done",
                result={
                    "resource_type": primary_res["resource_type"],
                    "resource_id": primary_res["resource_id"],
                    "resource_url": primary_res["resource_url"],
                    "resources": img_resources,
                    "legacy": {"task_shots": {"generated_shots": images, "total_shots": len(images), "total_time": 0.0}},
                },
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
            audio_resources = []
            for a in audios:
                url = _to_file_url(a.get("audio") or a.get("path") or a.get("url") or "")
                audio_resources.append(_resource(url, "audio", a.get("scene_id") or "s1", meta={"raw": a}))
            primary_res = audio_resources[0] if audio_resources else _resource("", "audio", "s1")
            _update_task(
                task_id,
                status=TASK_STATUS_FINISHED,
                progress=100,
                message="audio done",
                result={
                    "resource_type": primary_res["resource_type"],
                    "resource_id": primary_res["resource_id"],
                    "resource_url": primary_res["resource_url"],
                    "resources": audio_resources,
                    "legacy": {"task_audio": {"generated_audios": audios, "total_audios": len(audios), "total_time": 0.0}},
                },
                finishedAt=datetime.utcnow().isoformat(),
            )
            return

        # --- Full video pipeline (default) ---
        req = render_req
        clip_frames = _compute_clip_frames(req)
        async with httpx.AsyncClient() as client:
            # 1) Storyboard
            payload_sb = {"story": req.story, "style": req.style, "scenes": req.scenes}
            sb_data = await _call_json_api(client, LLM_URL, payload_sb)
            storyboard = sb_data.get("storyboard") or sb_data.get("shots")
            if not storyboard:
                raise RuntimeError("Storyboard empty")
            if len(storyboard) < req.scenes:
                # Pad storyboard to requested scene count to keep downstream stages aligned
                base_prompt = req.story
                last_item = storyboard[-1] if storyboard else {"prompt": base_prompt}
                for extra_idx in range(len(storyboard), req.scenes):
                    storyboard.append(
                        {
                            "id": f"s{extra_idx+1}",
                            "prompt": last_item.get("prompt") or base_prompt,
                            "description": last_item.get("description") or "",
                            "narration": last_item.get("narration") or base_prompt,
                            "title": last_item.get("title") or f"Shot {extra_idx+1}",
                        }
                    )
            scene_assets: List[Dict] = []
            sb_path = _save_storyboard(task_id, storyboard)
            sb_res = _resource(_to_file_url(sb_path), "storyboard", f"sb_{task_id}")
            resources.append(sb_res)
            legacy["storyboard"] = storyboard
            for idx, item in enumerate(storyboard):
                scene_id = item.get("scene_id") or item.get("id") or f"s{idx+1}"
                base_prompt = item.get("prompt") or item.get("description") or ""
                styled_prompt = f"{req.style}, {base_prompt}" if req.style else base_prompt
                narration_text = item.get("narration") or item.get("text") or base_prompt
                if scene_assets:
                    prev_raw = scene_assets[-1].get("raw_prompt") or scene_assets[-1].get("prompt") or ""
                    continuity = f" 延续上一镜头的场景氛围：{prev_raw}"
                else:
                    continuity = ""
                scene_assets.append(
                    {
                        "scene_id": scene_id,
                        "order": idx + 1,
                        "title": item.get("title") or f"Shot {idx+1}",
                        "prompt": f"{styled_prompt}{continuity}",
                        "raw_prompt": base_prompt,
                        "description": item.get("description") or "",
                        "narration": narration_text,
                        "style": req.style,
                    }
                )
            legacy["task_shots"]["generated_shots"] = scene_assets
            legacy["task_shots"]["total_shots"] = len(scene_assets)
            _update_task(task_id, progress=10, message=f"Storyboard ready ({len(scene_assets)} shots)", result={"resources": resources, "legacy": legacy})

            # 2) TXT2IMG
            frames: List[Dict] = []
            for idx, scene in enumerate(scene_assets):
                scene_images: List[Dict] = []
                payload_img = {
                    "prompt": scene["prompt"],
                    "scene_id": scene["scene_id"],
                    "style": {
                        "width": req.width,
                        "height": req.height,
                        "num_inference_steps": req.img_steps,
                        "guidance_scale": req.cfg_scale,
                    },
                }
                for _ in range(max(req.images_per_scene, 1)):
                    img_data = await _call_json_api(client, TXT2IMG_URL, payload_img)
                    images = img_data.get("images") or []
                    if not images:
                        continue
                    image_path = images[0].get("path") or images[0].get("url") or images[0].get("image")
                    scene_images.append({"path": image_path, **images[0]})
                if not scene_images:
                    raise RuntimeError(f"No image for scene {scene['scene_id']}")
                primary = scene_images[0]
                frames.append({"scene_id": scene["scene_id"], "path": primary["path"]})
                scene_assets[idx]["image"] = primary
                scene_assets[idx]["image_path"] = primary["path"]
                scene_assets[idx]["images"] = scene_images
                for img in scene_images:
                    resources.append(_resource(_to_file_url(img.get("path") or ""), "image", scene["scene_id"], meta={"order": scene["order"], "raw": img}))
                legacy["task_shots"]["generated_shots"] = scene_assets
                legacy["task_shots"]["total_shots"] = len(scene_assets)
                _update_task(
                    task_id,
                    progress=20 + int(20 * (idx + 1) / len(scene_assets)),
                    message=f"Images {idx+1}/{len(scene_assets)}",
                    result={"resources": resources, "legacy": legacy},
                )

            # 3) IMG2VID
            clips: List[Dict] = []
            img2vid_max_frames = max(int(os.getenv("IMG2VID_MAX_FRAMES", "48")), 8)
            for idx, scene in enumerate(scene_assets):
                frame_path = scene.get("image_path") or next((f["path"] for f in frames if f["scene_id"] == scene["scene_id"]), "")
                frames_for_service = min(clip_frames, img2vid_max_frames)
                payload_vid = {
                    "frame": frame_path,
                    "scene_id": scene["scene_id"],
                    "fps": req.fps,
                    "num_frames": frames_for_service,
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
                        raise RuntimeError(f"No video for scene {scene['scene_id']}")
                except Exception:
                    # Fallback: generate static video locally to keep pipeline moving.
                    video = str(_frame_to_video_fallback(frame_path, scene["scene_id"], req.fps, frames_for_service))
                clips.append({"scene_id": scene["scene_id"], "video": video, "order": scene["order"], "frames": frames_for_service})
                scene_assets[idx]["video"] = video
                scene_assets[idx]["frames"] = frames_for_service
                resources.append(_resource(_to_file_url(video), "video_clip", scene["scene_id"], meta={"order": scene["order"], "frames": frames_for_service}))
                legacy["task_video"]["clips"] = clips
                legacy["task_video"]["fps"] = str(req.fps)
                legacy["task_video"]["resolution"] = f"{req.width}x{req.height}"
                legacy["task_video"]["format"] = "mp4"
                legacy["task_shots"]["generated_shots"] = scene_assets
                legacy["task_shots"]["total_shots"] = len(scene_assets)
                _update_task(
                    task_id,
                    progress=40 + int(20 * (idx + 1) / len(scene_assets)),
                    message=f"Videos {idx+1}/{len(scene_assets)}",
                    result={"resources": resources, "legacy": legacy},
                )

            # 4) TTS
            lines = [{"scene_id": scene["scene_id"], "text": scene.get("narration") or scene.get("prompt") or ""} for scene in scene_assets]
            payload_tts = {"lines": lines, "speaker": req.speaker or None, "speed": req.speed}
            tts_data = await _call_json_api(client, TTS_URL, payload_tts)
            audios = tts_data.get("audios") or []
            if len(audios) != len(lines):
                raise RuntimeError("TTS count mismatch")
            audio_map = {a["scene_id"]: a for a in audios}
            for idx, scene in enumerate(scene_assets):
                audio = audio_map.get(scene["scene_id"])
                if audio:
                    scene_assets[idx]["audio"] = audio
                    scene_assets[idx]["audio_path"] = audio.get("audio") or audio.get("path")
            for clip in clips:
                audio = audio_map.get(clip["scene_id"])
                if audio:
                    clip["audio"] = audio.get("audio") or audio.get("path")
            for a in audios:
                resources.append(_resource(_to_file_url(a.get("audio") or a.get("path") or ""), "audio", a.get("scene_id"), meta={"raw": a}))
            legacy["task_audio"]["generated_audios"] = audios
            legacy["task_audio"]["total_audios"] = len(audios)
            legacy["task_video"]["clips"] = clips
            legacy["task_shots"]["generated_shots"] = scene_assets
            _update_task(
                task_id,
                progress=70,
                message="TTS ready",
                result={"resources": resources, "legacy": legacy},
            )

        # 5) Mux clips and audio
        muxed: List[Path] = []
        for idx, clip in enumerate(clips):
            scene_id = clip["scene_id"]
            audio = audio_map.get(scene_id)
            if not audio:
                raise RuntimeError(f"Missing audio for scene {scene_id}")
            audio_path = clip.get("audio") or audio.get("audio") or audio.get("path") or audio.get("url")
            if not audio_path:
                raise RuntimeError(f"Missing audio path for scene {scene_id}")
            out_clip = TMP_DIR / f"{scene_id}_mux.mp4"
            # Keep per-clip duration (from frames/fps) for fades and audio padding
            clip_duration = max((clip.get("frames", clip_frames) or clip_frames) / max(req.fps, 1), 0.01)
            fade_out_start = max(clip_duration - 0.35, 0.0)
            vf_filter = f"format=yuv420p,fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out_start:.2f}:d=0.35"
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                clip["video"],
                "-i",
                audio_path,
                "-vf",
                vf_filter,
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-af",
                "apad",
                "-shortest",
                str(out_clip),
            ]
            await asyncio.to_thread(_run_ffmpeg, cmd, f"mux {scene_id}")
            muxed.append(out_clip)
            clip["mux"] = str(out_clip)
            for scene in scene_assets:
                if scene["scene_id"] == scene_id:
                    scene["mux"] = str(out_clip)
                    break
            resources.append(_resource(_to_file_url(str(out_clip)), "mux_video", scene_id, meta={"order": clip.get("order")}))
            legacy["task_video"]["clips"] = clips
            _update_task(
                task_id,
                progress=75 + int(15 * (idx + 1) / len(clips)),
                message=f"Mux {idx+1}/{len(clips)}",
                result={"resources": resources, "legacy": legacy},
            )

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

        total_duration_sec = round(sum(c.get("frames", clip_frames) for c in clips) / max(req.fps, 1), 2)
        final_url = _to_file_url(final_path)
        final_res = _resource(final_url, "video", task_id, meta={"duration": total_duration_sec})
        legacy["task_video"]["path"] = str(final_path)
        legacy["task_video"]["fps"] = str(req.fps)
        legacy["task_video"]["resolution"] = f"{req.width}x{req.height}"
        legacy["task_video"]["format"] = "mp4"
        legacy["task_video"]["duration"] = f"{total_duration_sec}s"
        legacy["task_video"]["total_time"] = f"{total_duration_sec}s"
        legacy["task_shots"]["generated_shots"] = scene_assets
        legacy["task_shots"]["total_shots"] = len(scene_assets)
        legacy["task_shots"]["total_time"] = total_duration_sec
        _update_task(
            task_id,
            status=TASK_STATUS_FINISHED,
            progress=100,
            message="done",
            result={
                "resource_type": "video",
                "resource_id": task_id,
                "resource_url": final_url,
                # Only return the final video in response; other assets remain accessible via their file URLs.
                "resources": [final_res],
                "legacy": legacy,
            },
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
        parameters=_parameters_from_render(req),
        result=_default_result(),
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


@app.post("/v1/generate", response_model=RenderResponse, tags=["v1"])
@app.post("/v1/generate", response_model=RenderResponse, include_in_schema=False) # Alias for backward compatibility
async def generate_vi(req: GeneratePayload, background_tasks: BackgroundTasks):
    params = req.parameters if req.parameters is not None else GenerateParameters()
    shot_defaults = params.shot_defaults or ShotDefaults()
    shot = params.shot or ShotParam()
    video = params.video or VideoParam()
    tts = params.tts or TTSParam()

    # Map incoming payload to internal RenderRequest
    story = shot_defaults.story_text or shot.prompt or req.message or "story"
    style = shot_defaults.style or ""
    prompt_text = shot.prompt or shot_defaults.story_text or req.message or story

    def _to_int(val: Optional[str], default: int) -> int:
        try:
            return int(val) if val is not None else default
        except Exception:
            return default

    def _clamp_int(val: Optional[int], default: int, min_val: int, max_val: int) -> int:
        num = _to_int(val, default)
        return max(min_val, min(max_val, num))

    scenes = _clamp_int(shot_defaults.shot_count, 1, 1, 20)
    width = _clamp_int(shot.image_width, 768, 256, 2048)
    height = _clamp_int(shot.image_height, 512, 256, 2048)
    fps = _clamp_int(video.fps, 12, 4, 30)
    clip_seconds = 5.0
    frames = max(int(fps * clip_seconds), 8)
    render_req = RenderRequest(
        story=story,
        style=style,
        scenes=scenes,
        width=width,
        height=height,
        img_steps=4,
        cfg_scale=1.5,
        fps=fps,
        clip_seconds=clip_seconds,
        video_frames=frames,
        speaker=tts.voice,
        speed=1.0,
    )
    task_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    normalized_params = _parameters_from_generate(params, shot_defaults, shot, video, tts)
    normalized_params["shot"]["shot_count"] = scenes
    normalized_params["shot"]["image_width"] = width
    normalized_params["shot"]["image_height"] = height
    normalized_params["video"]["fps"] = str(fps)
    normalized_params["video"]["resolution"] = f"{width}x{height}"
    tasks[task_id] = TaskState(
        id=task_id,
        project_id=req.project_id,
        shot_id=shot.shot_id,
        type=req.type or TASK_TYPE_VIDEO,
        status=TASK_STATUS_PENDING,
        progress=0,
        message=req.message or "queued",
        parameters=normalized_params,
        result=_normalize_result(req.result),
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
            "prompt_text": prompt_text,
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

# Spec-compatible task query
@app.get("/v1/tasks/{task_id}")
async def task_status_v1(task_id: str):
    state = tasks.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="task not found")
    return {"task": _as_task_schema(state)}


@app.get("/v1/jobs/{job_id}", response_model=TaskSchema)
@app.get("/v1/jobs/{job_id}", response_model=TaskSchema, include_in_schema=False) # Alias
async def job_status(job_id: str):
    state = tasks.get(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="task not found")
    return _as_task_schema(state)

@app.delete("/v1/jobs/{job_id}")
@app.delete("/v1/jobs/{job_id}", include_in_schema=False) # Alias
async def stop_job(job_id: str):
    state = tasks.get(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="task not found")
    now = _now_iso()
    _update_task(job_id, status=TASK_STATUS_CANCELLED, message="stopped by user", finishedAt=now)
    return {"success": True, "deleteAT": now, "error": ""}


# ---- Project & shot endpoints (spec stubs) ----
def _get_or_404_project(project_id: str) -> Dict:
    project = projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return project


def _recent_task_for_project(project_id: str) -> Dict:
    for t in tasks.values():
        if t.project_id == project_id:
            return _as_task_schema(t).dict()
    now = _now_iso()
    return {
        "id": str(uuid.uuid4()),
        "projectId": project_id,
        "shotId": "",
        "type": "",
        "status": TASK_STATUS_PENDING,
        "progress": 0,
        "message": "",
        "parameters": _default_parameters(),
        "result": _default_result(),
        "error": "",
        "estimatedDuration": 0,
        "startedAt": now,
        "finishedAt": now,
        "createdAt": now,
        "updatedAt": now,
    }


def _storyboard_to_shots(project_id: str, storyboard: List[Dict]) -> List[Dict]:
    """Convert LLM storyboard items into shot schema aligned with gin-server."""
    shots: List[Dict] = []
    for idx, scene in enumerate(storyboard):
        shot_id = scene.get("scene_id") or scene.get("id") or str(uuid.uuid4())
        now = _now_iso()
        shots.append(
            {
                "id": shot_id,
                "projectId": project_id,
                "order": idx + 1,
                "title": scene.get("title") or f"Shot {idx+1}",
                "description": scene.get("description") or "",
                "prompt": scene.get("prompt") or "",
                "negativePrompt": scene.get("negativePrompt") or "",
                "narration": scene.get("narration") or scene.get("voiceover") or "",
                "bgm": scene.get("bgm") or "",
                "status": "created",
                "imagePath": scene.get("imagePath") or "",
                "audioPath": scene.get("audioPath") or "",
                "videoPath": scene.get("videoPath") or "",
                "duration": float(scene.get("duration") or 0.0),
                "transition": scene.get("transition") or "",
                "createdAt": now,
                "updatedAt": now,
            }
        )
    return shots


@app.post("/v1/projects")
async def create_project(Title: Optional[str] = None, StoryText: Optional[str] = None, Style: Optional[str] = None):
    """
    注意：此接口仅用于测试/兼容目的。
    客户端应连接 Go Server (119.45.124.222:8080)，而非直接连接 Gateway。
    Gateway 主要用于服务端与 AI 模型之间的通信。
    """
    project_id = str(uuid.uuid4())
    now = _now_iso()
    shot_count = 5
    project = {
        "id": project_id,
        "title": Title or "",
        "storyText": StoryText or "",
        "style": Style or "",
        "status": "created",
        "coverImage": "",
        "duration": 0,
        "videoUrl": "",
        "description": "",
        "shotCount": shot_count,
        "createdAt": now,
        "updatedAt": now,
    }
    projects[project_id] = project
    shots: Dict[str, Dict] = {}
    for i in range(shot_count):
        shot = _make_shot(project_id, i + 1)
        shots[shot["id"]] = shot
    project_shots[project_id] = shots

    # 创建一个同步完成的分镜任务，便于客户端轮询 /v1/tasks/{id}
    storyboard_task_id = str(uuid.uuid4())
    shot_list = list(shots.values())
    task_result = _default_result()
    task_result["resource_type"] = "storyboard"
    task_result["resource_id"] = project_id
    task_result["legacy"]["task_shots"]["generated_shots"] = shot_list
    task_result["legacy"]["task_shots"]["total_shots"] = len(shot_list)
    task_result["legacy"]["task_shots"]["total_time"] = 0.0

    tasks[storyboard_task_id] = TaskState(
        id=storyboard_task_id,
        project_id=project_id,
        type=TASK_TYPE_STORYBOARD,
        status=TASK_STATUS_FINISHED,
        progress=100,
        message="storyboard ready",
        parameters=_default_parameters(),
        result=task_result,
        error="",
        startedAt=now,
        finishedAt=now,
        createdAt=now,
        updatedAt=now,
    )

    shot_task_ids = [str(uuid.uuid4()) for _ in range(shot_count)]
    return {"project_id": project_id, "shot_task_ids": shot_task_ids, "text_task_id": storyboard_task_id}


@app.put("/v1/projects/{project_id}")
async def update_project(project_id: str, Title: Optional[str] = None, Description: Optional[str] = None):
    project = _get_or_404_project(project_id)
    if Title is not None:
        project["title"] = Title
    if Description is not None:
        project["description"] = Description
    project["updatedAt"] = _now_iso()
    projects[project_id] = project
    return {"id": project_id, "updateAT": project["updatedAt"]}


@app.delete("/v1/projects/{project_id}")
async def delete_project(project_id: str):
    deleted = project_id in projects
    projects.pop(project_id, None)
    project_shots.pop(project_id, None)
    return {"success": deleted, "deleteAt": _now_iso(), "message": "deleted" if deleted else "not found"}


@app.get("/v1/projects/{project_id}")
async def get_project(project_id: str):
    project = _get_or_404_project(project_id)
    shots = list(project_shots.get(project_id, {}).values()) or None
    recent_task = _recent_task_for_project(project_id)
    project_detail = project.copy()
    project_detail["shotCount"] = len(project_shots.get(project_id, {}))
    return {
        "project_detail": project_detail,
        "recent_task": recent_task,
        "shots": shots,
    }


@app.get("/v1/projects/{project_id}/shots")
async def list_shots(project_id: str):
    _get_or_404_project(project_id)
    shots = list(project_shots.get(project_id, {}).values())
    return {"project_id": project_id, "total_shots": len(shots), "shots": shots}


@app.post("/v1/projects/{project_id}/shots/{shot_id}")
async def update_shot(project_id: str, shot_id: str, background_tasks: BackgroundTasks, title: Optional[str] = None, prompt: Optional[str] = None, transition: Optional[str] = None):
    _get_or_404_project(project_id)
    shots = project_shots[project_id]
    if shot_id not in shots:
        shots[shot_id] = _make_shot(project_id, len(shots) + 1, shot_id=shot_id)
    shot = shots[shot_id]
    if title is not None:
        shot["title"] = title
    if prompt is not None:
        shot["prompt"] = prompt
    if transition is not None:
        shot["transition"] = transition
    shot["updatedAt"] = _now_iso()
    shots[shot_id] = shot
    
    # 创建任务记录
    task_id = str(uuid.uuid4())
    now = _now_iso()
    tasks[task_id] = TaskState(
        id=task_id,
        project_id=project_id,
        shot_id=shot_id,
        type=TASK_TYPE_SHOT,
        status=TASK_STATUS_PENDING,
        progress=0,
        message="shot update task created",
        createdAt=now,
        updatedAt=now,
    )
    
    # 模拟后台处理
    async def mock_shot_task():
        import asyncio
        await asyncio.sleep(1)
        if task_id in tasks:
            tasks[task_id].status = TASK_STATUS_PROCESSING
            tasks[task_id].progress = 50
            tasks[task_id].message = "generating image..."
            tasks[task_id].updatedAt = _now_iso()
        await asyncio.sleep(1)
        if task_id in tasks:
            tasks[task_id].status = TASK_STATUS_FINISHED
            tasks[task_id].progress = 100
            tasks[task_id].message = "shot ready"
            tasks[task_id].result = {
                "resource_type": "shot",
                "resource_id": shot_id,
                "image_url": f"/files/shots/{shot_id}.png",
            }
            tasks[task_id].updatedAt = _now_iso()
            tasks[task_id].finishedAt = _now_iso()
    
    background_tasks.add_task(mock_shot_task)
    return {"shot_id": shot_id, "task_id": task_id, "message": "updated"}


@app.get("/v1/projects/{project_id}/shots/{shot_id}")
async def get_shot(project_id: str, shot_id: str):
    _get_or_404_project(project_id)
    shot = project_shots[project_id].get(shot_id)
    if not shot:
        raise HTTPException(status_code=404, detail="shot not found")
    return {"shot_detail": shot}


@app.delete("/v1/projects/{project_id}/shots/{shot_id}")
async def delete_shot(project_id: str, shot_id: str):
    _get_or_404_project(project_id)
    shots = project_shots.get(project_id, {})
    existed = shots.pop(shot_id, None) is not None
    return {"message": "deleted" if existed else "not found", "shot_id": shot_id, "project_id": project_id}


@app.delete("/v1/shots/{shot_id}")
async def delete_shot_direct(shot_id: str):
    for pid, shots in project_shots.items():
        if shot_id in shots:
            shots.pop(shot_id, None)
            return {"message": "deleted", "shot_id": shot_id, "project_id": pid}
    raise HTTPException(status_code=404, detail="shot not found")


@app.post("/v1/projects/{project_id}/tts")
async def project_tts(project_id: str):
    _get_or_404_project(project_id)
    task_id = str(uuid.uuid4())
    return {"task_id": task_id, "message": "accepted", "project_id": project_id}


@app.post("/v1/projects/{project_id}/video")
async def project_video(project_id: str, background_tasks: BackgroundTasks):
    _get_or_404_project(project_id)
    task_id = str(uuid.uuid4())
    now = _now_iso()
    
    # 创建任务记录到 tasks 字典中
    tasks[task_id] = TaskState(
        id=task_id,
        project_id=project_id,
        type=TASK_TYPE_VIDEO,
        status=TASK_STATUS_PENDING,
        progress=0,
        message="video task created",
        createdAt=now,
        updatedAt=now,
    )
    
    # 模拟后台处理 - 几秒后完成
    async def mock_video_task():
        import asyncio
        await asyncio.sleep(2)
        if task_id in tasks:
            tasks[task_id].status = TASK_STATUS_PROCESSING
            tasks[task_id].progress = 50
            tasks[task_id].message = "generating video..."
            tasks[task_id].updatedAt = _now_iso()
        await asyncio.sleep(2)
        if task_id in tasks:
            tasks[task_id].status = TASK_STATUS_FINISHED
            tasks[task_id].progress = 100
            tasks[task_id].message = "video ready"
            tasks[task_id].result = {
                "resource_type": "video",
                "resource_id": project_id,
                "resource_url": f"/files/final/{project_id}.mp4",
            }
            tasks[task_id].updatedAt = _now_iso()
            tasks[task_id].finishedAt = _now_iso()
    
    background_tasks.add_task(mock_video_task)
    return {"task_id": task_id, "message": "accepted", "project_id": project_id}


# CLI entry: uvicorn gateway.main:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":  # pragma: no cover
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="StoryToVideo Gateway server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host, default 0.0.0.0")
    parser.add_argument("--port", type=int, default=8000, help="Bind port, default 8000")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload")
    cli_args = parser.parse_args()

    uvicorn.run(app, host=cli_args.host, port=cli_args.port, reload=cli_args.reload)
