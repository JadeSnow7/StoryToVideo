"""V1 Projects router (/v1/projects/*)."""

from fastapi import APIRouter

# Note: These routes are currently defined in main.py
# This file serves as the target for incremental migration

router = APIRouter(prefix="/v1", tags=["v1"])

# Routes to be migrated:
# POST /v1/projects -> create_project()
# GET /v1/projects/{project_id} -> get_project()
# PUT /v1/projects/{project_id} -> update_project()
# DELETE /v1/projects/{project_id} -> delete_project()
# GET /v1/projects/{project_id}/shots -> list_shots()
# POST /v1/projects/{project_id}/shots/{shot_id} -> update_shot()
# GET /v1/projects/{project_id}/shots/{shot_id} -> get_shot()
# DELETE /v1/projects/{project_id}/shots/{shot_id} -> delete_shot()
# DELETE /v1/shots/{shot_id} -> delete_shot_direct()
# POST /v1/projects/{project_id}/tts -> generate_tts()
# POST /v1/projects/{project_id}/video -> generate_video()
