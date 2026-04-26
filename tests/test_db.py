"""Unit tests for the ChatDB layer. No MCP, no chat logic — DB only."""
import os
import tempfile
import pytest
from src.api.db import ChatDB


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield ChatDB(path)
    os.unlink(path)


class TestMessages:
    def test_insert_and_get_all(self, db):
        db.insert_message("alice", "hello", role="designer")
        db.insert_message("bob",   "world", role="developer")
        msgs = db.get_all_messages()  # defaults to 'general'
        assert len(msgs) == 2
        assert msgs[0]["sender"] == "alice"
        assert msgs[1]["content"] == "world"

    def test_get_latest_empty(self, db):
        assert db.get_latest_message() is None

    def test_get_latest_returns_last(self, db):
        db.insert_message("a", "first")
        db.insert_message("b", "second")
        latest = db.get_latest_message()
        assert latest["content"] == "second"
        assert latest["sender"] == "b"

    def test_get_messages_since(self, db):
        m1 = db.insert_message("a", "one")
        m2 = db.insert_message("b", "two")
        m3 = db.insert_message("c", "three")
        since = db.get_messages_since(m1["id"])
        assert len(since) == 2
        assert since[0]["id"] == m2["id"]
        assert since[1]["id"] == m3["id"]

    def test_messages_are_ordered(self, db):
        for i in range(5):
            db.insert_message("x", str(i))
        msgs = db.get_all_messages()
        ids = [m["id"] for m in msgs]
        assert ids == sorted(ids)

    def test_role_stored_correctly(self, db):
        db.insert_message("agent", "hi", role="qa")
        assert db.get_all_messages()[0]["role"] == "qa"

    def test_null_role_allowed(self, db):
        db.insert_message("user", "hello")
        assert db.get_all_messages()[0]["role"] is None

    def test_channel_isolation(self, db):
        db.insert_message("a", "in general", channel="general")
        db.insert_message("b", "in backend", channel="backend")
        general = db.get_all_messages(channel="general")
        backend = db.get_all_messages(channel="backend")
        assert len(general) == 1
        assert general[0]["content"] == "in general"
        assert len(backend) == 1
        assert backend[0]["content"] == "in backend"

    def test_get_latest_scoped_to_channel(self, db):
        db.insert_message("a", "general msg", channel="general")
        db.insert_message("b", "other msg", channel="design")
        assert db.get_latest_message(channel="general")["content"] == "general msg"
        assert db.get_latest_message(channel="design")["content"] == "other msg"

    def test_get_messages_since_scoped_to_channel(self, db):
        m1 = db.insert_message("a", "general 1", channel="general")
        db.insert_message("b", "other channel", channel="other")
        db.insert_message("c", "general 2", channel="general")
        since = db.get_messages_since(m1["id"], channel="general")
        assert len(since) == 1
        assert since[0]["content"] == "general 2"

    def test_message_includes_channel_field(self, db):
        result = db.insert_message("x", "hello", channel="design")
        assert result["channel"] == "design"

    def test_get_recent_messages(self, db):
        for i in range(15):
            db.insert_message("x", f"msg{i}")
        recent = db.get_recent_messages(n=5)
        assert len(recent) == 5
        # Should be in chronological order (oldest first)
        assert recent[0]["content"] == "msg10"
        assert recent[4]["content"] == "msg14"

    def test_get_recent_messages_channel_scoped(self, db):
        for i in range(5):
            db.insert_message("x", f"g{i}", channel="general")
        for i in range(3):
            db.insert_message("y", f"b{i}", channel="backend")
        recent = db.get_recent_messages(channel="backend", n=10)
        assert all(m["channel"] == "backend" for m in recent)
        assert len(recent) == 3

    def test_get_latest_user_message(self, db):
        db.insert_message("user", "hi from human", role="user")
        db.insert_message("agent", "hi from agent", role="developer")
        db.insert_message("user", "second human msg", role="user")
        db.insert_message("agent", "agent reply", role="developer")
        pinned = db.get_latest_user_message()
        assert pinned["content"] == "second human msg"
        assert pinned["sender"] == "user"

    def test_get_latest_user_message_none(self, db):
        db.insert_message("agent", "only agent")
        assert db.get_latest_user_message() is None


