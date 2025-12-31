"""Model node FastAPI入口，聚合 LLM / 文生图 / 图生视频 / TTS 四个子服务。"""

from datetime import datetime
from typing import Dict

from fastapi import FastAPI

from model.services import img2vid, llm, tts, txt2img

SERVICE_PREFIXES: Dict[str, str] = {
    "llm": "/llm",
    "txt2img": "/txt2img",
    "img2vid": "/img2vid",
    "tts": "/tts",
}

app = FastAPI(title="StoryToVideo Model Node", version="0.2.0")


@app.get("/")
async def root():
    return {
        "status": "ok",
        "ts": datetime.utcnow().isoformat(),
        "services": {name: f"{prefix}/..." for name, prefix in SERVICE_PREFIXES.items()},
    }


@app.get("/health")
async def health():
    return {"status": "ok", "ts": datetime.utcnow().isoformat()}


llm.register_app(app, prefix=SERVICE_PREFIXES["llm"])
txt2img.register_app(app, prefix=SERVICE_PREFIXES["txt2img"])
img2vid.register_app(app, prefix=SERVICE_PREFIXES["img2vid"])
tts.register_app(app, prefix=SERVICE_PREFIXES["tts"])
