"""End-to-end API tests (echo provider, no external API needed)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["agents"] >= 5


def test_list_agents():
    r = client.get("/api/v1/agents")
    assert r.status_code == 200
    ids = {a["id"] for a in r.json()}
    assert "researcher" in ids


def test_simple_chat():
    r = client.post("/api/v1/chat", json={"message": "What is the sky blue?"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("complete", "approval_required")
    assert body["trace_id"].startswith("tr-")
    assert len(body["plan"]) >= 1


def test_multi_step_chat_builds_graph():
    r = client.post("/api/v1/chat", json={
        "message": "Research the market and draft a plan"
    })
    assert r.status_code == 200
    body = r.json()
    # multi-step planner -> researcher, strategist, validator
    assert len(body["plan"]) == 3
    agents = {t["agent_id"] for t in body["plan"]}
    assert {"researcher", "strategist", "validator"} == agents


def test_get_task_graph():
    r = client.post("/api/v1/chat", json={"message": "research and plan"})
    graph_id = r.json()["graph_id"]
    r2 = client.get(f"/api/v1/tasks/{graph_id}")
    assert r2.status_code == 200
    assert len(r2.json()) == 3
