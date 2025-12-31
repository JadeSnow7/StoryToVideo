#!/usr/bin/env python3
"""
End-to-end orchestration script:
- Story text -> storyboard (LLM service)
- Prompts -> keyframes (txt2img service)
- Keyframes -> clips (img2vid service)
- Narration -> audio (tts service)
- ffmpeg mux + concat -> final MP4
中文：一键串联 LLM 分镜、文生图、图生视频、TTS，并用 ffmpeg 复用后拼接成片。

Prerequisites:
- 模型节点已启动（默认 http://localhost:8000）：
  LLM        : /llm/storyboard
  TXT2IMG    : /txt2img/generate
  IMG2VID    : /img2vid/generate
  TTS        : /tts/narration
- 或通过 LLM_URL/TXT2IMG_URL/IMG2VID_URL/TTS_URL 定制完整地址。
- ffmpeg available in PATH.
"""

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

import requests
import soundfile as sf
from model.services.utils import resolve_project_root

PROJECT_ROOT = resolve_project_root()
DATA_ROOT = PROJECT_ROOT / "data"

DEFAULT_BASE_URL = os.getenv("MODEL_BASE_URL", "http://localhost:8000").rstrip("/")
LLM_URL = os.getenv("LLM_URL", f"{DEFAULT_BASE_URL}/llm/storyboard")
TXT2IMG_URL = os.getenv("TXT2IMG_URL", f"{DEFAULT_BASE_URL}/txt2img/generate")
IMG2VID_URL = os.getenv("IMG2VID_URL", f"{DEFAULT_BASE_URL}/img2vid/generate")
TTS_URL = os.getenv("TTS_URL", f"{DEFAULT_BASE_URL}/tts/narration")


def set_endpoints(
    base_url: str,
    llm_url: str | None,
    txt2img_url: str | None,
    img2vid_url: str | None,
    tts_url: str | None,
) -> None:
    """Update global endpoint URLs from CLI/env."""
    base = (base_url or DEFAULT_BASE_URL).rstrip("/")
    global LLM_URL, TXT2IMG_URL, IMG2VID_URL, TTS_URL  # noqa: PLW0603
    LLM_URL = llm_url or f"{base}/llm/storyboard"
    TXT2IMG_URL = txt2img_url or f"{base}/txt2img/generate"
    IMG2VID_URL = img2vid_url or f"{base}/img2vid/generate"
    TTS_URL = tts_url or f"{base}/tts/narration"


def run_ffmpeg(cmd: List[str], desc: str) -> None:
    """执行 ffmpeg，失败直接抛异常。"""
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{desc} failed: {proc.stderr.strip()}")


def call_json_api(url: str, payload: Dict, timeout: int = 600) -> Dict:
    resp = requests.post(url, json=payload, timeout=timeout)
    if not resp.ok:
        raise RuntimeError(f"API call {url} failed: {resp.status_code} {resp.text}")
    try:
        return resp.json()
    except Exception as exc:
        raise RuntimeError(f"API {url} returned non-JSON: {resp.text}") from exc


def step_storyboard(story: str, style: str, scenes: int) -> List[Dict]:
    """调用 LLM 拆分分镜。"""
    payload = {"story": story, "style": style, "scenes": scenes}
    data = call_json_api(LLM_URL, payload)
    sb = data.get("storyboard")
    if not sb:
        raise RuntimeError("Storyboard empty")
    return sb


def step_txt2img(storyboard: List[Dict], height: int, width: int, steps: int, cfg: float) -> List[Tuple[str, str]]:
    """文生图，返回 (scene_id, frame_path)。"""
    results = []
    for item in storyboard:
        scene_id = item["scene_id"]
        prompt = item["prompt"]
        payload = {
            "prompt": prompt,
            "scene_id": scene_id,
            "style": {
                "width": width,
                "height": height,
                "num_inference_steps": steps,
                "guidance_scale": cfg,
            },
        }
        data = call_json_api(TXT2IMG_URL, payload)
        images = data.get("images") or []
        if not images:
            raise RuntimeError(f"No image generated for {scene_id}")
        results.append((scene_id, images[0]["path"]))
    return results


