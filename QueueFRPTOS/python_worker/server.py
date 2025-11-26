import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import time
import os
import uuid
from uploader import TosUploader
import json 

app = FastAPI()

class GenerateRequest(BaseModel):
    task_id: str
    type: str = "shot_generation"
    prompt: str
    params: dict = {}

class GenerateResponse(BaseModel):
    status: str
    result: dict = {}
    error: str = ""

@app.post("/generate", response_model=GenerateResponse)
async def generate_dispatch(req: GenerateRequest):
    print(f"Received task: {req.task_id}")
    print(f"Prompt: {req.prompt[:50]}...")
    print(f"Style: {req.params.get('style', 'default')}")
    
    output_filename = f"{req.task_id}.png" # 提前定义变量

    try:
        if req.type == "storyboard": ##LLM故事转分镜
            return handle_storyboard_task(req)
        elif req.type == "shot_generation":#单分镜生成或者重绘
            return handle_shot_generation_task(req)
        else:
            return GenerateResponse(status="failed", error=f"Unknown task type: {req.type}")
        
    except Exception as e:
        print(f"Task {req.task_id} failed: {e}")
        return GenerateResponse(status="failed", error=str(e))

def handle_storyboard_task(req: GenerateRequest):
    print(f"Analying story: {req.prompt[:30]}...")
    time.sleep(2) # 模拟 LLM 思考时间
    
    # 【模拟】这里应该调用 ChatGPT/DeepSeek API 分析 story_text
    # 构造符合 Go Processor 期望的 shots 列表结构
    # 实际开发中，这里是 LLM 的 JSON Output
    mock_shots = [
        {
            "title": "",
            "description": "",
            "prompt": ""
        },
        {
            "title": "",
            "description": "",
            "prompt": ""
        },
        {
            "title": "",
            "description": "",
            "prompt": ""
        }
    ]
    filename = f"storyboard_{req.task_id}.json"
    json_url = None

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({"shots": mock_shots}, f, ensure_ascii=False, indent=2)
            
        #上传
        uploader = TosUploader()
        if uploader.s3:
            json_url = uploader.upload_file(filename, object_key=f"scripts/{req.task_id}.json")
            print(f"Storyboard uploaded to: {json_url}")
        else:
            print("TOS uploader not configured, returning fake URL")
            json_url = f"https://fake-url.com/{filename}"

        return GenerateResponse(
            status="success",
            result={
                "shots": mock_shots,
                "url": json_url,
                "total_shots": len(mock_shots),
                "msg": "Storyboard generated and uploaded."
            }
        )
    except Exception as e:
        return GenerateResponse(status="failed", error=f"Failed to process storyboard: {str(e)}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)
        

def handle_shot_generation_task(req: GenerateRequest):
    print(f"Generating image for: {req.prompt[:30]}...")
    style = req.params.get('style', 'cinematic')
    
    # 定义文件名
    output_filename = f"{req.task_id}.png"
    
    try:
        time.sleep(3) 
        
        # 创建一个假图片用于测试
        with open(output_filename, "w") as f:
            f.write(f"Fake Image Content for {req.task_id}")
            
        try:
            uploader = TosUploader()
            cloud_object_key = f"generated/{req.task_id}.png"
            if uploader.s3:
                image_url = uploader.upload_file(output_filename, object_key=cloud_object_key)
            else:
                print("TOS uploader not configured, returning fake URL")
                image_url = f"https://fake-url.com/{output_filename}"
        except Exception as upload_err:
            print(f"Upload warning: {upload_err}")
            image_url = f"http://127.0.0.1:8080/temp/{output_filename}"

        return GenerateResponse(
            status="success",
            result={
                "images": [image_url], 
                "style": style
            }
        )
    finally:
        # 清理本地临时文件
        if os.path.exists(output_filename):
            os.remove(output_filename)
    
if __name__ == "__main__":
    print("Worker started on port 8080...")
    uvicorn.run(app, host="127.0.0.1", port=8080)