class TestChannels:
    def test_general_channel_seeded_on_init(self, db):
        names = [c["name"] for c in db.get_all_channels()]
        assert "general" in names

    def test_create_channel(self, db):
        ch = db.create_channel("backend")
        assert ch["name"] == "backend"
        assert "id" in ch

    def test_create_duplicate_raises(self, db):
        db.create_channel("alpha")
        with pytest.raises(ValueError):
            db.create_channel("alpha")

    def test_get_channel_by_id(self, db):
        ch = db.create_channel("beta")
        found = db.get_channel_by_id(ch["id"])
        assert found["name"] == "beta"

    def test_get_channel_by_id_missing(self, db):
        assert db.get_channel_by_id(9999) is None

    def test_get_channel_by_name(self, db):
        db.create_channel("gamma")
        found = db.get_channel_by_name("gamma")
        assert found["name"] == "gamma"

    def test_get_channel_by_name_missing(self, db):
        assert db.get_channel_by_name("nonexistent") is None

    def test_get_all_channels_ordered(self, db):
        db.create_channel("z-channel")
        db.create_channel("a-channel")
        channels = db.get_all_channels()
        ids = [c["id"] for c in channels]
        assert ids == sorted(ids)

    def test_rename_channel(self, db):
        ch = db.create_channel("old-name")
        renamed = db.rename_channel(ch["id"], "new-name")
        assert renamed["name"] == "new-name"
        assert db.get_channel_by_id(ch["id"])["name"] == "new-name"

    def test_rename_missing_channel_returns_none(self, db):
        assert db.rename_channel(9999, "whatever") is None

    def test_rename_to_duplicate_raises(self, db):
        ch1 = db.create_channel("alpha")
        db.create_channel("beta")
        with pytest.raises(ValueError):
            db.rename_channel(ch1["id"], "beta")

    def test_delete_channel(self, db):
        ch = db.create_channel("to-delete")
        db.insert_message("x", "msg", channel="to-delete")
        assert db.delete_channel(ch["id"]) is True
        assert db.get_channel_by_id(ch["id"]) is None
        # Messages in that channel should also be gone
        assert db.get_all_messages(channel="to-delete") == []

    def test_delete_missing_channel_returns_false(self, db):
        assert db.delete_channel(9999) is False


class TestAgents:
    def test_register_and_get(self, db):
        db.register_agent("agent_1", "designer")
        agent = db.get_agent("agent_1")
        assert agent["name"] == "agent_1"
        assert agent["role"] == "designer"

    def test_get_unknown_agent(self, db):
        assert db.get_agent("nobody") is None

    def test_register_updates_on_conflict(self, db):
        db.register_agent("agent_1", "designer")
        db.register_agent("agent_1", "developer")
        assert db.get_agent("agent_1")["role"] == "developer"

    def test_update_last_seen(self, db):
        import time
        db.register_agent("agent_1", "qa")
        first = db.get_agent("agent_1")["last_seen"]
        time.sleep(0.05)
        db.update_agent_seen("agent_1")
        second = db.get_agent("agent_1")["last_seen"]
        assert second >= first

    def test_get_all_agents_ordered(self, db):
        db.register_agent("b", "developer")
        db.register_agent("a", "designer")
        names = [a["name"] for a in db.get_all_agents()]
        assert names[0] == "b"

    def test_register_with_new_fields(self, db):
        db.register_agent("bot", "developer", display_name="swift-falcon",
                          color="#79c0ff", agent_type="claude", model="claude-sonnet-4-6", channel="backend")
        a = db.get_agent("bot")
        assert a["display_name"] == "swift-falcon"
        assert a["color"] == "#79c0ff"
        assert a["agent_type"] == "claude"
        assert a["model"] == "claude-sonnet-4-6"
        assert a["channel"] == "backend"

    def test_update_agent_role(self, db):
        db.register_agent("a1", "designer")
        updated = db.update_agent("a1", role="developer")
        assert updated["role"] == "developer"

    def test_update_agent_status_and_pid(self, db):
        db.register_agent("a1", "developer")
        db.update_agent("a1", status="stopped", pid=12345)
        a = db.get_agent("a1")
        assert a["status"] == "stopped"
        assert a["pid"] == 12345

    def test_update_missing_agent_returns_none(self, db):
        assert db.update_agent("nobody", role="designer") is None

    def test_delete_agent(self, db):
        db.register_agent("a1", "developer")
        assert db.delete_agent("a1") is True
        assert db.get_agent("a1") is None

    def test_delete_missing_agent_returns_false(self, db):
        assert db.delete_agent("nobody") is False


