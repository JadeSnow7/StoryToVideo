"""FastAPI LLM storyboard service backed by Ollama (Qwen2.5-0.5B by default)."""

import json
import os
from typing import List, Optional

import httpx
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:0.5b")


class StoryboardRequest(BaseModel):
    story: str = Field(..., description="故事正文")
    style: Optional[str] = Field(None, description="整体风格提示，如 赛博朋克")
    scenes: int = Field(6, gt=0, le=20, description="分镜数量，默认 6")


class StoryboardItem(BaseModel):
    scene_id: str
    title: str
    prompt: str
    narration: str
    bgm: Optional[str] = None


class StoryboardResponse(BaseModel):
    storyboard: List[StoryboardItem]


SYSTEM_PROMPT = """你是分镜脚本助手。将输入的故事文本和风格信息，拆分为分镜列表，输出 JSON 对象：
{
  "storyboard": [
    {"scene_id": "s1", "title": "...", "prompt": "...", "narration": "...", "bgm": "..."},
    ...
  ]
}
要求：
- scene_id 按 s1, s2, ... 编号；总数与用户请求的 scenes 一致。
- prompt 要具体且保持前后连贯：明确人物/地点/时间/动作，沿用上一镜头的主角、道具、光线或情绪，不要跳跃到新场景；控制在 1 句话。
- narration 简短旁白（1 句话），与 prompt 对应；bgm 可留空或给风格提示。
- 仅返回 JSON，不要附加解释。
"""


def build_user_prompt(req: StoryboardRequest) -> str:
    style = f"\n风格：{req.style}" if req.style else ""
    return f"故事：{req.story}{style}\n分镜数量：{req.scenes}"


async def call_ollama(req: StoryboardRequest) -> List[StoryboardItem]:
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(req)},
        ],
        "format": "json",
        "stream": False,
    }
    url = f"{OLLAMA_HOST}/api/chat"
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Ollama error: {resp.text}")
    data = resp.json()
    content = data.get("message", {}).get("content")
    if not content:
        raise HTTPException(status_code=502, detail="Empty response from Ollama")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Invalid JSON returned by LLM")
    storyboard = parsed.get("storyboard")
    if not storyboard or not isinstance(storyboard, list):
        raise HTTPException(status_code=502, detail="LLM output missing storyboard list")
    sanitized: List[StoryboardItem] = []
    for idx, raw in enumerate(storyboard, start=1):
        if isinstance(raw, dict):
            item = raw
        elif isinstance(raw, list) and raw and isinstance(raw[0], dict):
            item = raw[0]
        else:
            item = {}
        normalized = {
            "scene_id": item.get("scene_id") or f"s{idx}",
            "title": item.get("title") or f"Scene {idx}",
            "prompt": item.get("prompt") or item.get("description") or "",
            "narration": item.get("narration") or item.get("voiceover") or "",
            "bgm": item.get("bgm"),
        }
        try:
            sanitized.append(StoryboardItem(**normalized))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"LLM output schema error: {exc}") from exc
    return sanitized


@router.get("/health")
async def health():
    return {"status": "ok", "model": LLM_MODEL, "ollama": OLLAMA_HOST}


@router.post("/storyboard", response_model=StoryboardResponse)
async def generate_storyboard(req: StoryboardRequest):
    items = await call_ollama(req)
    for idx, item in enumerate(items, start=1):
        if not item.scene_id:
            item.scene_id = f"s{idx}"
    return {"storyboard": items}


def register_app(app: FastAPI, prefix: str = "") -> None:
    app.include_router(router, prefix=prefix)


def create_app() -> FastAPI:
    app = FastAPI(title="LLM Storyboard Service", version="0.1.0")
    register_app(app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("model.services.llm:app", host="0.0.0.0", port=8001, reload=False)
