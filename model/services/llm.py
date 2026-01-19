"""FastAPI LLM storyboard service with cloud provider support.

Supported providers (via LLM_PROVIDER env var):
- ollama: Local Ollama (default)
- groq: Groq Cloud (free tier)
- deepseek: DeepSeek API
- openrouter: OpenRouter (multi-model)
"""

import json
import os
import re
from typing import List, Optional

import httpx
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from model.services.cloud_providers import get_llm_provider, LLMProvider
    CLOUD_PROVIDERS_AVAILABLE = True
except ImportError:
    CLOUD_PROVIDERS_AVAILABLE = False
    LLMProvider = None

router = APIRouter()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:0.5b")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()


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


SYSTEM_PROMPT = """You are a professional storyboard assistant for video production.

Your task: Convert the input story into a storyboard with EXACTLY the requested number of scenes.

OUTPUT FORMAT (JSON only, no explanation):
{"storyboard": [{"scene_id": "s1", "title": "...", "prompt": "...", "narration": "...", "bgm": ""}, ...]}

FIELD REQUIREMENTS:
- scene_id: s1, s2, s3... (must have exactly N scenes as requested)
- title: 2-5 word scene title (English or Chinese)
- prompt: ENGLISH ONLY, comma-separated keywords for Stable Diffusion Turbo:
  * 12-28 keyword phrases
  * Allowed characters: A-Z, a-z, 0-9, comma, space (no punctuation or symbols)
  * Format: "subject, action, setting, lighting, mood, camera angle, style, quality"
  * Example: "young woman, walking on street, modern city, daytime, casual outfit, eye level shot, realistic style, high detail, 8k"
  * NEVER use Chinese in prompt field
  * If a style is provided, reflect it with matching English keywords
- narration: Scene narration for TTS (Chinese or English)
- bgm: Empty string or mood keyword

EXAMPLE:
{"scene_id":"s1","title":"Morning Coffee","prompt":"young man, drinking coffee, cozy kitchen, morning sunlight through window, relaxed mood, medium shot, warm colors, photorealistic, high detail","narration":"清晨的阳光洒进厨房，他端起一杯热咖啡。","bgm":""}

IMPORTANT: The prompt field MUST be in English keywords only. This is critical for image generation.
"""


CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ASCII_ALPHA_RE = re.compile(r"[A-Za-z]")
PROMPT_ALLOWED_RE = re.compile(r"^[A-Za-z0-9, ]+$")
WORD_RE = re.compile(r"[A-Za-z0-9]+")
MIN_PROMPT_KEYWORDS = 12
MAX_PROMPT_KEYWORDS = 28


def build_user_prompt(req: StoryboardRequest) -> str:
    style = f"\n风格：{req.style}" if req.style else ""
    return f"故事：{req.story}{style}\n分镜数量：{req.scenes}"


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: Optional[int] = None) -> Optional[int]:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _ollama_options() -> dict:
    options = {
        "temperature": _env_float("LLM_TEMPERATURE", 0.3),
        "top_p": _env_float("LLM_TOP_P", 0.9),
        "top_k": _env_int("LLM_TOP_K", 40),
        "repeat_penalty": _env_float("LLM_REPEAT_PENALTY", 1.1),
        "repeat_last_n": _env_int("LLM_REPEAT_LAST_N", 128),
    }
    num_ctx = _env_int("LLM_NUM_CTX")
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    seed = _env_int("LLM_SEED")
    if seed is not None:
        options["seed"] = seed
    return options


def _has_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text or ""))


def _has_english(text: str) -> bool:
    return bool(ASCII_ALPHA_RE.search(text or ""))


# Keyword mapping for dynamic fallback prompt generation
KEYWORD_MAP = {
    # People
    "男": "man", "女": "woman", "人": "person", "孩子": "child", "老人": "elderly person",
    "年轻": "young", "男子": "young man", "女孩": "girl", "男孩": "boy",
    # Actions
    "走": "walking", "跑": "running", "坐": "sitting", "站": "standing", 
    "看": "looking", "读": "reading", "喝": "drinking", "吃": "eating",
    "说": "talking", "笑": "smiling", "哭": "crying", "想": "thinking",
    # Places
    "家": "home", "街": "street", "咖啡": "coffee shop", "图书馆": "library",
    "厨房": "kitchen", "客厅": "living room", "卧室": "bedroom", "办公": "office",
    "公园": "park", "学校": "school", "商店": "store", "餐厅": "restaurant",
    # Objects
    "书": "book", "电脑": "computer", "手机": "phone", "杯": "cup",
    "沙发": "sofa", "桌": "table", "椅": "chair", "窗": "window",
    # Time/Light
    "早": "morning", "晚": "evening", "夜": "night", "阳光": "sunlight",
    "清晨": "early morning", "黄昏": "dusk", "午后": "afternoon",
    # Mood
    "开心": "happy", "悲伤": "sad", "温馨": "warm", "紧张": "tense",
}

