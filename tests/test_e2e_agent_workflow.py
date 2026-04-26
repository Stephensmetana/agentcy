"""
End-to-end integration test: full agent workflow against a live server.

Requires the Agentcy server to be running at http://localhost:9001.
Skip with:  pytest -m "not e2e" tests/

Test sequence
─────────────
1. Create an "integration-test" channel
2. Spawn a Claude agent assigned to that channel
3. Wait for the agent to join (log confirms it)
4. Post a message as the user with a task the agent can fulfil and we can verify:
   the agent is asked to reply with a specific token so we can detect its response
5. Poll /api/messages until the agent's reply appears (up to 90 s)
6. Assert the agent replied in the right channel, after the user message
7. Tear down: kill agent, delete agent record, delete channel
"""
import os
import signal
import time
from pathlib import Path

import httpx
import pytest

BASE_URL = "http://localhost:9001"
LOGS_DIR = Path(__file__).parent.parent / "logs"

# Message we send and the token we expect back — simple enough that any
# instruction-following LLM will include it verbatim in its response.
USER_PROMPT = (
    "INTEGRATION TEST — reply with the exact token INT_TEST_OK somewhere in your response "
    "to confirm you received this message and are active in this channel."
)
EXPECTED_TOKEN = "INT_TEST_OK"


# ── helpers ────────────────────────────────────────────────────────────────────

def api(method: str, path: str, **kwargs):
    resp = httpx.request(method, f"{BASE_URL}{path}", timeout=15, **kwargs)
    resp.raise_for_status()
    return resp.json()


def wait_for(condition, timeout: float, interval: float = 0.5, description: str = "condition"):
    """Poll `condition()` every `interval` seconds until it returns truthy or timeout."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = condition()
        if last:
            return last
        time.sleep(interval)
    raise TimeoutError(f"Timed out waiting for {description} after {timeout}s")


def wait_for_log(log_path: Path, text: str, timeout: float = 15.0):
    def check():
        if log_path.exists():
            content = log_path.read_text(errors="replace")
            if text in content:
                return content
        return None
    return wait_for(check, timeout, description=f"{text!r} in {log_path.name}")


# ── server availability check ───────────────────────────────────────────────

def server_is_up() -> bool:
    try:
        httpx.get(f"{BASE_URL}/api/channels", timeout=3)
        return True
    except Exception:
        return False


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def live_server():
    if not server_is_up():
        pytest.skip("Agentcy server not running at http://localhost:9001")


@pytest.fixture
def integration_channel(live_server):
    """Create a fresh channel for the test, delete it afterwards."""
    ch = api("POST", "/api/channels", json={"name": "integration-test"})
    yield ch
    # Delete all messages are tied to the channel record; deleting the channel cleans up
    try:
        api("DELETE", f"/api/channels/{ch['id']}")
    except Exception:
        pass


@pytest.fixture
def integration_agent(integration_channel):
    """Spawn an agent into the integration-test channel, kill+delete it afterwards."""
    channel_name = integration_channel["name"]
    data = api("POST", "/api/agents/spawn", json={
        "type": "claude",
        "model": "claude-sonnet-4-6",
        "role": "developer",
        "channel": channel_name,
        "interval": 5,
    })
    yield data, integration_channel

    agent_name = data["agent_name"]
    pid = data.get("pid")

    # Kill process
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        api("DELETE", f"/api/agents/{agent_name}/kill")
    except Exception:
        pass

    # Delete record
    try:
        api("DELETE", f"/api/agents/{agent_name}")
    except Exception:
        pass


# ── tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestFullAgentWorkflow:

    def test_channel_created(self, integration_channel):
        """Channel exists and is reachable via the API."""
        ch = integration_channel
        assert ch["name"] == "integration-test"
        assert "id" in ch

        channels = api("GET", "/api/channels")
        assert any(c["id"] == ch["id"] for c in channels), (
            "integration-test channel not found in /api/channels"
        )

    def test_agent_spawned_and_joined_channel(self, integration_agent):
        """Agent process starts, joins the correct channel, and appears in /api/agents."""
        data, channel = integration_agent
        agent_name = data["agent_name"]
        channel_name = channel["name"]

        # PID was returned immediately
        assert isinstance(data["pid"], int), "spawn did not return a PID"

        # Log confirms the agent joined the right channel
        log_path = LOGS_DIR / f"{agent_name}.log"
        log = wait_for_log(log_path, f"Joining as '{agent_name}'", timeout=15)
        assert f"channel=#{channel_name}" in log, (
            f"Expected channel=#{channel_name} in log.\n{log}"
        )
        wait_for_log(log_path, "Joined as role:", timeout=15)

        # Agent record appears in the DB
        agents = api("GET", "/api/agents")
        record = next((a for a in agents if a["name"] == agent_name), None)
        assert record is not None, f"Agent {agent_name!r} not found in /api/agents"
        assert record["channel"] == channel_name
        assert record["status"] == "active"

    def test_agent_responds_to_user_message(self, integration_agent):
        """
        Post a message to the channel and wait for the agent to reply.

        The user message asks the agent to include the token INT_TEST_OK in its
        response so we can identify it without needing to parse natural language.
        """
        data, channel = integration_agent
        agent_name = data["agent_name"]
        channel_name = channel["name"]
        log_path = LOGS_DIR / f"{agent_name}.log"

        # Wait for agent to finish joining before we post
        wait_for_log(log_path, "Joined as role:", timeout=15)

        # Post user message
        user_msg = api("POST", "/api/messages", json={
            "sender": "user",
            "content": USER_PROMPT,
            "channel": channel_name,
        })
        user_msg_id = user_msg["id"]

        # Wait for the agent to respond (up to 90 s — claude -p can be slow)
        def agent_replied():
            messages = api("GET", f"/api/messages?channel={channel_name}")
            return next(
                (m for m in messages
                 if m["sender"] == agent_name and m["id"] > user_msg_id),
                None,
            )

        reply = wait_for(agent_replied, timeout=90, interval=3,
                         description=f"reply from {agent_name}")

        assert reply is not None, "Agent never replied"
        assert reply["channel"] == channel_name, (
            f"Reply landed in wrong channel: {reply['channel']!r}"
        )
        assert EXPECTED_TOKEN in reply["content"], (
            f"Expected {EXPECTED_TOKEN!r} in agent reply.\nGot: {reply['content']}"
        )

    def test_cleanup_removes_agent_and_channel(self, integration_agent):
        """
        Verify that the teardown (handled by fixtures) actually removes the
        agent record and channel from the API.

        This test runs after the fixtures have done their cleanup because pytest
        executes fixture teardown after the last test that uses them.  We
        therefore call the cleanup manually here and assert on the result.
        """
        data, channel = integration_agent
        agent_name = data["agent_name"]
        channel_id = channel["id"]
        pid = data.get("pid")

        # Kill + delete agent
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            api("DELETE", f"/api/agents/{agent_name}/kill")
        except Exception:
            pass
        api("DELETE", f"/api/agents/{agent_name}")

        # Delete channel
        api("DELETE", f"/api/channels/{channel_id}")

        # Assert agent is gone
        agents = api("GET", "/api/agents")
        assert not any(a["name"] == agent_name for a in agents), (
            f"Agent {agent_name!r} still present after deletion"
        )

        # Assert channel is gone
        channels = api("GET", "/api/channels")
        assert not any(c["id"] == channel_id for c in channels), (
            f"Channel {channel_id} still present after deletion"
        )
