"""
Integration test: spawn a Claude agent via the API and validate its logs.

This test hits the real /api/agents/spawn endpoint, which launches a real
subprocess. It then reads the log file the server writes and asserts that
the agent started and joined the correct channel.

The test redirects logs to a pytest tmp_path via the AGENTCY_LOGS_DIR env var
so it never touches the production logs/ directory.

Run integration tests:
    pytest -m integration tests/
Skip them:
    pytest -m "not integration" tests/
"""
import os
import signal
import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.server import create_ui_app

ROLES_PATH = "roles.json"


@pytest.fixture
def logs_dir(tmp_path):
    d = tmp_path / "logs"
    d.mkdir()
    return d


@pytest.fixture
def client(logs_dir):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    os.environ["AGENTCY_LOGS_DIR"] = str(logs_dir)
    app = create_ui_app(db_path, ROLES_PATH)
    with TestClient(app) as c:
        yield c

    os.environ.pop("AGENTCY_LOGS_DIR", None)
    os.unlink(db_path)


def _wait_for_log_line(log_path: Path, expected: str, timeout: float = 10.0) -> str:
    """Poll log_path until a line containing `expected` appears or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if log_path.exists():
            content = log_path.read_text(errors="replace")
            if expected in content:
                return content
        time.sleep(0.2)
    content = log_path.read_text(errors="replace") if log_path.exists() else "(log file never created)"
    raise TimeoutError(
        f"Expected {expected!r} not found in log within {timeout}s.\nLog content:\n{content}"
    )


@pytest.mark.integration
class TestAgentSpawn:
    def test_spawn_returns_agent_metadata(self, client, logs_dir):
        resp = client.post("/api/agents/spawn", json={
            "type": "claude",
            "model": "claude-sonnet-4-6",
            "role": "designer",
            "channel": "general",
            "interval": 5,
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert "agent_name" in data
        assert "display_name" in data
        assert "pid" in data
        assert isinstance(data["pid"], int)

        client.delete(f"/api/agents/{data['agent_name']}/kill")
        client.delete(f"/api/agents/{data['agent_name']}")

    def test_agent_log_shows_startup_and_correct_channel(self, client, logs_dir):
        channel = "general"
        resp = client.post("/api/agents/spawn", json={
            "type": "claude",
            "model": "claude-sonnet-4-6",
            "role": "designer",
            "channel": channel,
            "interval": 5,
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        agent_name = data["agent_name"]
        log_path = logs_dir / f"{agent_name}.log"

        try:
            # Agent must log that it is joining with the right channel
            content = _wait_for_log_line(
                log_path,
                f"Joining as '{agent_name}'",
                timeout=10,
            )
            assert f"channel=#{channel}" in content, (
                f"Expected channel=#{channel} in log.\nLog:\n{content}"
            )

            # Agent must log that it joined successfully
            content = _wait_for_log_line(log_path, "Joined as role:", timeout=10)
            assert "Joined as role:" in content

        finally:
            pid = data.get("pid")
            if pid:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            client.delete(f"/api/agents/{agent_name}/kill")
            client.delete(f"/api/agents/{agent_name}")

    def test_agent_registered_in_db_with_correct_channel(self, client, logs_dir):
        channel = "general"
        resp = client.post("/api/agents/spawn", json={
            "type": "claude",
            "model": "claude-sonnet-4-6",
            "role": "designer",
            "channel": channel,
            "interval": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        agent_name = data["agent_name"]

        try:
            agents = client.get("/api/agents").json()
            match = next((a for a in agents if a["name"] == agent_name), None)
            assert match is not None, f"Agent {agent_name!r} not found in /api/agents"
            assert match["channel"] == channel
            assert match["status"] == "active"
            assert match["agent_type"] == "claude"
        finally:
            client.delete(f"/api/agents/{agent_name}/kill")
            client.delete(f"/api/agents/{agent_name}")
