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
- 4 services already running locally:
  LLM        : http://localhost:8001/storyboard
  TXT2IMG    : http://localhost:8002/generate
  IMG2VID    : http://localhost:8003/img2vid
  TTS        : http://localhost:8004/narration
- ffmpeg available in PATH.
"""

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

import requests


# Default service endpoints
LLM_URL = "http://localhost:8001/storyboard"
TXT2IMG_URL = "http://localhost:8002/generate"
IMG2VID_URL = "http://localhost:8003/img2vid"
TTS_URL = "http://localhost:8004/narration"


def run_ffmpeg(cmd: List[str], desc: str) -> None:
    """执行 ffmpeg，失败直接抛异常。"""
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{desc} failed: {proc.stderr.strip()}")


def call_json_api(url: str, payload: Dict) -> Dict:
    resp = requests.post(url, json=payload, timeout=600)
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
        data = call_json_api(IMG2VID_URL, payload)
        video = data.get("video")
        if not video:
            raise RuntimeError(f"No video generated for {scene_id}")
        results.append((scene_id, video))
    return results


def step_tts(storyboard: List[Dict], speaker: str, speed: float) -> List[Tuple[str, str, int]]:
    """TTS 旁白，返回 (scene_id, audio_path, sample_rate)。"""
    lines = [{"scene_id": item["scene_id"], "text": item["narration"]} for item in storyboard]
    payload = {"lines": lines, "speaker": speaker or None, "speed": speed}
    data = call_json_api(TTS_URL, payload)
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


def concat_videos(video_paths: List[Path], out_path: Path) -> None:
    with tempfile.NamedTemporaryFile("w", delete=False) as tf:
        for path in video_paths:
            tf.write(f"file '{path.resolve().as_posix()}'\n")
        list_path = tf.name
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", str(out_path)]
    run_ffmpeg(cmd, "concat videos")


def orchestrate(args) -> Path:
    print("1) Storyboard...")
    storyboard = step_storyboard(args.story, args.style, args.scenes)

    print("2) TXT2IMG ...")
    frames = step_txt2img(storyboard, args.height, args.width, args.img_steps, args.cfg_scale)

    print("3) IMG2VID ...")
    clips = step_img2vid(frames, args.fps, args.video_frames)

    print("4) TTS ...")
    audios = step_tts(storyboard, args.speaker, args.speed)
    audio_map = {a[0]: a for a in audios}

    print("5) Mux and concat ...")
    tmp_dir = Path("data/final/tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    muxed_paths: List[Path] = []
    for scene_id, clip_path in clips:
        if scene_id not in audio_map:
            raise RuntimeError(f"Missing audio for scene {scene_id}")
        _, audio_path, _ = audio_map[scene_id]
        out_clip = tmp_dir / f"{scene_id}_mux.mp4"
        mux_clip_with_audio(clip_path, audio_path, out_clip)
        muxed_paths.append(out_clip)

    final_dir = Path("data/final")
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
    return p.parse_args()


def main():
    args = parse_args()
    try:
        final_path = orchestrate(args)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"✅ Done. Final video: {final_path}")


if __name__ == "__main__":
    main()
