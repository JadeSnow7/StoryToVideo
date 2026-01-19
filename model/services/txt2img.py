"""FastAPI text-to-image service with cloud provider support.

Supported providers (via IMAGE_PROVIDER env var):
- local: SD Turbo (default, requires GPU)
- horde: AI Horde (free, community-driven)
- cloudflare: Cloudflare Workers AI (fast, generous free tier)
"""

import os
import time
import uuid
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field
from model.services.utils import resolve_project_root

# Conditional imports for local GPU mode
try:
    import torch
    from diffusers import AutoPipelineForText2Image
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

# Cloud providers
try:
    from model.services.cloud_providers import get_image_provider, ImageProvider
    CLOUD_PROVIDERS_AVAILABLE = True
except ImportError:
    CLOUD_PROVIDERS_AVAILABLE = False
    ImageProvider = None

router = APIRouter()

PROJECT_ROOT = resolve_project_root()
MODEL_ID = os.getenv("MODEL_ID", "stabilityai/sd-turbo")
DEVICE = os.getenv("DEVICE", "cuda")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "data/frames"))
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "local").lower()

pipe = None  # lazy loaded for local mode


class ImageStyle(BaseModel):
    width: int = Field(512, ge=256, le=2048)
    height: int = Field(384, ge=256, le=2048)
    num_inference_steps: int = Field(4, ge=1, le=20)
    guidance_scale: float = Field(1.5, ge=0.0, le=10.0)


class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None
    style: ImageStyle = Field(default_factory=ImageStyle)
    scene_id: Optional[str] = Field(None, description="用于输出文件命名")


class GeneratedItem(BaseModel):
    path: str
    seed: int


class GenerateResponse(BaseModel):
    images: List[GeneratedItem]


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_pipeline():
    """Load local SD Turbo pipeline (only in local mode)."""
    global pipe
    if pipe is not None:
        return
    if not TORCH_AVAILABLE:
        raise RuntimeError("torch/diffusers not available. Use cloud provider or install dependencies.")
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model_kwargs = {"torch_dtype": dtype}
    model_kwargs["variant"] = "fp16"
    p = AutoPipelineForText2Image.from_pretrained(MODEL_ID, **model_kwargs)
    if DEVICE:
        p = p.to(DEVICE)
    try:
        p.enable_xformers_memory_efficient_attention()
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
    return slug or "img"


def save_image(image, scene_id: Optional[str], seed: int) -> str:
    ensure_output_dir()
    base = scene_id or _slug(str(uuid.uuid4())[:8])
    ts = int(time.time())
    filename = f"{base}_{seed}_{ts}.png"
    path = OUTPUT_DIR / filename
    image.save(path)
    return str(path)


def save_image_bytes(image_bytes: bytes, scene_id: Optional[str], seed: int) -> str:
    """Save image from bytes (for cloud providers)."""
    ensure_output_dir()
    base = scene_id or _slug(str(uuid.uuid4())[:8])
    ts = int(time.time())
    filename = f"{base}_{seed}_{ts}.png"
    path = OUTPUT_DIR / filename
    with open(path, "wb") as f:
        f.write(image_bytes)
    return str(path)


async def _startup():
    # Only load local pipeline if in local mode and torch is available
    if IMAGE_PROVIDER == "local" and TORCH_AVAILABLE:
        load_pipeline()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "provider": IMAGE_PROVIDER,
        "model": MODEL_ID if IMAGE_PROVIDER == "local" else "cloud",
        "device": DEVICE,
        "output_dir": str(OUTPUT_DIR),
        "cloud_available": CLOUD_PROVIDERS_AVAILABLE,
    }


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    # Use cloud provider if configured
    if IMAGE_PROVIDER != "local" and CLOUD_PROVIDERS_AVAILABLE:
        return await generate_cloud(req)
    return await generate_local(req)


async def generate_cloud(req: GenerateRequest) -> dict:
    """Generate image using cloud provider (AI Horde/Cloudflare)."""
    provider = get_image_provider()
    if provider is None:
        raise HTTPException(status_code=500, detail="Cloud image provider not configured")
    
    try:
        image_bytes = await provider.generate(
            prompt=req.prompt,
            negative_prompt=req.negative_prompt,
            width=req.style.width,
            height=req.style.height,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Cloud generation failed: {exc}") from exc
    
    if not image_bytes:
        raise HTTPException(status_code=500, detail="No image generated")
    
    seed = req.seed if req.seed is not None else int(time.time())
    path = save_image_bytes(image_bytes, req.scene_id or "s1", seed)
    return {"images": [GeneratedItem(path=path, seed=seed)]}


async def generate_local(req: GenerateRequest) -> dict:
    """Generate image using local SD Turbo."""
    if not TORCH_AVAILABLE:
        raise HTTPException(status_code=500, detail="torch/diffusers not available")
    if pipe is None:
        load_pipeline()
    gen = None
    if req.seed is not None:
        try:
            gen = torch.Generator(device=DEVICE).manual_seed(int(req.seed))
        except Exception:
            gen = torch.Generator().manual_seed(int(req.seed))
    try:
        result = pipe(
            req.prompt,
            negative_prompt=req.negative_prompt,
            width=req.style.width,
            height=req.style.height,
            num_inference_steps=req.style.num_inference_steps,
            guidance_scale=req.style.guidance_scale,
            generator=gen,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc
    images = result.images if hasattr(result, "images") else []
    if not images:
        raise HTTPException(status_code=500, detail="No images generated")
    items: List[GeneratedItem] = []
    for idx, img in enumerate(images):
        seed = req.seed if req.seed is not None else int(torch.seed())
        path = save_image(img, req.scene_id or f"s{idx+1}", seed)
        items.append(GeneratedItem(path=path, seed=seed))
    return {"images": items}


def register_app(app: FastAPI, prefix: str = "") -> None:
    app.include_router(router, prefix=prefix)
    app.add_event_handler("startup", _startup)


def create_app() -> FastAPI:
    app = FastAPI(title="TXT2IMG Service (SD Turbo)", version="0.1.0")
    register_app(app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("model.services.txt2img:app", host="0.0.0.0", port=8002, reload=False)
