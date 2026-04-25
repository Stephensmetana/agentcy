"""
REST API integration tests.

Uses FastAPI's TestClient (in-process, no running server needed).
Tests all public endpoints in ui_server.py.
"""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from src.api.server import create_ui_app

ROLES_PATH = "roles.json"


@pytest.fixture
def client():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    app = create_ui_app(db_path, ROLES_PATH)
    with TestClient(app) as c:
        yield c
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# GET /api/messages
# ---------------------------------------------------------------------------

class TestGetMessages:
    def test_empty_returns_list(self, client):
        resp = client.get("/api/messages")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_posted_messages(self, client):
        client.post("/api/messages", json={"content": "hello"})
        resp = client.get("/api/messages")
        assert resp.status_code == 200
        messages = resp.json()
        assert len(messages) == 1
        assert messages[0]["content"] == "hello"
        assert messages[0]["sender"] == "user"


# ---------------------------------------------------------------------------
# GET /api/messages/since/{message_id}
# ---------------------------------------------------------------------------

class TestGetMessagesSince:
    def test_returns_messages_after_id(self, client):
        client.post("/api/messages", json={"content": "first"})
        resp1 = client.get("/api/messages")
        first_id = resp1.json()[0]["id"]

        client.post("/api/messages", json={"content": "second"})
        client.post("/api/messages", json={"content": "third"})

        resp = client.get(f"/api/messages/since/{first_id}")
        assert resp.status_code == 200
        contents = [m["content"] for m in resp.json()]
        assert "second" in contents
        assert "third" in contents
        assert "first" not in contents

    def test_returns_empty_when_no_new_messages(self, client):
        client.post("/api/messages", json={"content": "only"})
        resp = client.get("/api/messages")
        last_id = resp.json()[-1]["id"]

        since_resp = client.get(f"/api/messages/since/{last_id}")
        assert since_resp.status_code == 200
        assert since_resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/latest
# ---------------------------------------------------------------------------

class TestGetLatest:
    def test_empty_returns_empty_object(self, client):
        resp = client.get("/api/latest")
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_returns_most_recent_message(self, client):
        client.post("/api/messages", json={"content": "first"})
        client.post("/api/messages", json={"content": "last"})
        resp = client.get("/api/latest")
        assert resp.status_code == 200
        assert resp.json()["content"] == "last"


# ---------------------------------------------------------------------------
# POST /api/messages
# ---------------------------------------------------------------------------

class TestPostMessage:
    def test_post_valid_message(self, client):
        resp = client.post("/api/messages", json={"content": "hello world"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["content"] == "hello world"
        assert body["sender"] == "user"
        assert "id" in body

    def test_post_empty_content_is_rejected(self, client):
        resp = client.post("/api/messages", json={"content": ""})
        assert resp.status_code == 400

    def test_post_missing_content_is_rejected(self, client):
        resp = client.post("/api/messages", json={})
        assert resp.status_code == 400

    def test_post_whitespace_only_is_rejected(self, client):
        resp = client.post("/api/messages", json={"content": "   "})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/agents
# ---------------------------------------------------------------------------

class TestGetAgents:
    def test_empty_returns_list(self, client):
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# GET / (browser UI)
# ---------------------------------------------------------------------------

class TestServeUI:
    def test_root_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
