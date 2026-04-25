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
        """Messages in one channel are not visible in another."""
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
        latest_general = db.get_latest_message(channel="general")
        assert latest_general["content"] == "general msg"
        latest_design = db.get_latest_message(channel="design")
        assert latest_design["content"] == "other msg"

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


class TestChannels:
    def test_general_channel_seeded_on_init(self, db):
        channels = db.get_all_channels()
        names = [c["name"] for c in channels]
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
        agent = db.get_agent("agent_1")
        assert agent["role"] == "developer"

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
        # ordered by joined_at, so b comes first
        assert names[0] == "b"
