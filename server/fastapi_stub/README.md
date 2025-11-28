# Server Layer / 服务端

Preferred stack: Django + DRF + Nginx + Gunicorn + PostgreSQL + task queue. FastAPI stub provided for rapid client integration; swap with production stack per PRD.  
推荐栈：Django + DRF + Nginx + Gunicorn + PostgreSQL + 任务队列。提供 FastAPI 桩便于快速联调，正式请替换为生产实现。

## FastAPI stub (dev only) / 开发桩
```bash
cd server/fastapi_stub
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Django (reference) / 参考步骤
1) `python -m venv .venv && source .venv/bin/activate`  
2) `pip install django djangorestframework gunicorn psycopg2-binary`  
3) `django-admin startproject api .` (fresh)  
4) 创建 projects/shots/tasks 应用，DRF viewsets，JWT 鉴权。  
5) Celery/RQ 处理异步；配置 Redis/AMQP。  
6) Nginx 反代 Gunicorn；设置 `ALLOWED_HOSTS` 与静态目录。

## API Surface (MVP) / API 范围
- POST `/api/projects/create`
- GET `/api/projects/{id}/storyboard`
- POST `/api/shots/{id}/update_prompt`
- POST `/api/shots/{id}/generate_image`
- POST `/api/shots/{id}/generate_video` (optional 可选)
- GET `/api/tasks/{task_id}/status`
- POST `/api/webhook/task_complete`

## Storage / 存储
- DB: PostgreSQL/MySQL
- Assets: OSS/TOS (images/video/audio)

## FRP
- Use FRP to expose local model node endpoints to cloud server; sample in `../frp`.  
  使用 FRP 将本地模型端口暴露给云端服务，示例见 `../frp`。
