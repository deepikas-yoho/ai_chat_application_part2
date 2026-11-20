import os
import pytest
from fastapi.testclient import TestClient

os.environ["APP_API_KEY"] = "test-key"
from app.main import app, sessions, requests_by_token

client = TestClient(app)
HEADERS = {"X-API-Key": "test-key"}


@pytest.fixture(autouse=True)
def reset_state():
    sessions.clear()
    requests_by_token.clear()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_auth_required():
    assert client.get("/api/sessions").status_code == 401


def test_create_and_list_session():
    created = client.post("/api/sessions", headers=HEADERS, json={"title": "Test"}).json()
    listed = client.get("/api/sessions", headers=HEADERS).json()
    assert listed == [{"id": created["id"], "title": "Test"}]


def test_session_isolation_and_history():
    a = client.post("/api/sessions", headers=HEADERS, json={}).json()["id"]
    b = client.post("/api/sessions", headers=HEADERS, json={}).json()["id"]
    assert client.get(f"/api/sessions/{a}/messages", headers=HEADERS).json() == []
    assert client.get(f"/api/sessions/{b}/messages", headers=HEADERS).json() == []
    assert client.get("/api/sessions/not-real/messages", headers=HEADERS).status_code == 404


def test_streaming_reply_and_history():
    sid = client.post("/api/sessions", headers=HEADERS, json={}).json()["id"]
    with client.stream("POST", f"/api/sessions/{sid}/stream", headers=HEADERS,
                       json={"message": "hello"}) as response:
        body = "".join(response.iter_text())
    assert response.status_code == 200
    assert "Demo response" in body
    history = client.get(f"/api/sessions/{sid}/messages", headers=HEADERS).json()
    assert [m["role"] for m in history] == ["user", "assistant"]


def test_empty_message_rejected():
    sid = client.post("/api/sessions", headers=HEADERS, json={}).json()["id"]
    assert client.post(f"/api/sessions/{sid}/stream", headers=HEADERS,
                       json={"message": " "}).status_code == 400


def test_rate_limit(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "RATE_LIMIT", 1)
    sid = client.post("/api/sessions", headers=HEADERS, json={}).json()["id"]
    # First request consumes the single allowed slot.
    with client.stream("POST", f"/api/sessions/{sid}/stream", headers=HEADERS,
                       json={"message": "one"}) as r:
        list(r.iter_text())
    assert client.post(f"/api/sessions/{sid}/stream", headers=HEADERS,
                       json={"message": "two"}).status_code == 429


def test_usage():
    client.post("/api/sessions", headers=HEADERS, json={})
    data = client.get("/api/usage", headers=HEADERS).json()
    assert data["sessions"] == 1
    assert data["rate_limit"] > 0