STYLE_KEYWORDS = {
    "赛博朋克": ["cyberpunk", "neon lights", "futuristic city", "rainy night", "high contrast"],
    "蒸汽朋克": ["steampunk", "brass", "gears", "victorian", "warm light"],
    "电影": ["cinematic", "film still", "anamorphic lens", "soft contrast"],
    "写实": ["photorealistic", "realistic texture", "natural light"],
    "国风": ["chinese ink style", "ink wash", "misty atmosphere", "traditional art"],
    "水墨": ["ink wash", "brush strokes", "paper texture", "minimalist"],
    "动漫": ["anime style", "cel shading", "clean line art"],
    "二次元": ["anime style", "vivid colors", "clean line art"],
    "油画": ["oil painting", "brush strokes", "canvas texture"],
    "水彩": ["watercolor", "soft wash", "paper texture"],
    "像素": ["pixel art", "8 bit", "low resolution"],
    "复古": ["retro", "vintage", "film grain"],
    "科幻": ["sci fi", "futuristic", "high tech"],
    "奇幻": ["fantasy", "magical", "ethereal"],
    "黑白": ["black and white", "monochrome", "high contrast"],
    "日系": ["japanese style", "soft light", "clean composition"],
}

STYLE_SPLIT_RE = re.compile(r"[，,、/|;]+")
MULTI_SUBJECT_ZH_RE = re.compile(r"(两人|三人|多人|人群|一家|家人|父子|母子|夫妻|情侣|朋友|同学|孩子们|他们|她们|大家)")
MULTI_SUBJECT_EN_RE = re.compile(
    r"\b(two|three|four|five|several|many|multiple|group|crowd|family|couple|friends|people|men|women|children|kids|twins|siblings)\b",
    re.IGNORECASE,
)
TWO_SUBJECT_ZH_RE = re.compile(r"(两人|俩人|两个|一对|情侣|夫妻|兄弟|姐妹|兄妹|一男一女|男孩和女孩|男孩与女孩|男孩对女孩|一个男孩对另一个女孩)")
TWO_SUBJECT_EN_RE = re.compile(r"\b(two people|two persons|couple|pair|boy and girl|two kids|two children|two subjects)\b", re.IGNORECASE)
CHILD_ZH_RE = re.compile(r"(男孩|女孩|孩子|儿童|小孩|小男孩|小女孩)")
ADULT_ZH_RE = re.compile(r"(男人|女人|男子|女子|成人|大人|父亲|母亲|爸爸|妈妈)")
CHILD_EN_RE = re.compile(r"\b(boy|girl|child|children|kid|kids)\b", re.IGNORECASE)
ADULT_EN_RE = re.compile(r"\b(man|woman|adult|elderly|father|mother)\b", re.IGNORECASE)
PERSON_WORDS = {
    "person",
    "man",
    "woman",
    "boy",
    "girl",
    "child",
    "children",
    "kid",
    "kids",
    "elderly",
    "adult",
    "teen",
}
SINGLE_SUBJECT_HINTS = ["single subject", "clean composition"]
TWO_SUBJECT_HINTS = ["two people", "no extra people", "no duplicate people"]
TWO_CHILD_HINTS = ["two children", "no extra people", "no duplicate people"]

EN_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "to", "of", "in", "on",
    "at", "for", "from", "with", "by", "as", "is", "am", "are", "was", "were", "be",
    "been", "being", "it", "its", "this", "that", "these", "those", "i", "you", "he",
    "she", "they", "we", "me", "my", "your", "his", "her", "their", "our", "us",
    "today", "yesterday", "tomorrow", "now", "just", "very", "really",
}


def _split_keywords(prompt: str) -> List[str]:
    return [p.strip() for p in (prompt or "").split(",") if p.strip()]


def _normalize_prompt(prompt: str) -> str:
    if not prompt:
        return ""
    cleaned = prompt.strip()
    cleaned = cleaned.replace("，", ",").replace("、", ",")
    cleaned = cleaned.replace(";", ",").replace("|", ",")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _is_keyword_prompt(prompt: str) -> bool:
    if not prompt:
        return False
    if _has_cjk(prompt):
        return False
    if not PROMPT_ALLOWED_RE.match(prompt):
        return False
    return len(_split_keywords(prompt)) >= MIN_PROMPT_KEYWORDS


def _extract_english_keywords(text: str) -> List[str]:
    tokens = [w.lower() for w in WORD_RE.findall(text or "")]
    keywords: List[str] = []
    for word in tokens:
        if word in EN_STOPWORDS:
            continue
        if word not in keywords:
            keywords.append(word)
    return keywords


