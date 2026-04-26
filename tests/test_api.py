"""
REST API integration tests.

Uses FastAPI's TestClient (in-process, no running server needed).
Tests all public endpoints in server.py.
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

    def test_channel_scoped(self, client):
        client.post("/api/messages", json={"content": "in general", "channel": "general"})
        client.post("/api/channels", json={"name": "backend"})
        client.post("/api/messages", json={"content": "in backend", "channel": "backend"})
        general = client.get("/api/messages?channel=general").json()
        backend = client.get("/api/messages?channel=backend").json()
        assert any(m["content"] == "in general" for m in general)
        assert any(m["content"] == "in backend" for m in backend)
        assert not any(m["content"] == "in backend" for m in general)


# ---------------------------------------------------------------------------
# GET /api/messages/since/{message_id}
# ---------------------------------------------------------------------------

class TestGetMessagesSince:
    def test_returns_messages_after_id(self, client):
        client.post("/api/messages", json={"content": "first"})
        first_id = client.get("/api/messages").json()[0]["id"]
        client.post("/api/messages", json={"content": "second"})
        client.post("/api/messages", json={"content": "third"})
        resp = client.get(f"/api/messages/since/{first_id}")
        assert resp.status_code == 200
        contents = [m["content"] for m in resp.json()]
        assert "second" in contents
        assert "third" in contents
        assert "first" not in contents

    def test_returns_empty_when_no_new(self, client):
        client.post("/api/messages", json={"content": "only"})
        last_id = client.get("/api/messages").json()[-1]["id"]
        assert client.get(f"/api/messages/since/{last_id}").json() == []


# ---------------------------------------------------------------------------
# GET /api/messages/recent
# ---------------------------------------------------------------------------

class TestGetMessagesRecent:
    def test_returns_last_n(self, client):
        for i in range(12):
            client.post("/api/messages", json={"content": f"msg{i}"})
        resp = client.get("/api/messages/recent?n=5")
        assert resp.status_code == 200
        msgs = resp.json()
        assert len(msgs) == 5
        # last message should be msg11
        assert msgs[-1]["content"] == "msg11"


# ---------------------------------------------------------------------------
# GET /api/latest
# ---------------------------------------------------------------------------

class TestGetLatest:
    def test_empty_returns_empty_object(self, client):
        assert client.get("/api/latest").json() == {}

    def test_returns_most_recent(self, client):
        client.post("/api/messages", json={"content": "first"})
        client.post("/api/messages", json={"content": "last"})
        assert client.get("/api/latest").json()["content"] == "last"


# ---------------------------------------------------------------------------
# GET /api/pinned
# ---------------------------------------------------------------------------

class TestGetPinned:
    def test_empty_returns_empty(self, client):
        assert client.get("/api/pinned").json() == {}

    def test_returns_latest_user_message(self, client):
        client.post("/api/messages", json={"content": "human msg 1"})
        # Post an agent message too
        client.post("/api/messages", json={"content": "agent reply", "sender": "bot"})
        client.post("/api/messages", json={"content": "human msg 2"})
        pinned = client.get("/api/pinned").json()
        assert pinned["content"] == "human msg 2"
        assert pinned["sender"] == "user"


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

    def test_post_empty_content_rejected(self, client):
        assert client.post("/api/messages", json={"content": ""}).status_code == 400

    def test_post_missing_content_rejected(self, client):
        assert client.post("/api/messages", json={}).status_code == 400

    def test_post_whitespace_only_rejected(self, client):
        assert client.post("/api/messages", json={"content": "   "}).status_code == 400

    def test_post_with_channel(self, client):
        client.post("/api/channels", json={"name": "design"})
        resp = client.post("/api/messages", json={"content": "design msg", "channel": "design"})
        assert resp.status_code == 200
        assert resp.json()["channel"] == "design"

    def test_post_agent_message(self, client):
        # Register agent first
        client.post("/api/agent/join", json={"agent_name": "bot1"})
        resp = client.post("/api/messages", json={"content": "agent says hi", "sender": "bot1"})
        assert resp.status_code == 200
        assert resp.json()["sender"] == "bot1"


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

class TestChannelsCRUD:
    def test_get_channels_includes_general(self, client):
        channels = client.get("/api/channels").json()
        assert any(c["name"] == "general" for c in channels)

    def test_create_channel(self, client):
        resp = client.post("/api/channels", json={"name": "design"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "design"
        assert "id" in resp.json()

    def test_create_duplicate_channel_409(self, client):
        client.post("/api/channels", json={"name": "alpha"})
        assert client.post("/api/channels", json={"name": "alpha"}).status_code == 409

    def test_create_channel_missing_name_400(self, client):
        assert client.post("/api/channels", json={}).status_code == 400

    def test_rename_channel(self, client):
        ch = client.post("/api/channels", json={"name": "old"}).json()
        renamed = client.patch(f"/api/channels/{ch['id']}", json={"name": "new"}).json()
        assert renamed["name"] == "new"

    def test_rename_missing_channel_404(self, client):
        assert client.patch("/api/channels/9999", json={"name": "x"}).status_code == 404

    def test_delete_channel(self, client):
        ch = client.post("/api/channels", json={"name": "to-delete"}).json()
        resp = client.delete(f"/api/channels/{ch['id']}")
        assert resp.status_code == 200
        assert client.get(f"/api/channels/{ch['id']}").status_code == 404

    def test_delete_general_channel(self, client):
        general = next(c for c in client.get("/api/channels").json() if c["name"] == "general")
        assert client.delete(f"/api/channels/{general['id']}").status_code == 200
        assert client.get(f"/api/channels/{general['id']}").status_code == 404

    def test_delete_missing_channel_404(self, client):
        assert client.delete("/api/channels/9999").status_code == 404

    def test_get_channel_by_id(self, client):
        ch = client.post("/api/channels", json={"name": "mytest"}).json()
        found = client.get(f"/api/channels/{ch['id']}").json()
        assert found["name"] == "mytest"

    def test_get_channel_missing_404(self, client):
        assert client.get("/api/channels/9999").status_code == 404


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class TestExport:
    def test_export_channel_returns_markdown(self, client):
        client.post("/api/messages", json={"content": "hello", "channel": "general"})
        resp = client.get("/api/export?channel=general")
        assert resp.status_code == 200
        assert "general" in resp.text

    def test_export_all_returns_markdown(self, client):
        client.post("/api/messages", json={"content": "msg1"})
        resp = client.get("/api/export/all")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/markdown")


# ---------------------------------------------------------------------------
# Roles CRUD
# ---------------------------------------------------------------------------

class TestRolesCRUD:
    def test_get_roles_seeded_from_json(self, client):
        roles = client.get("/api/roles").json()
        assert isinstance(roles, list)
        assert len(roles) > 0
        names = [r["name"] for r in roles]
        assert "developer" in names

    def test_create_role(self, client):
        resp = client.post("/api/roles", json={
            "name": "tester", "description": "Tests things",
            "rules": ["Find bugs", "Report clearly"], "max_active": 2,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "tester"

    def test_create_role_missing_name_400(self, client):
        assert client.post("/api/roles", json={"description": "x"}).status_code == 400

    def test_create_duplicate_role_409(self, client):
        client.post("/api/roles", json={"name": "r1", "description": ""})
        assert client.post("/api/roles", json={"name": "r1", "description": ""}).status_code == 409

    def test_update_role(self, client):
        client.post("/api/roles", json={"name": "r2", "description": "old"})
        updated = client.put("/api/roles/r2", json={"description": "new"}).json()
        assert updated["description"] == "new"

    def test_update_missing_role_404(self, client):
        assert client.put("/api/roles/nobody", json={"description": "x"}).status_code == 404

    def test_delete_role(self, client):
        client.post("/api/roles", json={"name": "temp_role", "description": ""})
        assert client.delete("/api/roles/temp_role").status_code == 200

    def test_delete_missing_role_404(self, client):
        assert client.delete("/api/roles/nobody").status_code == 404

    def test_export_roles_returns_json(self, client):
        resp = client.get("/api/roles/export")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Agent management
# ---------------------------------------------------------------------------

class TestAgentManagement:
    def test_get_agents_empty(self, client):
        assert isinstance(client.get("/api/agents").json(), list)

    def test_agent_join(self, client):
        resp = client.post("/api/agent/join", json={"agent_name": "bot1"})
        assert resp.status_code == 200
        assert "role" in resp.json()
        assert "system_header" in resp.json()

    def test_update_agent_role(self, client):
        client.post("/api/agent/join", json={"agent_name": "bot2"})
        updated = client.patch("/api/agents/bot2", json={"role": "designer"}).json()
        assert updated["role"] == "designer"

    def test_update_missing_agent_404(self, client):
        assert client.patch("/api/agents/nobody", json={"role": "dev"}).status_code == 404

    def test_delete_agent(self, client):
        client.post("/api/agent/join", json={"agent_name": "bot3"})
        assert client.delete("/api/agents/bot3").status_code == 200
        agents = client.get("/api/agents").json()
        assert not any(a["name"] == "bot3" for a in agents)

    def test_delete_missing_agent_404(self, client):
        assert client.delete("/api/agents/nobody").status_code == 404


# ---------------------------------------------------------------------------
# Agent read endpoints
# ---------------------------------------------------------------------------

class TestAgentReadEndpoints:
    def test_read_all(self, client):
        client.post("/api/agent/join", json={"agent_name": "reader"})
        client.post("/api/messages", json={"content": "test msg"})
        resp = client.get("/api/agent/read_all?agent_name=reader")
        assert resp.status_code == 200
        assert "text" in resp.json()
        assert "test msg" in resp.json()["text"]

    def test_read_latest(self, client):
        client.post("/api/agent/join", json={"agent_name": "reader2"})
        client.post("/api/messages", json={"content": "latest"})
        resp = client.get("/api/agent/read_latest?agent_name=reader2")
        assert resp.status_code == 200
        assert resp.json()["latest_message"]["content"] == "latest"

    def test_read_since(self, client):
        client.post("/api/agent/join", json={"agent_name": "reader3"})
        client.post("/api/messages", json={"content": "msg1"})
        msg1_id = client.get("/api/messages").json()[-1]["id"]
        client.post("/api/messages", json={"content": "msg2"})
        resp = client.get(f"/api/agent/read_since?agent_name=reader3&last_id={msg1_id}")
        assert resp.status_code == 200
        msgs = resp.json()["messages"]
        assert any(m["content"] == "msg2" for m in msgs)

    def test_read_recent(self, client):
        client.post("/api/agent/join", json={"agent_name": "reader4"})
        for i in range(5):
            client.post("/api/messages", json={"content": f"m{i}"})
        resp = client.get("/api/agent/read_recent?agent_name=reader4&n=3")
        assert resp.status_code == 200
        msgs = resp.json()["messages"]
        assert len(msgs) == 3


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class TestTasks:
    def test_get_tasks_empty(self, client):
        assert client.get("/api/tasks").json() == []

    def test_create_task(self, client):
        resp = client.post("/api/tasks", json={"title": "My task", "channel": "general"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "My task"

    def test_create_task_missing_title_400(self, client):
        assert client.post("/api/tasks", json={"channel": "general"}).status_code == 400

    def test_get_task_by_id(self, client):
        task = client.post("/api/tasks", json={"title": "T1"}).json()
        found = client.get(f"/api/tasks/{task['id']}").json()
        assert found["title"] == "T1"

    def test_get_missing_task_404(self, client):
        assert client.get("/api/tasks/9999").status_code == 404

    def test_update_task(self, client):
        task = client.post("/api/tasks", json={"title": "Old"}).json()
        updated = client.patch(f"/api/tasks/{task['id']}", json={"status": "done"}).json()
        assert updated["status"] == "done"

    def test_delete_task(self, client):
        task = client.post("/api/tasks", json={"title": "Temp"}).json()
        assert client.delete(f"/api/tasks/{task['id']}").status_code == 200
        assert client.get(f"/api/tasks/{task['id']}").status_code == 404

    def test_filter_tasks_by_channel(self, client):
        client.post("/api/channels", json={"name": "backend"})
        client.post("/api/tasks", json={"title": "T1", "channel": "general"})
        client.post("/api/tasks", json={"title": "T2", "channel": "backend"})
        general_tasks = client.get("/api/tasks?channel=general").json()
        backend_tasks = client.get("/api/tasks?channel=backend").json()
        assert len(general_tasks) == 1
        assert len(backend_tasks) == 1


# ---------------------------------------------------------------------------
# GET /api/agents
# ---------------------------------------------------------------------------

class TestGetAgents:
    def test_empty_returns_list(self, client):
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# GET / (browser UI) + SPA routes
# ---------------------------------------------------------------------------

class TestServeUI:
    def test_root_returns_html(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_channel_route_returns_html(self, client):
        resp = client.get("/channel/general")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_settings_route_returns_html(self, client):
        resp = client.get("/settings")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_settings_subpage_returns_html(self, client):
        resp = client.get("/settings/agents")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_tasks_route_returns_html(self, client):
        resp = client.get("/tasks")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
