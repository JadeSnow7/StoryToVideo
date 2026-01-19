"""FastAPI TTS service with cloud provider support.

Supported providers (via TTS_PROVIDER env var):
- local: CosyVoice2 (default, requires GPU)
- edge: Microsoft Edge TTS (free, no API key)
- elevenlabs: ElevenLabs (10k chars/month free)
"""

import os
import sys
import time
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import soundfile as sf
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field
from model.services.utils import resolve_project_root

# Cloud providers
try:
    from model.services.cloud_providers import get_tts_provider, TTSProvider
    CLOUD_PROVIDERS_AVAILABLE = True
except ImportError:
    CLOUD_PROVIDERS_AVAILABLE = False
    TTSProvider = None

router = APIRouter()

PROJECT_ROOT = resolve_project_root()
COSYVOICE_ROOT = PROJECT_ROOT / "CosyVoice"
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "local").lower()

# Only load CosyVoice for local mode
if TTS_PROVIDER == "local":
    if COSYVOICE_ROOT.exists() and str(COSYVOICE_ROOT) not in sys.path:
        sys.path.insert(0, str(COSYVOICE_ROOT))
    try:
        from cosyvoice.cli.cosyvoice import CosyVoice2
        COSYVOICE_AVAILABLE = True
    except ImportError:
        CosyVoice2 = None
        COSYVOICE_AVAILABLE = False
else:
    CosyVoice2 = None
    COSYVOICE_AVAILABLE = False

MODEL_ID = os.getenv(
    "MODEL_ID",
    str(PROJECT_ROOT / "pretrained_models" / "CosyVoice2-0.5B" / "iic" / "CosyVoice2-0___5B"),
)
DEVICE = os.getenv("DEVICE", "cuda")
OUTPUT_DIR = Path(os.getenv("AUDIO_DIR", os.getenv("OUTPUT_DIR", PROJECT_ROOT / "data/audio")))
ZERO_SHOT_AUDIO = PROJECT_ROOT / "CosyVoice" / "asset" / "zero_shot_prompt.wav"
ZERO_SHOT_TEXT = "希望你以后能够做的比我还好呦。"
ZERO_SHOT_ID = "zero_shot_demo"

voice_model = None
default_speaker: Optional[str] = None
available_speakers: List[str] = []


class Line(BaseModel):
    scene_id: str
    text: str


class NarrationRequest(BaseModel):
    lines: List[Line]
    speaker: Optional[str] = Field(None, description="说话人/音色，如不指定使用默认")
    sample_rate: Optional[int] = Field(None, description="可选采样率，默认为模型采样率")
    speed: float = Field(1.0, ge=0.5, le=2.0)


class AudioItem(BaseModel):
    scene_id: str
    audio: str
    sample_rate: int


class NarrationResponse(BaseModel):
    audios: List[AudioItem]


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_voice_model():
    global voice_model, default_speaker, available_speakers  # noqa: PLW0603
    if voice_model is not None:
        return
    model_path = Path(MODEL_ID)
    if not model_path.exists():
        raise RuntimeError(f"MODEL_ID path not found: {model_path}")
    voice_model = CosyVoice2(str(model_path), load_jit=False, load_trt=False, fp16=True)
    try:
        spks = voice_model.list_available_spks() or []
    except Exception:
        spks = []

    def _ensure_embedding(spk_id: str) -> None:
        entry = voice_model.frontend.spk2info.get(spk_id)
        if entry and "embedding" not in entry and "llm_embedding" in entry:
            entry["embedding"] = entry["llm_embedding"]

    if not spks and ZERO_SHOT_AUDIO.exists():
        try:
            import torchaudio

            prompt, sr = torchaudio.load(str(ZERO_SHOT_AUDIO), backend="soundfile")
            if prompt.shape[0] > 1:
                prompt = prompt.mean(dim=0, keepdim=True)
            if sr != 16000:
                prompt = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)(prompt)
            voice_model.add_zero_shot_spk(ZERO_SHOT_TEXT, prompt, ZERO_SHOT_ID)
            _ensure_embedding(ZERO_SHOT_ID)
            voice_model.save_spkinfo()
            spks = voice_model.list_available_spks() or []
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] bootstrap zero-shot speaker failed: {exc}")

    for spk_id in spks:
        _ensure_embedding(spk_id)

    available_speakers = spks
    default_speaker = spks[0] if spks else None


def _slug(text: str) -> str:
    keep = []
    for ch in text:
        if ch.isalnum():
            keep.append(ch.lower())
        elif ch in (" ", "-", "_"):
            keep.append("_")
    slug = "".join(keep).strip("_")
    return slug or "audio"


