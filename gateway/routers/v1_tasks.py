"""V1 Tasks router (/v1/tasks/*)."""

from fastapi import APIRouter

# Note: These routes are currently defined in main.py
# This file serves as the target for incremental migration

router = APIRouter(prefix="/v1", tags=["v1"])

# Routes to be migrated:
# GET /v1/tasks/{task_id} -> task_status_v1()
