"""Legacy endpoints router (/render, /tasks/*)."""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

# For now, import from main.py to avoid duplicating orchestration logic
# This allows incremental migration
from gateway.schemas import (
    RenderRequest,
    RenderResponse,
    TaskResponse,
    TASK_STATUS_PENDING,
    TASK_TYPE_VIDEO,
)

router = APIRouter(tags=["legacy"])

# Note: These routes are stubs that will be connected to the main.py logic
# during the incremental migration. The actual implementation remains in main.py
# until fully migrated.

# The following routes need to be preserved:
# POST /render -> render()
# GET /tasks/{task_id} -> task_status()
# GET /tasks/{task_id}/stream -> task_stream()

# For now, these are defined in main.py and will be migrated here incrementally.
