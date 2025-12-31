"""Shared helpers for model services."""

import os
from pathlib import Path


def resolve_project_root() -> Path:
    """Return the project root for locating data/models.

    Priority:
    1) MODEL_ROOT env (absolute or relative path).
    2) First parent containing markers like data/pretrained_models/CosyVoice/README.md.
    3) Parent of the current file (best-effort fallback).
    """
    env_root = os.getenv("MODEL_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    here = Path(__file__).resolve()
    markers = {"data", "pretrained_models", "CosyVoice", "README.md"}
    for parent in here.parents:
        for marker in markers:
            if (parent / marker).exists():
                return parent
    return here.parent
