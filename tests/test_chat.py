"""Unit tests for ChatRoom business logic."""
import os
import tempfile
import pytest
from src.api.db import ChatDB
from src.api.chat import ChatRoom

ROLES_PATH = "roles.json"


@pytest.fixture
def room():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    db = ChatDB(path)
    r = ChatRoom(db, ROLES_PATH)
    yield r
    os.unlink(path)


class TestJoin:
    def test_join_returns_role_and_header(self, room):
        result = room.join("agent_1")
        assert "role" in result
        assert "system_header" in result
        assert "agent_name" in result
        assert result["agent_name"] == "agent_1"

    def test_join_posts_system_message(self, room):
        room.join("agent_1")
        msgs = room.get_all_messages()
        assert any("agent_1" in m["content"] for m in msgs)

    def test_join_preferred_role(self, room):
        result = room.join("agent_1", preferred_role="designer")
        assert result["role"] == "designer"

    def test_second_agent_gets_different_role(self, room):
        r1 = room.join("agent_1")
        r2 = room.join("agent_2")
        # If they share a role, that role must allow >= 2 agents
        if r1["role"] == r2["role"]:
            from src.api.roles import load_roles
            roles = load_roles(ROLES_PATH)
            role_def = next(r for r in roles if r["name"] == r1["role"])
            assert role_def.get("max_active", 99) >= 2


class TestReadAll:
    def test_read_all_contains_header(self, room):
        room.join("agent_1")
        text = room.read_all("agent_1")
        assert "SYSTEM" in text
        assert "ROLE" in text

    def test_read_all_contains_messages(self, room):
        room.join("agent_1")
        room.send_message("agent_1", "hello from agent")
        text = room.read_all("agent_1")
        assert "hello from agent" in text

    def test_read_all_chat_log_header(self, room):
        room.join("agent_1")
        text = room.read_all("agent_1")
        assert "CHAT LOG" in text

    def test_read_all_channel_in_header(self, room):
        room.join("agent_1")
        text = room.read_all("agent_1", channel="general")
        assert "general" in text

    def test_read_all_channel_isolation(self, room):
        room.join("agent_1")
        room.send_message("agent_1", "in general", channel="general")
        room.send_message("agent_1", "in backend", channel="backend")
        general = room.read_all("agent_1", channel="general")
        backend = room.read_all("agent_1", channel="backend")
        assert "in general" in general
        assert "in backend" not in general
        assert "in backend" in backend
        assert "in general" not in backend


class TestReadLatest:
    def test_read_latest_after_join_has_message(self, room):
        room.join("agent_1")
        result = room.read_latest("agent_1")
        assert "latest_message" in result
        assert result["latest_message"] is not None

    def test_read_latest_returns_last_message(self, room):
        room.join("agent_1")
        room.send_message("agent_1", "first")
        room.send_message("agent_1", "second")
        result = room.read_latest("agent_1")
        assert result["latest_message"]["content"] == "second"

    def test_read_latest_has_system_header(self, room):
        room.join("agent_1")
        result = room.read_latest("agent_1")
        assert "SYSTEM" in result["system_header"]

    def test_read_latest_channel_isolation(self, room):
        room.join("agent_1")
        room.send_message("agent_1", "general last", channel="general")
        room.send_message("agent_1", "design last", channel="design")
        latest_general = room.read_latest("agent_1", channel="general")
        latest_design = room.read_latest("agent_1", channel="design")
        assert latest_general["latest_message"]["content"] == "general last"
        assert latest_design["latest_message"]["content"] == "design last"

    def test_read_latest_empty_channel_returns_none(self, room):
        room.join("agent_1")
        result = room.read_latest("agent_1", channel="empty-channel")
        assert result["latest_message"] is None


class TestSendMessage:
    def test_send_stores_message(self, room):
        room.join("agent_1")
        room.send_message("agent_1", "test content")
        msgs = room.get_all_messages(channel="general")
        contents = [m["content"] for m in msgs]
        assert "test content" in contents

    def test_send_attaches_role(self, room):
        room.join("agent_1", preferred_role="designer")
        room.send_message("agent_1", "hi")
        msgs = room.get_all_messages(channel="general")
        agent_msg = next(m for m in msgs if m["sender"] == "agent_1")
        assert agent_msg["role"] == "designer"

    def test_send_to_specific_channel(self, room):
        room.join("agent_1")
        room.send_message("agent_1", "backend msg", channel="backend")
        msgs = room.get_all_messages(channel="backend")
        contents = [m["content"] for m in msgs]
        assert "backend msg" in contents
        assert "backend msg" not in [m["content"] for m in room.get_all_messages(channel="general")]

    def test_user_message_has_user_role(self, room):
        room.send_user_message("human here")
        msgs = room.get_all_messages(channel="general")
        assert msgs[-1]["sender"] == "user"
        assert msgs[-1]["role"] == "user"


class TestGetChannels:
    def test_get_channels_includes_general(self, room):
        channels = room.get_channels()
        names = [c["name"] for c in channels]
        assert "general" in names
