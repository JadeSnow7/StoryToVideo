"""Project and Shot schemas."""

from pydantic import BaseModel


class ShotSchema(BaseModel):
    """Shot data schema for API responses."""
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
