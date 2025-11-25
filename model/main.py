"""Minimal FastAPI entrypoint for model node.

This keeps the same endpoint names used in the docs and can be wired to
real pipelines (Qwen via Ollama, Stable Diffusion, Stable Video Diffusion,
CosyVoice, etc.). For now, it echoes the request to keep the container
lightweight while providing a health surface for integration.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field


class StoryboardRequest(BaseModel):
    story: str = Field(..., description="User story text")
    style: Optional[str] = Field(None, description="Tone or visual style hint")


class Shot(BaseModel):
    title: str
    prompt: str
    narration: str
    bgm: Optional[str] = None


class StoryboardResponse(BaseModel):
    shots: List[Shot]
    generated_at: datetime


class SDRequest(BaseModel):
    prompt: str
    style: Optional[str] = None
    width: int = 1024
    height: int = 576


class SDResponse(BaseModel):
    url: str
    note: Optional[str] = None


class Img2VidRequest(BaseModel):
    image_url: str
    duration_seconds: float = 3.0
    transition: Optional[str] = Field(None, description="e.g. dissolve, zoom")


class Img2VidResponse(BaseModel):
    url: str
    note: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = Field(None, description="voice name or speaker id")


class TTSResponse(BaseModel):
    url: str
    note: Optional[str] = None


app = FastAPI(title="StoryToVideo Model Node", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "ts": datetime.utcnow().isoformat()}


@app.post("/llm/storyboard", response_model=StoryboardResponse)
def storyboard(req: StoryboardRequest) -> StoryboardResponse:
    # TODO: wire to Qwen/Ollama
    shot = Shot(
        title="自动生成分镜",
        prompt=f"{req.style or '默认风格'} | {req.story[:80]}",
        narration=req.story,
        bgm="lofi-chill"
    )
    return StoryboardResponse(shots=[shot], generated_at=datetime.utcnow())


@app.post("/sd_generate", response_model=SDResponse)
def sd_generate(req: SDRequest) -> SDResponse:
    # TODO: wire to Stable Diffusion Turbo pipeline
    note = f"Requested {req.width}x{req.height} image in style={req.style or 'default'}"
    return SDResponse(url="https://example.com/keyframe.png", note=note)


@app.post("/img2vid", response_model=Img2VidResponse)
def img2vid(req: Img2VidRequest) -> Img2VidResponse:
    # TODO: wire to Stable-Video-Diffusion-Img2Vid
    note = f"duration={req.duration_seconds}s transition={req.transition or 'cut'}"
    return Img2VidResponse(url="https://example.com/clip.mp4", note=note)


@app.post("/tts", response_model=TTSResponse)
def tts(req: TTSRequest) -> TTSResponse:
    # TODO: wire to CosyVoice-mini
    note = f"voice={req.voice or 'default'}"
    return TTSResponse(url="https://example.com/narration.wav", note=note)
