"""Task-related Pydantic models for the Gateway API."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


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


class TaskState(BaseModel):
    """Internal task state representation."""
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


class TaskShotParameters(BaseModel):
    """Shot generation parameters."""
    style: str = ""
    text_llm: str = ""
    image_llm: str = ""
    generate_tts: bool = False
    shot_count: int = 0
    image_width: int = 0
    image_height: int = 0


class TaskVideoParameters(BaseModel):
    """Video generation parameters."""
    format: str = ""
    resolution: str = ""
    fps: str = ""
    transition_effects: str = ""


class TaskParameters(BaseModel):
    """Combined task parameters."""
    shot: TaskShotParameters = Field(default_factory=TaskShotParameters)
    video: TaskVideoParameters = Field(default_factory=TaskVideoParameters)


class TaskShotsResult(BaseModel):
    """Result of shot generation task."""
    generated_shots: List[Dict] = Field(default_factory=list)
    total_shots: int = 0
    total_time: float = 0.0


class TaskAudioResult(BaseModel):
    """Result of audio generation task."""
    generated_audios: List[Dict] = Field(default_factory=list)
    total_audios: int = 0
    total_time: float = 0.0


class TaskVideoResult(BaseModel):
    """Result of video generation task."""
    path: str = ""
    duration: str = ""
    fps: str = ""
    resolution: str = ""
    format: str = ""
    total_time: str = ""
    clips: List[Dict] = Field(default_factory=list)


class TaskResult(BaseModel):
    """Combined task result."""
    task_shots: TaskShotsResult = Field(default_factory=TaskShotsResult)
    task_audio: TaskAudioResult = Field(default_factory=TaskAudioResult)
    task_video: TaskVideoResult = Field(default_factory=TaskVideoResult)


class TaskSchema(BaseModel):
    """Task schema for API responses (matches OpenAPI spec)."""
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


class TaskResponse(BaseModel):
    """Simple task response."""
    id: str
    status: str
    progress: int
    message: str = ""
    result: Optional[Dict] = None
    error: Optional[str] = None