def synthesize(text: str, speaker: Optional[str], speed: float) -> (np.ndarray, int):
    if voice_model is None:
        raise RuntimeError("voice_model not loaded")
    spk = speaker or default_speaker
    if spk is None:
        raise RuntimeError(
            f"No speaker available; please provide speaker id. "
            f"Available: {available_speakers or '[]'}"
        )
    try:
        gen = voice_model.inference_sft(tts_text=text, spk_id=spk, stream=False, speed=speed)
        audio_np = None
        for out in gen:
            audio_np = out["tts_speech"]
            break
        if audio_np is None:
            raise RuntimeError("CosyVoice2 returned empty audio")
        return audio_np.squeeze(), voice_model.sample_rate
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] TTS synthesize fallback to silence for speaker={spk}: {exc}")
        return generate_silence(0.2)


def generate_silence(duration_sec: float) -> (np.ndarray, int):
    sr = voice_model.sample_rate if voice_model is not None else 24000
    samples = max(1, int(sr * duration_sec))
    return np.zeros(samples, dtype=np.float32), sr


def save_audio(audio: np.ndarray, sample_rate: int, scene_id: str) -> str:
    ensure_output_dir()
    base = _slug(scene_id) if scene_id else _slug(str(uuid.uuid4())[:8])
    ts = int(time.time())
    filename = f"{base}_{ts}.wav"
    path = OUTPUT_DIR / filename
    sf.write(path, audio, sample_rate)
    return str(path)


def save_audio_bytes(audio_bytes: bytes, scene_id: str, sample_rate: int) -> str:
    """Save audio from bytes (for cloud providers)."""
    ensure_output_dir()
    base = _slug(scene_id) if scene_id else _slug(str(uuid.uuid4())[:8])
    ts = int(time.time())
    filename = f"{base}_{ts}.mp3"  # Cloud providers often return MP3
    path = OUTPUT_DIR / filename
    with open(path, "wb") as f:
        f.write(audio_bytes)
    return str(path)


async def _startup():
    # Only load local model if in local mode
    if TTS_PROVIDER == "local" and COSYVOICE_AVAILABLE:
        load_voice_model()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "provider": TTS_PROVIDER,
        "model": MODEL_ID if TTS_PROVIDER == "local" else "cloud",
        "device": DEVICE,
        "output_dir": str(OUTPUT_DIR),
        "default_speaker": default_speaker,
        "available_speakers": available_speakers,
        "cloud_available": CLOUD_PROVIDERS_AVAILABLE,
    }


@router.post("/narration", response_model=NarrationResponse)
async def narration(req: NarrationRequest):
    if not req.lines:
        raise HTTPException(status_code=400, detail="lines is empty")
    
    # Use cloud provider if configured
    if TTS_PROVIDER != "local" and CLOUD_PROVIDERS_AVAILABLE:
        return await narration_cloud(req)
    return await narration_local(req)


async def narration_cloud(req: NarrationRequest) -> dict:
    """Generate narration using cloud TTS (Edge TTS/ElevenLabs)."""
    provider = get_tts_provider()
    if provider is None:
        raise HTTPException(status_code=500, detail="Cloud TTS provider not configured")
    
    outputs: List[AudioItem] = []
    for line in req.lines:
        try:
            text = line.text or ""
            if not text.strip():
                # Generate silence for empty text
                audio, sr = generate_silence(0.2)
                path = save_audio(audio, sr, line.scene_id)
            else:
                audio_bytes, sr = await provider.synthesize(
                    text=text,
                    voice=req.speaker,
                    speed=req.speed,
                )
                path = save_audio_bytes(audio_bytes, line.scene_id, sr)
            outputs.append(AudioItem(scene_id=line.scene_id, audio=path, sample_rate=sr))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"TTS failed for {line.scene_id}: {exc}") from exc
    return {"audios": outputs}


async def narration_local(req: NarrationRequest) -> dict:
    """Generate narration using local CosyVoice2."""
    if not COSYVOICE_AVAILABLE:
        raise HTTPException(status_code=500, detail="CosyVoice not available")
    if voice_model is None:
        load_voice_model()
    outputs: List[AudioItem] = []
    for line in req.lines:
        try:
            text = line.text or ""
            if not text.strip():
                audio, sr = generate_silence(0.2)
            else:
                audio, sr = synthesize(text, req.speaker, req.speed)
            path = save_audio(audio, sr, line.scene_id)
            outputs.append(AudioItem(scene_id=line.scene_id, audio=path, sample_rate=sr))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"TTS failed for {line.scene_id}: {exc}") from exc
    return {"audios": outputs}


def register_app(app: FastAPI, prefix: str = "") -> None:
    app.include_router(router, prefix=prefix)
    app.add_event_handler("startup", _startup)


def create_app() -> FastAPI:
    app = FastAPI(title="TTS Service (CosyVoice2 local)", version="0.2.0")
    register_app(app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("model.services.tts:app", host="0.0.0.0", port=8004, reload=False)