def _sanitize_keyword(word: str) -> str:
    return (word or "").replace("-", " ").strip()


def _style_keywords(style: Optional[str]) -> List[str]:
    if not style:
        return []
    keywords: List[str] = []
    for part in STYLE_SPLIT_RE.split(style):
        token = part.strip()
        if not token:
            continue
        if _has_cjk(token):
            for cn, items in STYLE_KEYWORDS.items():
                if cn in token:
                    for item in items:
                        if item not in keywords:
                            keywords.append(item)
        else:
            phrase = _sanitize_keyword(_normalize_prompt(token)).lower()
            if phrase and phrase not in keywords:
                keywords.append(phrase)
            for kw in _extract_english_keywords(token):
                if kw not in keywords:
                    keywords.append(kw)
    return keywords


def _count_person_keywords(keywords: List[str]) -> int:
    count = 0
    for keyword in keywords:
        words = keyword.lower().split()
        if any(word in PERSON_WORDS for word in words):
            count += 1
    return count


def _has_two_subject_hint(text: str) -> bool:
    return bool(TWO_SUBJECT_ZH_RE.search(text) or TWO_SUBJECT_EN_RE.search(text))


def _filter_person_keywords(keywords: List[str], text: str) -> List[str]:
    child_context = bool(CHILD_ZH_RE.search(text) or CHILD_EN_RE.search(text))
    adult_context = bool(ADULT_ZH_RE.search(text) or ADULT_EN_RE.search(text))
    if child_context and not adult_context:
        filtered: List[str] = []
        for keyword in keywords:
            words = keyword.lower().split()
            if any(word in {"man", "woman", "adult", "elderly", "father", "mother"} for word in words):
                continue
            filtered.append(keyword)
        return filtered
    return keywords


def _should_add_single_subject(text: str, keywords: List[str]) -> bool:
    if _has_two_subject_hint(text):
        return False
    if MULTI_SUBJECT_ZH_RE.search(text):
        return False
    if MULTI_SUBJECT_EN_RE.search(text):
        return False
    person_count = _count_person_keywords(keywords)
    if person_count >= 2:
        return False
    return True


def _apply_subject_hints(prompt: str, title: str, narration: str) -> str:
    keywords = _split_keywords(prompt)
    text = " ".join([t for t in [title, narration, prompt] if t])
    keywords = _filter_person_keywords(keywords, text)
    if _has_two_subject_hint(text):
        child_context = bool(CHILD_ZH_RE.search(text) or CHILD_EN_RE.search(text))
        hints = TWO_CHILD_HINTS if child_context else TWO_SUBJECT_HINTS
        for hint in hints:
            if hint not in keywords:
                keywords.append(hint)
        cleaned = [_sanitize_keyword(k) for k in keywords if k]
        deduped: List[str] = []
        for item in cleaned:
            if item and item not in deduped:
                deduped.append(item)
        return ", ".join(deduped[:MAX_PROMPT_KEYWORDS])
    if not _should_add_single_subject(text, keywords):
        return prompt
    for hint in SINGLE_SUBJECT_HINTS:
        if hint not in keywords:
            keywords.append(hint)
    if _count_person_keywords(keywords) == 1 and "one person" not in keywords:
        keywords.append("one person")
    cleaned = [_sanitize_keyword(k) for k in keywords if k]
    deduped: List[str] = []
    for item in cleaned:
        if item and item not in deduped:
            deduped.append(item)
    return ", ".join(deduped[:MAX_PROMPT_KEYWORDS])


def _apply_style_keywords(prompt: str, style: Optional[str]) -> str:
    style_kw = _style_keywords(style)
    if not style_kw:
        return prompt
    keywords = _split_keywords(prompt)
    for item in style_kw:
        if item and item not in keywords:
            keywords.append(item)
    cleaned = [_sanitize_keyword(k) for k in keywords if k]
    deduped: List[str] = []
    for item in cleaned:
        if item and item not in deduped:
            deduped.append(item)
    return ", ".join(deduped[:MAX_PROMPT_KEYWORDS])


