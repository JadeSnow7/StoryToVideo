"""FFmpeg-related utilities for video processing."""

import subprocess
from pathlib import Path
from typing import List


def run_ffmpeg(cmd: List[str], desc: str) -> None:
    """Run an ffmpeg command and raise on failure."""
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{desc} failed: {proc.stderr.strip()}")


def frame_to_video_fallback(
    frame_path: str, 
    scene_id: str, 
    fps: int, 
    num_frames: int,
    clips_dir: Path
) -> Path:
    """Create a static video from a single frame as fallback.
    
    If img2vid service is slow/unavailable, this creates a simple
    static video using ffmpeg.
    """
    clips_dir.mkdir(parents=True, exist_ok=True)
    out = clips_dir / f"{scene_id}_fallback.mp4"
    duration = max(num_frames / max(fps, 1), 0.5)
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-t",
        f"{duration:.2f}",
        "-i",
        frame_path,
        "-vf",
        f"fps={fps}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out),
    ]
    run_ffmpeg(cmd, f"fallback video for {scene_id}")
    return out