def step_img2vid(frames: List[Tuple[str, str]], fps: int, num_frames: int) -> List[Tuple[str, str]]:
    """图生视频，返回 (scene_id, clip_path)。"""
    results = []
    for scene_id, frame_path in frames:
        payload = {
            "frame": frame_path,
            "scene_id": scene_id,
            "fps": fps,
            "num_frames": num_frames,
        }
        # img2vid 较慢，单独延长超时时间
        data = call_json_api(IMG2VID_URL, payload, timeout=1200)
        video = data.get("video")
        if not video:
            raise RuntimeError(f"No video generated for {scene_id}")
        results.append((scene_id, video))
    return results


def step_tts(storyboard: List[Dict], speaker: str, speed: float) -> List[Tuple[str, str, int]]:
    """TTS 旁白，返回 (scene_id, audio_path, sample_rate)。"""
    lines = [{"scene_id": item["scene_id"], "text": item["narration"]} for item in storyboard]
    payload = {"lines": lines, "speaker": speaker or None, "speed": speed}
    # TTS 可能较慢，拉长超时。
    data = call_json_api(TTS_URL, payload, timeout=1200)
    audios = data.get("audios") or []
    if len(audios) != len(lines):
        raise RuntimeError(f"TTS count mismatch: expected {len(lines)}, got {len(audios)}")
    return [(a["scene_id"], a["audio"], a.get("sample_rate", 44100)) for a in audios]


def mux_clip_with_audio(clip: str, audio: str, out_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        clip,
        "-i",
        audio,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(out_path),
    ]
    run_ffmpeg(cmd, f"mux {clip} + {audio}")


def audio_duration_seconds(audio_path: str) -> float:
    """Return audio duration in seconds."""
    try:
        info = sf.info(audio_path)
        if info.frames and info.samplerate:
            return info.frames / float(info.samplerate)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to read audio duration for {audio_path}: {exc}") from exc
    raise RuntimeError(f"Audio duration unavailable for {audio_path}")


def normalize_storyboard(scenes: int, storyboard: List[Dict]) -> List[Dict]:
    """Trim or pad storyboard to the expected scene count, keeping sequential scene_id."""
    if not storyboard:
        return []
    trimmed = storyboard[:scenes]
    if len(trimmed) < scenes:
        last = trimmed[-1] if trimmed else {"title": "Scene", "prompt": "", "narration": "", "bgm": None}
        for idx in range(len(trimmed) + 1, scenes + 1):
            trimmed.append(
                {
                    "scene_id": f"s{idx}",
                    "title": last.get("title") or f"Scene {idx}",
                    "prompt": last.get("prompt") or last.get("narration") or "placeholder frame",
                    "narration": last.get("narration") or "",
                    "bgm": last.get("bgm"),
                }
            )
    # reassign scene_id sequentially to avoid duplicates
    for idx, item in enumerate(trimmed, start=1):
        item["scene_id"] = f"s{idx}"
    return trimmed


def concat_videos(video_paths: List[Path], out_path: Path) -> None:
    with tempfile.NamedTemporaryFile("w", delete=False) as tf:
        for path in video_paths:
            tf.write(f"file '{path.resolve().as_posix()}'\n")
        list_path = tf.name
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_path,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "main",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    run_ffmpeg(cmd, "concat videos")


