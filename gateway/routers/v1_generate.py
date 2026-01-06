"""V1 Generate and Jobs router (/v1/generate, /v1/jobs/*)."""

from fastapi import APIRouter

# Note: These routes are currently defined in main.py
# This file serves as the target for incremental migration

router = APIRouter(prefix="/v1", tags=["v1"])

# Routes to be migrated:
# POST /v1/generate -> generate_vi()
# GET /v1/jobs/{job_id} -> job_status()
# DELETE /v1/jobs/{job_id} -> stop_job()
