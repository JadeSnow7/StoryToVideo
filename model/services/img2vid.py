"""FastAPI image-to-video service using Stable-Video-Diffusion-Img2Vid (diffusers).

Optimized for lower resource consumption:
- Reduced default frames: 10 (was 14)
- Reduced inference steps: 6 (was 8)
- Aggressive memory optimization enabled by default
- CPU offload enabled by default for 6-8GB cards
"""

import gc
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import torch
from diffusers import StableVideoDiffusionPipeline
from diffusers.utils import export_to_video
from fastapi import APIRouter, FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel, Field
from model.services.utils import resolve_project_root

router = APIRouter()

PROJECT_ROOT = resolve_project_root()
MODEL_ID = os.getenv("MODEL_ID", "stabilityai/stable-video-diffusion-img2vid")
DEVICE = os.getenv("DEVICE", "cuda")
OUTPUT_DIR = Path(os.getenv("CLIPS_DIR", os.getenv("OUTPUT_DIR", PROJECT_ROOT / "data/clips")))

# Optimized defaults for lower VRAM consumption
MAX_FRAMES = max(int(os.getenv("SVD_MAX_FRAMES", "10")), 6)  # Reduced from 12
DEFAULT_STEPS = max(int(os.getenv("SVD_STEPS", "6")), 2)  # Reduced from 8
MAX_SIDE = max(int(os.getenv("SVD_MAX_SIDE", "448")), 256)  # Reduced from 512
CPU_OFFLOAD = os.getenv("SVD_CPU_OFFLOAD", "1") != "0"
LOW_VRAM_MODE = os.getenv("SVD_LOW_VRAM", "1") != "0"  # New: extra aggressive for 6GB cards
SVD_ENABLED = os.getenv("SVD_ENABLED", "1") != "0"  # Set to 0 to disable SVD completely

pipe = None  # lazy loaded


class GenerateRequest(BaseModel):
    frame: str = Field(..., description="输入单帧图片路径（PNG/JPG）")
    scene_id: Optional[str] = Field(None, description="用于输出文件命名")
    fps: int = Field(12, ge=4, le=30)
    num_frames: int = Field(14, ge=6, le=48)
    motion_bucket_id: int = Field(127, ge=1, le=255)
    noise_aug_strength: float = Field(0.1, ge=0.0, le=1.0)
    num_inference_steps: int = Field(DEFAULT_STEPS, ge=2, le=50)
    seed: Optional[int] = None


class GenerateResponse(BaseModel):
    video: str
    fps: int
    seed: Optional[int] = None


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_pipeline():
    global pipe  # noqa: PLW0603
    if not SVD_ENABLED:
        print("[img2vid] SVD disabled by env var, skipping pipeline load")
        return
    if pipe is not None:
        return
    torch.backends.cuda.matmul.allow_tf32 = True
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    p = StableVideoDiffusionPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=dtype,
        variant="fp16",
    )
    if DEVICE:
        p = p.to(DEVICE)
    try:
        p.enable_attention_slicing()
    except Exception:
        pass
    try:
        p.enable_vae_slicing()
    except Exception:
        pass
    try:
        p.enable_xformers_memory_efficient_attention()
    except Exception:
        pass
    if CPU_OFFLOAD:
        try:
            # CPU offload keeps memory stable on 8GB cards; falls back silently if accelerate is missing
            p.enable_sequential_cpu_offload()
        except Exception:
            pass
    p.set_progress_bar_config(disable=True)
    pipe = p


def _slug(text: str) -> str:
    keep = []
    for ch in text:
        if ch.isalnum():
            keep.append(ch.lower())
        elif ch in (" ", "-", "_"):
            keep.append("_")
    slug = "".join(keep).strip("_")
    return slug or "clip"


def load_image(path: str) -> Image.Image:
    try:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        max_side = max(w, h)
        if max_side > MAX_SIDE:
            scale = MAX_SIDE / float(max_side)
            new_w = int(w * scale) // 8 * 8
            new_h = int(h * scale) // 8 * 8
            img = img.resize((max(new_w, 8), max(new_h, 8)), Image.LANCZOS)
        return img
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to open image: {exc}") from exc


def save_video(frames, fps: int, scene_id: Optional[str], seed: Optional[int]) -> str:
    ensure_output_dir()
    base = scene_id or _slug(str(uuid.uuid4())[:8])
    ts = int(time.time())
    filename = f"{base}_{seed or 'seed'}_{ts}.mp4"
    out_path = OUTPUT_DIR / filename
    export_to_video(frames, out_path, fps=fps)
    return str(out_path)


async def _startup():
    load_pipeline()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "model": MODEL_ID,
        "device": DEVICE,
        "output_dir": str(OUTPUT_DIR),
        "max_frames": MAX_FRAMES,
        "steps": DEFAULT_STEPS,
    }


@router.post("/generate", response_model=GenerateResponse, name="img2vid_generate")
@router.post("/img2vid", response_model=GenerateResponse, include_in_schema=False)
async def generate(req: GenerateRequest):
    if not SVD_ENABLED:
        raise HTTPException(status_code=503, detail="SVD video generation is disabled on this server")
    if pipe is None:
        load_pipeline()
    # Clamp heavy params to keep latency predictable
    num_frames = min(max(req.num_frames, 6), MAX_FRAMES)
    num_steps = min(max(req.num_inference_steps, 2), DEFAULT_STEPS)
    image = load_image(req.frame)
    gen = None
    if req.seed is not None:
        try:
            gen = torch.Generator(device=DEVICE).manual_seed(int(req.seed))
        except Exception:
            gen = torch.Generator().manual_seed(int(req.seed))
    try:
        start_ts = time.perf_counter()
        with torch.inference_mode():
            result = pipe(
                image=image,
                num_frames=num_frames,
                fps=req.fps,
                motion_bucket_id=req.motion_bucket_id,
                noise_aug_strength=req.noise_aug_strength,
                num_inference_steps=num_steps,
                generator=gen,
            )
        elapsed = time.perf_counter() - start_ts
        print(f"[img2vid] scene={req.scene_id or 'n/a'} frames={num_frames} steps={num_steps} fps={req.fps} took {elapsed:.2f}s")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc
    frames = result.frames[0] if hasattr(result, "frames") else []
    if not frames:
        raise HTTPException(status_code=500, detail="No frames generated")
    video_path = save_video(frames, req.fps, req.scene_id, req.seed)
    return {"video": video_path, "fps": req.fps, "seed": req.seed}


def register_app(app: FastAPI, prefix: str = "") -> None:
    app.include_router(router, prefix=prefix)
    app.add_event_handler("startup", _startup)


def create_app() -> FastAPI:
    app = FastAPI(title="IMG2VID Service (SVD Img2Vid)", version="0.1.0")
    register_app(app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("model.services.img2vid:app", host="0.0.0.0", port=8003, reload=False)
