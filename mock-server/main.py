"""
本地模拟服务端 - 用于客户端开发测试
完全模拟 Go Server 的业务流程

业务流程：
1. POST /v1/api/projects -> 创建项目，返回 project_id, text_task_id, shot_task_ids
2. GET /v1/api/tasks/:task_id -> 查询任务状态
3. GET /v1/api/projects/:project_id/shots -> 获取分镜列表
4. POST /v1/api/projects/:project_id/video -> 触发视频生成
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="StoryToVideo Mock Server", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 常量定义 ====================

# 任务类型
TASK_TYPE_PROJECT_TEXT = "project_text"
TASK_TYPE_SHOT_IMAGE = "shot_image"
TASK_TYPE_PROJECT_VIDEO = "project_video"
TASK_TYPE_PROJECT_AUDIO = "project_audio"

# 任务状态
TASK_STATUS_PENDING = "pending"
TASK_STATUS_BLOCKED = "blocked"
TASK_STATUS_PROCESSING = "processing"
TASK_STATUS_FINISHED = "finished"
TASK_STATUS_FAILED = "failed"

# 项目状态
PROJECT_STATUS_CREATED = "created"
PROJECT_STATUS_TEXT_GENERATED = "text_generated"
PROJECT_STATUS_READY = "ready"

# 分镜状态
SHOT_STATUS_PENDING = "pending"
SHOT_STATUS_PROCESSING = "processing"
SHOT_STATUS_COMPLETED = "completed"
SHOT_STATUS_FAILED = "failed"

# ==================== 数据模型 ====================

class TaskResult(BaseModel):
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_url: Optional[str] = None

class Task(BaseModel):
    id: str
    project_id: str
    shot_id: Optional[str] = None
    type: str
    status: str
    progress: int = 0
    message: str = ""
    parameters: Optional[Dict] = None
    result: Optional[TaskResult] = None
    created_at: str
    updated_at: str

class Shot(BaseModel):
    id: str
    project_id: str
    order: int
    title: str
    description: str
    prompt: str
    narration: str = ""
    image_path: str = ""
    video_path: str = ""
    audio_path: str = ""
    transition: str = "cut"
    duration: float = 3.0
    status: str = SHOT_STATUS_PENDING
    created_at: str
    updated_at: str

class Project(BaseModel):
    id: str
    title: str
    story_text: str
    style: str
    description: str = ""
    status: str = PROJECT_STATUS_CREATED
    cover_image: str = ""
    video_url: str = ""
    duration: float = 0
    shot_count: int = 0
    created_at: str
    updated_at: str

# ==================== 内存存储 ====================

projects: Dict[str, Project] = {}
tasks: Dict[str, Task] = {}
shots: Dict[str, Shot] = {}  # key: shot_id
project_shots: Dict[str, List[str]] = {}  # key: project_id, value: [shot_ids]

# ==================== 工具函数 ====================

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

def generate_mock_shots(project_id: str, story_text: str, style: str) -> List[Shot]:
    """模拟 LLM 生成分镜"""
    # 简单地按句号分割故事，生成分镜
    sentences = [s.strip() for s in story_text.replace("。", ".").split(".") if s.strip()]
    if not sentences:
        sentences = ["默认场景"]
    
    # 最多生成 5 个分镜
    sentences = sentences[:5]
    
    result = []
    for i, sentence in enumerate(sentences):
        now = now_iso()
        shot = Shot(
            id=str(uuid.uuid4()),
            project_id=project_id,
            order=i + 1,
            title=f"分镜 {i + 1}",
            description=sentence[:50] if len(sentence) > 50 else sentence,
            prompt=f"{style} style, {sentence}",
            narration=sentence,
            status=SHOT_STATUS_PENDING,
            created_at=now,
            updated_at=now
        )
        result.append(shot)
    
    return result

async def simulate_task_execution(task_id: str, duration: float = 3.0):
    """模拟任务执行过程"""
    task = tasks.get(task_id)
    if not task:
        return
    
    # 更新状态为 processing
    task.status = TASK_STATUS_PROCESSING
    task.progress = 0
    task.message = "正在处理..."
    task.updated_at = now_iso()
    
    # 模拟进度更新
    steps = 10
    for i in range(steps):
        await asyncio.sleep(duration / steps)
        task.progress = int((i + 1) / steps * 100)
        task.message = f"处理中 {task.progress}%"
        task.updated_at = now_iso()
    
    # 任务完成
    task.status = TASK_STATUS_FINISHED
    task.progress = 100
    task.message = "完成"
    task.updated_at = now_iso()
    
    # 根据任务类型设置结果
    if task.type == TASK_TYPE_PROJECT_TEXT:
        # 文本任务完成后，生成分镜并解锁 shot_image 任务
        project = projects.get(task.project_id)
        if project:
            mock_shots = generate_mock_shots(task.project_id, project.story_text, project.style)
            project_shots[task.project_id] = []
            
            for shot in mock_shots:
                shots[shot.id] = shot
                project_shots[task.project_id].append(shot.id)
            
            project.shot_count = len(mock_shots)
            project.status = PROJECT_STATUS_TEXT_GENERATED
            project.updated_at = now_iso()
            
            # 解锁并执行 shot_image 任务
            shot_ids = project_shots[task.project_id]
            for t in tasks.values():
                if t.project_id == task.project_id and t.type == TASK_TYPE_SHOT_IMAGE:
                    if t.parameters and t.parameters.get("depends_on") == task_id:
                        # 找到对应的 shot 并更新参数
                        shot_order = t.parameters.get("shot_order", 1)
                        if shot_order <= len(shot_ids):
                            shot_id = shot_ids[shot_order - 1]
                            shot = shots.get(shot_id)
                            if shot:
                                t.shot_id = shot_id
                                t.parameters["shot_id"] = shot_id
                                t.parameters["prompt"] = shot.prompt
                        
                        t.status = TASK_STATUS_PENDING
                        t.updated_at = now_iso()
                        # 异步执行
                        asyncio.create_task(simulate_task_execution(t.id, 2.0))
    
    elif task.type == TASK_TYPE_SHOT_IMAGE:
        # 图片任务完成，更新 shot 的 image_path
        shot = shots.get(task.shot_id) if task.shot_id else None
        if shot:
            # 使用模拟图片 URL
            image_url = f"https://picsum.photos/seed/{task.shot_id}/512/512"
            shot.image_path = image_url
            shot.status = SHOT_STATUS_COMPLETED
            shot.updated_at = now_iso()
            
            task.result = TaskResult(
                resource_type="image",
                resource_id=task.shot_id,
                resource_url=image_url
            )
        
        # 检查是否所有分镜都完成
        project = projects.get(task.project_id)
        if project:
            shot_ids = project_shots.get(task.project_id, [])
            all_completed = all(
                shots.get(sid) and shots[sid].status == SHOT_STATUS_COMPLETED
                for sid in shot_ids
            )
            if all_completed:
                project.status = PROJECT_STATUS_READY
                project.updated_at = now_iso()
    
    elif task.type == TASK_TYPE_PROJECT_VIDEO:
        # 视频任务完成
        task.result = TaskResult(
            resource_type="video",
            resource_id=task.project_id,
            resource_url=f"https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"
        )
        project = projects.get(task.project_id)
        if project:
            project.video_url = task.result.resource_url
            project.updated_at = now_iso()

# ==================== API 接口 ====================

@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-server"}

# ---------- 项目接口 ----------

@app.post("/v1/api/projects")
async def create_project(
    Title: Optional[str] = None,
    StoryText: Optional[str] = None, 
    Style: Optional[str] = None,
    Description: Optional[str] = None,
    Desription: Optional[str] = None,  # 兼容客户端拼写错误
    background_tasks: BackgroundTasks = None
):
    """
    创建项目 - 支持 Query 参数格式（客户端使用）
    返回: project_id, text_task_id, shot_task_ids
    """
    # 兼容拼写错误
    if Desription and not Description:
        Description = Desription
    
    now = now_iso()
    project_id = str(uuid.uuid4())
    
    # 创建项目
    project = Project(
        id=project_id,
        title=Title or "未命名项目",
        story_text=StoryText or "",
        style=Style or "电影",
        description=Description or "",
        status=PROJECT_STATUS_CREATED,
        created_at=now,
        updated_at=now
    )
    projects[project_id] = project
    
    # 创建 text 任务
    text_task_id = str(uuid.uuid4())
    text_task = Task(
        id=text_task_id,
        project_id=project_id,
        type=TASK_TYPE_PROJECT_TEXT,
        status=TASK_STATUS_PENDING,
        progress=0,
        message="等待执行",
        parameters={"story_text": StoryText, "style": Style},
        created_at=now,
        updated_at=now
    )
    tasks[text_task_id] = text_task
    
    # 创建 n 个 shot_image 任务 (初始为 blocked)
    shot_count = 5  # 预估分镜数
    shot_task_ids = []
    for i in range(shot_count):
        shot_task_id = str(uuid.uuid4())
        shot_task = Task(
            id=shot_task_id,
            project_id=project_id,
            type=TASK_TYPE_SHOT_IMAGE,
            status=TASK_STATUS_BLOCKED,
            progress=0,
            message="等待文本任务完成",
            parameters={
                "depends_on": text_task_id,
                "shot_order": i + 1
            },
            created_at=now,
            updated_at=now
        )
        tasks[shot_task_id] = shot_task
        shot_task_ids.append(shot_task_id)
    
    # 异步执行文本任务
    asyncio.create_task(simulate_task_execution(text_task_id, 3.0))
    
    return {
        "project_id": project_id,
        "text_task_id": text_task_id,
        "shot_task_ids": shot_task_ids
    }

@app.get("/v1/api/projects/{project_id}")
async def get_project(project_id: str):
    """获取项目详情"""
    project = projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project.model_dump()}

@app.get("/v1/api/projects/{project_id}/shots")
async def get_shots(project_id: str):
    """获取项目的分镜列表"""
    shot_ids = project_shots.get(project_id, [])
    result = []
    for shot_id in shot_ids:
        shot = shots.get(shot_id)
        if shot:
            result.append({
                "id": shot.id,
                "order": shot.order,
                "title": shot.title,
                "description": shot.description,
                "prompt": shot.prompt,
                "narration": shot.narration,
                "imagePath": shot.image_path,
                "imageUrl": shot.image_path,  # 兼容客户端
                "videoPath": shot.video_path,
                "audioPath": shot.audio_path,
                "transition": shot.transition,
                "duration": shot.duration,
                "status": shot.status
            })
    return {"shots": result}

@app.get("/v1/api/projects/{project_id}/shots/{shot_id}")
async def get_shot_detail(project_id: str, shot_id: str):
    """获取单个分镜详情"""
    shot = shots.get(shot_id)
    if not shot or shot.project_id != project_id:
        raise HTTPException(status_code=404, detail="Shot not found")
    return {"shot": shot.model_dump()}

# ---------- 任务接口 ----------

@app.get("/v1/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态"""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    result = {
        "task": {
            "id": task.id,
            "project_id": task.project_id,
            "shot_id": task.shot_id,
            "type": task.type,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "parameters": task.parameters,
            "result": task.result.model_dump() if task.result else None,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
    }
    return result

# ---------- 视频生成接口 ----------

@app.post("/v1/api/projects/{project_id}/video")
async def generate_video(project_id: str):
    """触发视频生成任务"""
    project = projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    now = now_iso()
    video_task_id = str(uuid.uuid4())
    video_task = Task(
        id=video_task_id,
        project_id=project_id,
        type=TASK_TYPE_PROJECT_VIDEO,
        status=TASK_STATUS_PENDING,
        progress=0,
        message="等待执行",
        created_at=now,
        updated_at=now
    )
    tasks[video_task_id] = video_task
    
    # 异步执行
    asyncio.create_task(simulate_task_execution(video_task_id, 5.0))
    
    return {"task_id": video_task_id}

# ==================== 启动服务 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8888)
