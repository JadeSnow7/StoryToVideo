from fastapi.testclient import TestClient

from model import main


client = TestClient(main.app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("status") == "ok"
    assert "ts" in payload


def test_storyboard_endpoint():
    payload = {"story": "夕阳下的海边散步", "style": "pixar"}
    resp = client.post("/llm/storyboard", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "shots" in data and isinstance(data["shots"], list)
    assert data["shots"], "should return at least one shot"
    first_shot = data["shots"][0]
    assert first_shot["title"]
    assert payload["story"] in first_shot["narration"]


def test_sd_generate_endpoint():
    payload = {
        "prompt": "sunset beach cinematic",
        "style": "anime",
        "width": 1024,
        "height": 576,
    }
    resp = client.post("/sd_generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"].startswith("http")
    assert "1024x576" in data["note"]


def test_img2vid_endpoint():
    payload = {
        "image_url": "https://example.com/keyframe.png",
        "duration_seconds": 3.0,
        "transition": "dissolve",
    }
    resp = client.post("/img2vid", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"].endswith(".mp4")
    assert "duration=3.0" in data["note"]


def test_tts_endpoint():
    payload = {"text": "欢迎使用 StoryToVideo", "voice": "female"}
    resp = client.post("/tts", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"].endswith(".wav")
    assert "voice=female" in data["note"]
