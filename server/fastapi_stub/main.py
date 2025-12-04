from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid

app = FastAPI(title="StoryToVideo API Stub", version="0.1.0")

# In-memory stores for demo only
PROJECTS = {}
SHOTS = {}
TASKS = {}


class CreateProjectRequest(BaseModel):
    title: str
    story_text: str
    style: str


class ProjectResponse(BaseModel):
    project_id: str
    storyboard: List[dict]


class UpdatePromptRequest(BaseModel):
    prompt: Optional[str] = None
    narration: Optional[str] = None
    transition: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str


class ShotDefaults(BaseModel):
    shot_count: Optional[int] = None
    style: Optional[str] = None
    story_text: Optional[str] = None

    class Config:
        populate_by_name = True
        fields = {"story_text": "storyText"}


class ShotParam(BaseModel):
    transition: Optional[str] = None
    shot_id: Optional[str] = None
    image_width: Optional[str] = None
    image_height: Optional[str] = None
    prompt: Optional[str] = None

    class Config:
        populate_by_name = True
        fields = {
            "shot_id": "shotId",
            "image_width": "image_width",
            "image_height": "image_height",
        }


class VideoParam(BaseModel):
    resolution: Optional[str] = None
    fps: Optional[int] = None
    format: Optional[str] = None
    bitrate: Optional[int] = None


class TTSParam(BaseModel):
    voice: Optional[str] = None
    lang: Optional[str] = None
    sample_rate: Optional[int] = None
    format: Optional[str] = None


class Parameters(BaseModel):
    shot_defaults: Optional[ShotDefaults] = None
    shot: Optional[ShotParam] = None
    video: Optional[VideoParam] = None
    tts: Optional[TTSParam] = None


class ResultMeta(BaseModel):
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_url: Optional[str] = None


class GenerateRequest(BaseModel):
    id: Optional[str] = None
    project_id: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    message: Optional[str] = None
    parameters: Optional[Parameters] = None
    result: Optional[ResultMeta] = None
    error: Optional[str] = None
    estimatedDuration: Optional[int] = None
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

    class Config:
        populate_by_name = True
        fields = {"project_id": "projectId"}


class GenerateResponse(BaseModel):
    job_id: str
    message: str
    error: str


@app.post("/api/projects/create", response_model=ProjectResponse)
def create_project(req: CreateProjectRequest):
    project_id = str(uuid.uuid4())
    # Simple mock storyboard: 3 shots
    storyboard = []
    for i in range(3):
        shot_id = str(uuid.uuid4())
        SHOTS[shot_id] = {
            "id": shot_id,
            "project_id": project_id,
            "order": i,
            "prompt": f"Shot {i+1} description",
            "narration": "",
            "image_url": None,
            "status": "PENDING",
        }
        storyboard.append(SHOTS[shot_id])
    PROJECTS[project_id] = {"id": project_id, "title": req.title, "style": req.style}
    return {"project_id": project_id, "storyboard": storyboard}


@app.get("/api/projects/{project_id}/storyboard")
def get_storyboard(project_id: str):
    shots = [s for s in SHOTS.values() if s["project_id"] == project_id]
    if not shots:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project_id": project_id, "shots": shots}


@app.post("/api/shots/{shot_id}/update_prompt")
def update_prompt(shot_id: str, req: UpdatePromptRequest):
    shot = SHOTS.get(shot_id)
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    if req.prompt:
        shot["prompt"] = req.prompt
    if req.narration:
        shot["narration"] = req.narration
    if req.transition:
        shot["transition"] = req.transition
    return shot


def _create_task(task_type: str, payload: dict):
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "id": task_id,
        "type": task_type,
        "payload": payload,
        "status": "RUNNING",
        "progress": 0,
        "result": None,
        "error": None,
    }
    # In a real system, enqueue async job. Here we mark success immediately.
    TASKS[task_id]["status"] = "SUCCESS"
    TASKS[task_id]["progress"] = 100
    TASKS[task_id]["result"] = {"url": "https://example.com/mock.png"}
    return task_id


@app.post("/api/shots/{shot_id}/generate_image", response_model=TaskResponse)
def generate_image(shot_id: str):
    shot = SHOTS.get(shot_id)
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    task_id = _create_task("SD", {"shot_id": shot_id})
    shot["status"] = "RUNNING"
    shot["task_id"] = task_id
    return {"task_id": task_id}


@app.get("/api/tasks/{task_id}/status")
def task_status(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/api/webhook/task_complete")
def task_complete(task_id: str, result_url: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task["status"] = "SUCCESS"
    task["progress"] = 100
    task["result"] = {"url": result_url}
    return {"ok": True}


@app.post("/vi/api/generate", response_model=GenerateResponse)
def generate_vi(req: GenerateRequest):
    # Stub: accept payload, create a job id, store minimal task info.
    job_id = str(uuid.uuid4())
    TASKS[job_id] = {
        "id": job_id,
        "payload": req.dict(by_alias=True),
        "status": "RECEIVED",
        "progress": req.progress or 0,
        "error": None,
    }
    return {"job_id": job_id, "message": "accepted", "error": ""}
