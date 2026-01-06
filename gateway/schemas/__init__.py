"""Schemas package initialization.

Re-exports all schema models for convenient importing.
"""

from gateway.schemas.task import (
    TaskState,
    TaskSchema,
    TaskParameters,
    TaskShotParameters,
    TaskVideoParameters,
    TaskResult,
    TaskShotsResult,
    TaskAudioResult,
    TaskVideoResult,
    TaskResponse,
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

from gateway.schemas.generate import (
    RenderRequest,
    RenderResponse,
    ShotDefaults,
    ShotParam,
    VideoParam,
    TTSParam,
    GenerateParameters,
    GeneratePayload,
)

from gateway.schemas.project import (
    ShotSchema,
)

__all__ = [
    # Task
    "TaskState",
    "TaskSchema",
    "TaskParameters",
    "TaskShotParameters",
    "TaskVideoParameters",
    "TaskResult",
    "TaskShotsResult",
    "TaskAudioResult",
    "TaskVideoResult",
    "TaskResponse",
    # Task constants
    "TASK_STATUS_PENDING",
    "TASK_STATUS_BLOCKED",
    "TASK_STATUS_PROCESSING",
    "TASK_STATUS_FINISHED",
    "TASK_STATUS_FAILED",
    "TASK_STATUS_CANCELLED",
    "TASK_TYPE_STORYBOARD",
    "TASK_TYPE_SHOT",
    "TASK_TYPE_AUDIO",
    "TASK_TYPE_VIDEO",
    # Generate
    "RenderRequest",
    "RenderResponse",
    "ShotDefaults",
    "ShotParam",
    "VideoParam",
    "TTSParam",
    "GenerateParameters",
    "GeneratePayload",
    # Project
    "ShotSchema",
]
