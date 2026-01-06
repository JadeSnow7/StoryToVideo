"""Task orchestration service.

This module handles the core task orchestration logic for the Gateway.
It coordinates calls to downstream services (LLM, TXT2IMG, IMG2VID, TTS)
and manages task state updates.

Note: The actual orchestration logic is currently in main.py.
This file serves as the target module for incremental migration.
The migration should:
1. Move _orchestrate() and related helper functions here
2. Update main.py to import from this module
3. Gradually decouple dependencies
"""

import copy
from datetime import datetime
from typing import Dict, List, Optional

# Re-export constants that will be used by orchestrator
from gateway.schemas.task import (
    TASK_STATUS_PENDING,
    TASK_STATUS_BLOCKED,
    TASK_STATUS_PROCESSING,
    TASK_STATUS_FINISHED,
    TASK_STATUS_FAILED,
    TASK_STATUS_CANCELLED,
    TASK_TYPE_STORYBOARD,
    TASK_TYPE_SHOT,
    TASK_TYPE_AUDIO,
    TASK_TYPE_VIDEO,
)


def default_parameters() -> Dict:
    """Return default task parameters structure."""
    return {
        "shot": {
            "style": "",
            "text_llm": "",
            "image_llm": "",
            "generate_tts": False,
            "shot_count": 0,
            "image_width": 0,
            "image_height": 0,
            "negative_prompt": "",
        },
        "video": {
            "format": "",
            "resolution": "",
            "fps": "",
            "transition_effects": "",
        },
    }


def default_result() -> Dict:
    """Return default task result structure."""
    return {
        "resource_type": "",
        "resource_id": "",
        "resource_url": "",
        "resources": [],
        "legacy": {
            "task_shots": {"generated_shots": [], "total_shots": 0, "total_time": 0.0},
            "task_audio": {"generated_audios": [], "total_audios": 0, "total_time": 0.0},
            "task_video": {"path": "", "duration": "", "fps": "", "resolution": "", "format": "", "total_time": "", "clips": []},
        },
    }


def deep_merge_dict(base: Dict, updates: Dict) -> Dict:
    """Deep merge two dictionaries."""
    if hasattr(base, "model_dump"):
        base = base.model_dump()
    if hasattr(updates, "model_dump"):
        updates = updates.model_dump()
    merged = copy.deepcopy(base if isinstance(base, dict) else {})
    if not isinstance(updates, dict):
        return merged
    for key, val in updates.items():
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dict(merged.get(key, {}), val)
        else:
            merged[key] = val
    return merged


def normalize_parameters(params: Optional[Dict]) -> Dict:
    """Normalize task parameters with defaults."""
    return deep_merge_dict(default_parameters(), params or {})


def normalize_result(result: Optional[Dict]) -> Dict:
    """Normalize task result with defaults."""
    base = default_result()
    if result is None:
        return base
    merged = deep_merge_dict(base, result)
    merged.setdefault("resources", [])
    merged.setdefault("legacy", default_result().get("legacy", {}))
    return merged


# The main orchestrate function will be migrated here
# async def orchestrate(task_id: str, task_type: str, ctx: Dict) -> None:
#     """Main orchestration function for task execution."""
#     pass
