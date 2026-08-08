"""Senses (voice/vision) endpoint tests."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_senses_status_initial():
    r = client.get("/api/v1/senses/status")
    assert r.status_code == 200
    body = r.json()
    assert "hearing_enabled" in body
    assert "vision_enabled" in body


def test_ingest_audio():
    r = client.post("/api/v1/senses/audio", json={
        "level": 0.6, "transcript": "hello jarvis", "duration_ms": 1200,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["speech"] is True
    assert body["trace_id"].startswith("tr-")


def test_ingest_audio_silence():
    r = client.post("/api/v1/senses/audio", json={"level": 0.01})
    assert r.status_code == 200
    assert r.json()["speech"] is False


def test_ingest_vision():
    r = client.post("/api/v1/senses/vision", json={
        "mime": "image/jpeg",
        "data_b64": "iVBORw0KGgoAAAANSUhEUg==",  # tiny placeholder
        "width": 640, "height": 480,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["trace_id"].startswith("tr-")


def test_ingest_vision_empty_rejected():
    r = client.post("/api/v1/senses/vision", json={"data_b64": ""})
    assert r.status_code == 200
    assert r.json()["ok"] is False


def test_status_reflects_activity():
    client.post("/api/v1/senses/audio", json={"level": 0.5,
                                              "transcript": "testing"})
    r = client.get("/api/v1/senses/status")
    room = r.json()["room"]
    assert room["speech_heard"] is True
    assert room["activity"] in ("quiet", "active", "loud", "silence")
