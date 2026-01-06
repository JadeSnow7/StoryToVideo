"""Render/Generate request and response models."""

from typing import Dict, Optional
from pydantic import BaseModel, Field


# Default values from environment (can be overridden)
DEFAULT_IMG_STEPS = 4
DEFAULT_CFG_SCALE = 1.5
DEFAULT_IMG_WIDTH = 384
DEFAULT_IMG_HEIGHT = 256


class RenderRequest(BaseModel):
    """Request model for /render and /v1/generate endpoints."""
    story: str = Field(..., description="故事文本")
    style: str = Field("", description="可选风格")
    scenes: int = Field(4, ge=1, le=20, description="分镜数量")
    width: int = Field(DEFAULT_IMG_WIDTH, ge=256, le=2048)
    height: int = Field(DEFAULT_IMG_HEIGHT, ge=256, le=2048)
    img_steps: int = Field(DEFAULT_IMG_STEPS, ge=1, le=50)
    cfg_scale: float = Field(DEFAULT_CFG_SCALE, ge=0.0, le=20.0)
    images_per_scene: int = Field(1, ge=1, le=3, description="每个分镜生成的图片数量")
    fps: int = Field(12, ge=4, le=30)
    clip_seconds: float = Field(5.0, ge=1.0, le=30.0, description="单个分镜时长（秒）")
    video_frames: int = Field(60, ge=8, le=480, description="单个分镜帧数")
    speaker: Optional[str] = Field(None, description="TTS 说话人")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="TTS 语速")


class RenderResponse(BaseModel):
    """Response model for render endpoints."""
    job_id: str
    message: str = ""
    error: str = ""


class ShotDefaults(BaseModel):
    """Default parameters for shot generation."""
    shot_count: Optional[int] = None
    style: Optional[str] = None
    story_text: Optional[str] = Field(None, alias="storyText")


class ShotParam(BaseModel):
    """Shot-specific parameters."""
    transition: Optional[str] = None
    shot_id: Optional[str] = Field(None, alias="shotId")
    image_width: Optional[str] = None
    image_height: Optional[str] = None
    prompt: Optional[str] = None
    style: Optional[str] = None
    negative_prompt: Optional[str] = Field(None, alias="negativePrompt")


class VideoParam(BaseModel):
    """Video generation parameters."""
    resolution: Optional[str] = None
    fps: Optional[int] = None
    format: Optional[str] = None
    bitrate: Optional[int] = None


class TTSParam(BaseModel):
    """TTS generation parameters."""
    voice: Optional[str] = None
    lang: Optional[str] = None
    sample_rate: Optional[int] = None
    format: Optional[str] = Field("wav", description="audio format")


class GenerateParameters(BaseModel):
    """Parameters for /v1/generate endpoint."""
    shot_defaults: Optional[ShotDefaults] = None
    shot: Optional[ShotParam] = None
    video: Optional[VideoParam] = None
    tts: Optional[TTSParam] = None


class GeneratePayload(BaseModel):
    """Payload for /v1/generate endpoint (Worker compatibility).
    
    Note: project_id uses alias for snake_case compatibility with Go Worker.
    """
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
    
    class Config:
        # Allow both snake_case and camelCase for Worker compatibility
        populate_by_name = True
