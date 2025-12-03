from fastapi.testclient import TestClient

from server.fastapi_stub.main import app, PROJECTS, SHOTS, TASKS


client = TestClient(app)


def _reset_state():
    PROJECTS.clear()
    SHOTS.clear()
    TASKS.clear()


def test_create_project_and_list():
    _reset_state()
    create_payload = {
        "title": "Demo",
        "story_text": "Once upon a time",
        "style": "comic",
    }
    create_resp = client.post("/api/projects/create", json=create_payload)
    assert create_resp.status_code == 200
    project_id = create_resp.json()["project_id"]

    list_resp = client.get("/api/projects")
    assert list_resp.status_code == 200
    projects = list_resp.json()["projects"]
    assert len(projects) == 1
    assert projects[0]["id"] == project_id
    assert projects[0]["title"] == "Demo"


def test_task_completion_updates_shot():
    _reset_state()
    create_resp = client.post(
        "/api/projects/create",
        json={"title": "Demo", "story_text": "Story", "style": "comic"},
    )
    project_id = create_resp.json()["project_id"]
    storyboard_resp = client.get(f"/api/projects/{project_id}/storyboard")
    shot_id = storyboard_resp.json()["shots"][0]["id"]

    generate_resp = client.post(f"/api/shots/{shot_id}/generate_image")
    task_id = generate_resp.json()["task_id"]
    assert SHOTS[shot_id]["status"] == "RUNNING"

    result_url = "https://example.com/final.png"
    webhook_resp = client.post(
        "/api/webhook/task_complete", params={"task_id": task_id, "result_url": result_url}
    )
    assert webhook_resp.status_code == 200
    assert webhook_resp.json()["ok"] is True

    updated_storyboard = client.get(f"/api/projects/{project_id}/storyboard").json()
    shot = updated_storyboard["shots"][0]
    assert shot["status"] == "SUCCESS"
    assert shot["image_url"] == result_url
