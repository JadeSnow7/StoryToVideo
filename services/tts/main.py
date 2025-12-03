"""
FastAPI TTS service using local CosyVoice2 models (bypassing ModelScope pipeline).
"""

import os
import sys
import time
import uuid
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Ensure local CosyVoice repo is importable
ROOT = Path(__file__).resolve().parents[2]  # repo root
COSYVOICE_ROOT = ROOT / "CosyVoice"
if COSYVOICE_ROOT.exists() and str(COSYVOICE_ROOT) not in sys.path:
    sys.path.insert(0, str(COSYVOICE_ROOT))

from cosyvoice.cli.cosyvoice import CosyVoice2  # type: ignore  # noqa: E402


MODEL_ID = os.getenv(
    "MODEL_ID",
    str(ROOT / "pretrained_models" / "CosyVoice2-0.5B" / "iic" / "CosyVoice2-0___5B"),
)
DEVICE = os.getenv("DEVICE", "cuda")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "data/audio"))
ZERO_SHOT_AUDIO = ROOT / "CosyVoice" / "asset" / "zero_shot_prompt.wav"
ZERO_SHOT_TEXT = "希望你以后能够做的比我还好呦。"
ZERO_SHOT_ID = "zero_shot_demo"

app = FastAPI(title="TTS Service (CosyVoice2 local)", version="0.2.0")

voice_model: Optional[CosyVoice2] = None
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
    # pick first available speaker if not provided later
    try:
        spks = voice_model.list_available_spks() or []
    except Exception:
        spks = []

    def _ensure_embedding(spk_id: str) -> None:
        entry = voice_model.frontend.spk2info.get(spk_id)
        if entry and "embedding" not in entry and "llm_embedding" in entry:
            entry["embedding"] = entry["llm_embedding"]

    # If no speakers bundled, bootstrap a zero-shot speaker from the repo demo audio.
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
    # CosyVoice2.inference_sft yields generator; take first chunk
    gen = voice_model.inference_sft(tts_text=text, spk_id=spk, stream=False, speed=speed)
    audio_np = None
    for out in gen:
        audio_np = out["tts_speech"]
        break
    if audio_np is None:
        raise RuntimeError("CosyVoice2 returned empty audio")
    return audio_np.squeeze(), voice_model.sample_rate


def generate_silence(duration_sec: float) -> (np.ndarray, int):
    """Return a short silent clip to tolerate empty narration."""
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


@app.on_event("startup")
async def _startup():
    load_voice_model()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": MODEL_ID,
        "device": DEVICE,
        "output_dir": str(OUTPUT_DIR),
        "default_speaker": default_speaker,
        "available_speakers": available_speakers,
    }


@app.post("/narration", response_model=NarrationResponse)
async def narration(req: NarrationRequest):
    if not req.lines:
        raise HTTPException(status_code=400, detail="lines is empty")
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
            # override sample rate if caller forces one via resample? (not implemented; ignore)
            path = save_audio(audio, sr, line.scene_id)
            outputs.append(AudioItem(scene_id=line.scene_id, audio=path, sample_rate=sr))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"TTS failed for {line.scene_id}: {exc}") from exc
    return {"audios": outputs}


# Run directly: python services/tts/main.py
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("services.tts.main:app", host="0.0.0.0", port=8004, reload=False)