def _build_keyword_prompt(
    title: str,
    narration: str,
    scene_idx: int,
    style: Optional[str],
    original_prompt: str,
) -> str:
    text = " ".join([t for t in [title, narration, original_prompt] if t])
    keywords: List[str] = []

    if _has_cjk(text):
        for cn, en in KEYWORD_MAP.items():
            if cn in text and en not in keywords:
                keywords.append(en)
    else:
        keywords.extend(_extract_english_keywords(text))

    style_kw = _style_keywords(style)
    for item in style_kw:
        if item not in keywords:
            keywords.append(item)

    scene_variations = [
        "wide shot",
        "medium shot",
        "close up shot",
        "establishing shot",
        "eye level shot",
    ]
    keywords.append(scene_variations[scene_idx % len(scene_variations)])

    defaults = [
        "cinematic lighting",
        "soft light",
        "natural colors",
        "shallow depth of field",
        "high detail",
        "sharp focus",
        "film still",
    ]
    for item in defaults:
        if item not in keywords:
            keywords.append(item)

    fillers = [
        "subject",
        "scene",
        "background",
        "composition",
        "atmosphere",
        "realistic texture",
        "photorealistic",
    ]
    for filler in fillers:
        if len(keywords) >= MIN_PROMPT_KEYWORDS:
            break
        if filler not in keywords:
            keywords.append(filler)

    cleaned = [_sanitize_keyword(k) for k in keywords if k]
    deduped: List[str] = []
    for item in cleaned:
        if item and item not in deduped:
            deduped.append(item)

    prompt = ", ".join(deduped[:MAX_PROMPT_KEYWORDS])
    return _apply_subject_hints(prompt, title, narration)


def _generate_fallback_prompt(
    title: str,
    narration: str,
    scene_idx: int,
    style: Optional[str],
    original_prompt: str,
) -> str:
    """Generate an English keyword prompt when model output is not compliant."""
    return _build_keyword_prompt(title, narration, scene_idx, style, original_prompt)


async def call_ollama(req: StoryboardRequest) -> List[StoryboardItem]:
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(req)},
        ],
        "format": "json",
        "stream": False,
        "options": _ollama_options(),
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
            "prompt": _normalize_prompt(
                (item.get("prompt") or item.get("description") or "").strip()
            ),
            "narration": (item.get("narration") or item.get("voiceover") or "").strip(),
            "bgm": item.get("bgm"),
        }
        if not _is_keyword_prompt(normalized["prompt"]):
            normalized["prompt"] = _generate_fallback_prompt(
                normalized["title"],
                normalized["narration"],
                idx,
                req.style,
                normalized["prompt"],
            )
        else:
            normalized["prompt"] = _apply_style_keywords(normalized["prompt"], req.style)
        normalized["prompt"] = _apply_subject_hints(
            normalized["prompt"], normalized["title"], normalized["narration"]
        )
        try:
            sanitized.append(StoryboardItem(**normalized))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"LLM output schema error: {exc}") from exc
    return sanitized


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "provider": LLM_PROVIDER,
        "model": LLM_MODEL,
        "ollama": OLLAMA_HOST,
        "cloud_available": CLOUD_PROVIDERS_AVAILABLE,
    }


async def call_cloud_llm(req: StoryboardRequest) -> List[StoryboardItem]:
    """Call cloud LLM provider (Groq/DeepSeek/OpenRouter)."""
    if not CLOUD_PROVIDERS_AVAILABLE:
        raise HTTPException(status_code=500, detail="Cloud providers not available")
    
    provider = get_llm_provider()
    if provider is None:
        raise HTTPException(status_code=500, detail="Cloud provider not configured")
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(req)},
    ]
    
    try:
        response = await provider.chat_completion(
            messages=messages,
            temperature=_env_float("LLM_TEMPERATURE", 0.3),
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Cloud LLM error: {exc}") from exc
    
    # Parse response (OpenAI-compatible format)
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise HTTPException(status_code=502, detail="Empty response from cloud LLM")
    
    return _parse_llm_response(content, req)


def _parse_llm_response(content: str, req: StoryboardRequest) -> List[StoryboardItem]:
    """Parse LLM response content into storyboard items."""
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
            "prompt": _normalize_prompt(
                (item.get("prompt") or item.get("description") or "").strip()
            ),
            "narration": (item.get("narration") or item.get("voiceover") or "").strip(),
            "bgm": item.get("bgm"),
        }
        if not _is_keyword_prompt(normalized["prompt"]):
            normalized["prompt"] = _generate_fallback_prompt(
                normalized["title"],
                normalized["narration"],
                idx,
                req.style,
                normalized["prompt"],
            )
        else:
            normalized["prompt"] = _apply_style_keywords(normalized["prompt"], req.style)
        normalized["prompt"] = _apply_subject_hints(
            normalized["prompt"], normalized["title"], normalized["narration"]
        )
        try:
            sanitized.append(StoryboardItem(**normalized))
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"LLM output schema error: {exc}") from exc
    return sanitized


@router.post("/storyboard", response_model=StoryboardResponse)
async def generate_storyboard(req: StoryboardRequest):
    # Use cloud provider if configured, fallback to Ollama
    if LLM_PROVIDER != "ollama" and CLOUD_PROVIDERS_AVAILABLE:
        items = await call_cloud_llm(req)
    else:
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