def orchestrate(args) -> Path:
    print(
        "使用的服务地址: "
        f"LLM={LLM_URL}, TXT2IMG={TXT2IMG_URL}, IMG2VID={IMG2VID_URL}, TTS={TTS_URL}"
    )
    print("1) Storyboard...")
    storyboard: List[Dict] = []
    for attempt in range(3):
        storyboard = step_storyboard(args.story, args.style, args.scenes)
        if len(storyboard) == args.scenes:
            break
        print(f"[WARN] Storyboard scenes mismatch: expected {args.scenes}, got {len(storyboard)}; retry {attempt+1}/3")
    if not storyboard:
        raise RuntimeError("Storyboard empty after retries")
    if len(storyboard) != args.scenes:
        print(f"[WARN] Normalizing storyboard to {args.scenes} scenes (current {len(storyboard)})")
        storyboard = normalize_storyboard(args.scenes, storyboard)

    print("2) TTS ...")
    audios = step_tts(storyboard, args.speaker, args.speed)
    audio_map: Dict[str, Dict] = {}
    for scene_id, audio_path, sr in audios:
        duration = audio_duration_seconds(audio_path)
        audio_map[scene_id] = {"path": audio_path, "sample_rate": sr, "duration": duration}

    print("3) TXT2IMG ...")
    frames = step_txt2img(storyboard, args.height, args.width, args.img_steps, args.cfg_scale)

    print("4) IMG2VID ...")
    effective_fps = min(max(args.fps, 4), 30)
    clips: List[Tuple[str, str]] = []
    for scene_id, frame_path in frames:
        audio_meta = audio_map.get(scene_id)
        if not audio_meta:
            raise RuntimeError(f"Missing audio for scene {scene_id}")
        # 使用音频时长确保视频不短于旁白
        desired_frames = max(args.video_frames, math.ceil(audio_meta["duration"] * effective_fps))
        num_frames = min(desired_frames, 48)  # API 上限 48
        clip = step_img2vid([(scene_id, frame_path)], effective_fps, num_frames)[0]
        clips.append(clip)

    print("5) Mux and concat ...")
    tmp_dir = DATA_ROOT / "final/tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    muxed_paths: List[Path] = []
    for scene_id, clip_path in clips:
        if scene_id not in audio_map:
            raise RuntimeError(f"Missing audio for scene {scene_id}")
        audio_path = audio_map[scene_id]["path"]
        out_clip = tmp_dir / f"{scene_id}_mux.mp4"
        mux_clip_with_audio(clip_path, audio_path, out_clip)
        muxed_paths.append(out_clip)

    final_dir = DATA_ROOT / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    final_path = final_dir / f"final_{int(time.time())}.mp4"
    concat_videos(muxed_paths, final_path)
    return final_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run full pipeline: story -> video")
    p.add_argument("--story", required=True, help="故事文本")
    p.add_argument("--style", default="", help="可选风格描述")
    p.add_argument("--scenes", type=int, default=4, help="分镜数量")
    p.add_argument("--height", type=int, default=512, help="生成图片高度")
    p.add_argument("--width", type=int, default=768, help="生成图片宽度")
    p.add_argument("--img-steps", type=int, default=4, help="文生图推理步数")
    p.add_argument("--cfg-scale", type=float, default=1.5, help="guidance scale")
    p.add_argument("--fps", type=int, default=12, help="生成视频 fps")
    p.add_argument("--video-frames", type=int, default=16, help="生成视频总帧数")
    p.add_argument("--speaker", default="", help="TTS 说话人，不填则用默认")
    p.add_argument("--speed", type=float, default=1.0, help="TTS 语速 0.5~2.0")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL, help="模型节点基础地址（默认 env MODEL_BASE_URL 或 http://localhost:8000）")
    p.add_argument("--llm-url", default=os.getenv("LLM_URL"), help="完整 LLM 地址，覆盖 base-url")
    p.add_argument("--txt2img-url", default=os.getenv("TXT2IMG_URL"), help="完整 TXT2IMG 地址，覆盖 base-url")
    p.add_argument("--img2vid-url", default=os.getenv("IMG2VID_URL"), help="完整 IMG2VID 地址，覆盖 base-url")
    p.add_argument("--tts-url", default=os.getenv("TTS_URL"), help="完整 TTS 地址，覆盖 base-url")
    return p.parse_args()


def main():
    args = parse_args()
    set_endpoints(args.base_url, args.llm_url, args.txt2img_url, args.img2vid_url, args.tts_url)
    try:
        final_path = orchestrate(args)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"✅ Done. Final video: {final_path}")


if __name__ == "__main__":
    main()
