"""Health check endpoint."""

import os
from fastapi import APIRouter

router = APIRouter()

LLM_URL = os.getenv("LLM_URL", "http://127.0.0.1:8001/storyboard")
TXT2IMG_URL = os.getenv("TXT2IMG_URL", "http://127.0.0.1:8002/generate")
IMG2VID_URL = os.getenv("IMG2VID_URL", "http://127.0.0.1:8003/img2vid")
TTS_URL = os.getenv("TTS_URL", "http://127.0.0.1:8004/narration")


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "llm": LLM_URL,
        "txt2img": TXT2IMG_URL,
        "img2vid": IMG2VID_URL,
        "tts": TTS_URL,
    }