class TestRoles:
    def test_create_and_get_role(self, db):
        role = db.create_role("tester", "Finds bugs", ["Write tests", "Report issues"])
        assert role["name"] == "tester"
        assert "Write tests" in role["rules"]

    def test_get_role_by_name(self, db):
        db.create_role("writer", "Writes content", ["Draft text"])
        found = db.get_role_by_name("writer")
        assert found["name"] == "writer"
        assert isinstance(found["rules"], list)

    def test_get_missing_role_returns_none(self, db):
        assert db.get_role_by_name("nonexistent") is None

    def test_create_duplicate_role_raises(self, db):
        db.create_role("r1", "desc", [])
        with pytest.raises(ValueError):
            db.create_role("r1", "desc2", [])

    def test_update_role(self, db):
        db.create_role("r1", "original", ["rule1"])
        updated = db.update_role("r1", description="updated", rules=["rule2"])
        assert updated["description"] == "updated"
        assert updated["rules"] == ["rule2"]

    def test_update_missing_role_returns_none(self, db):
        assert db.update_role("nobody", description="x") is None

    def test_delete_role(self, db):
        db.create_role("temp", "temp", [])
        assert db.delete_role("temp") is True
        assert db.get_role_by_name("temp") is None

    def test_delete_missing_role_returns_false(self, db):
        assert db.delete_role("nobody") is False

    def test_seed_roles_from_list(self, db):
        roles = [
            {"name": "dev", "description": "Develops", "rules": ["code"], "max_active": 2},
            {"name": "qa",  "description": "Tests",    "rules": ["test"],  "max_active": 1},
        ]
        db.seed_roles_from_list(roles)
        all_roles = db.get_all_roles()
        names = [r["name"] for r in all_roles]
        assert "dev" in names
        assert "qa" in names

    def test_seed_skips_existing(self, db):
        db.create_role("dev", "original", [])
        db.seed_roles_from_list([{"name": "dev", "description": "new", "rules": []}])
        # Should still have original description
        assert db.get_role_by_name("dev")["description"] == "original"

    def test_roles_are_seeded_false_on_empty(self, db):
        assert db.roles_are_seeded() is False

    def test_roles_are_seeded_true_after_create(self, db):
        db.create_role("r1", "", [])
        assert db.roles_are_seeded() is True

    def test_get_all_roles_returns_parsed_rules(self, db):
        db.create_role("r1", "", ["do this", "do that"])
        roles = db.get_all_roles()
        r = next(r for r in roles if r["name"] == "r1")
        assert isinstance(r["rules"], list)
        assert r["rules"] == ["do this", "do that"]


class TestTasks:
    def test_create_and_get_task(self, db):
        task = db.create_task("Fix bug", "Some description", channel="general", status="todo")
        assert task["title"] == "Fix bug"
        assert task["status"] == "todo"
        assert task["channel"] == "general"
        got = db.get_task(task["id"])
        assert got["title"] == "Fix bug"

    def test_get_missing_task_returns_none(self, db):
        assert db.get_task(9999) is None

    def test_get_all_tasks(self, db):
        db.create_task("T1")
        db.create_task("T2")
        assert len(db.get_all_tasks()) == 2

    def test_get_tasks_filtered_by_channel(self, db):
        db.create_task("T1", channel="general")
        db.create_task("T2", channel="backend")
        assert len(db.get_all_tasks(channel="general")) == 1
        assert len(db.get_all_tasks(channel="backend")) == 1

    def test_update_task(self, db):
        task = db.create_task("Old title")
        updated = db.update_task(task["id"], title="New title", status="done")
        assert updated["title"] == "New title"
        assert updated["status"] == "done"

    def test_update_missing_task_returns_none(self, db):
        assert db.update_task(9999, title="x") is None

    def test_delete_task(self, db):
        task = db.create_task("To delete")
        assert db.delete_task(task["id"]) is True
        assert db.get_task(task["id"]) is None

    def test_delete_missing_task_returns_false(self, db):
        assert db.delete_task(9999) is False
