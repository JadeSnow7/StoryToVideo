"""
FastAPI text-to-image service using Stable Diffusion Turbo (diffusers).
"""

import os
import time
import uuid
from pathlib import Path
from typing import List, Optional

import torch
from diffusers import AutoPipelineForText2Image
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


MODEL_ID = os.getenv("MODEL_ID", "stabilityai/sd-turbo")
DEVICE = os.getenv("DEVICE", "cuda")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "data/frames"))

app = FastAPI(title="TXT2IMG Service (SD Turbo)", version="0.1.0")

pipe = None  # will be loaded at startup


class ImageStyle(BaseModel):
    width: int = Field(768, ge=256, le=2048)
    height: int = Field(512, ge=256, le=2048)
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
    global pipe  # noqa: PLW0603
    if pipe is not None:
        return
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model_kwargs = {"torch_dtype": dtype}
    # variant="fp16" may be required for sd-turbo weights; keep it optional.
    model_kwargs["variant"] = "fp16"
    p = AutoPipelineForText2Image.from_pretrained(MODEL_ID, **model_kwargs)
    if DEVICE:
        p = p.to(DEVICE)
    # xformers is optional; ignore if not available.
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


@app.on_event("startup")
async def _startup():
    load_pipeline()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": MODEL_ID,
        "device": DEVICE,
        "output_dir": str(OUTPUT_DIR),
    }


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
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
    except Exception as exc:  # noqa: BLE001
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


# Run directly: python services/txt2img/main.py
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("services.txt2img.main:app", host="0.0.0.0", port=8002, reload=False)
