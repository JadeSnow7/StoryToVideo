"""Utility functions for the Gateway services."""

import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# CJK character detection regex
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.utcnow().isoformat()


def has_cjk(text: str) -> bool:
    """Check if text contains CJK characters."""
    return bool(CJK_RE.search(text or ""))


def run_ffmpeg(cmd: List[str], desc: str) -> None:
    """Run an ffmpeg command and raise on failure."""
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{desc} failed: {proc.stderr.strip()}")


def to_file_url(path: str, static_root: Path) -> str:
    """Convert a local path to /files/... url if under static_root."""
    if not path:
        return ""
    p = Path(path).resolve()
    try:
        rel = p.relative_to(static_root)
        return f"/files/{rel.as_posix()}"
    except Exception:
        return p.as_posix()


def make_resource(url: str, rtype: str, rid: Optional[str] = None, meta: Optional[Dict] = None) -> Dict:
    """Create a resource dictionary."""
    import uuid
    rid_val = rid or Path(url).stem if url else (rid or str(uuid.uuid4()))
    res = {"resource_type": rtype, "resource_id": rid_val, "resource_url": url}
    if meta:
        res["meta"] = meta
    return res
