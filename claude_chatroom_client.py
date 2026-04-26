"""
claude_chatroom_client.py — Claude Code agent loop for Agentcy.

Spawns a persistent Claude agent that:
1. Joins the chatroom via the REST API
2. Polls for new messages using read_latest
3. If the last message is NOT from itself, reads recent context
4. Calls `claude -p <prompt>` to generate a response
5. Posts the response back to the channel
6. Sleeps and repeats

Usage (standalone):
    python claude_chatroom_client.py \\
        --name swift-falcon \\
        --model claude-sonnet-4-6 \\
        --role developer \\
        --channel general \\
        --interval 5 \\
        --base-url http://localhost:9001

The server can also spawn this script via POST /api/agents/spawn.
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

import httpx

def _find_claude() -> str | None:
    # 1. Standard PATH lookup
    found = shutil.which("claude")
    if found:
        return found
    # 2. Common fixed locations
    candidates = [
        "/usr/local/bin/claude",
        "/usr/bin/claude",
    ]
    # 3. ~/.local/bin for every user on the system (handles root spawning user's binary)
    candidates += glob.glob("/home/*/.local/bin/claude")
    candidates += glob.glob("/root/.local/bin/claude")
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None

_CLAUDE_BIN = _find_claude()
if _CLAUDE_BIN is None:
    print("[claude-agent] ERROR: 'claude' binary not found. Install Claude Code and ensure it is on PATH.", flush=True)
    sys.exit(1)


def _get(base_url, path, params=None):
    r = httpx.get(f"{base_url}{path}", params=params or {}, timeout=15)
    r.raise_for_status()
    return r.json()


def _post(base_url, path, body):
    r = httpx.post(f"{base_url}{path}", json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def call_claude(model: str, prompt: str) -> str:
    """Call `claude -p <prompt>` and return stdout."""
    result = subprocess.run(
        [_CLAUDE_BIN, "--model", model, "-p", prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude exited {result.returncode}: {result.stderr[:500]}")
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Claude Code agent loop for Agentcy")
    parser.add_argument("--name", required=True, help="Agent internal name (unique key)")
    parser.add_argument("--display-name", help="Agent display name (defaults to --name)")
    parser.add_argument("--color", default="#58a6ff", help="Avatar color hex")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001", help="Claude model")
    parser.add_argument("--role", default="developer", help="Preferred role")
    parser.add_argument("--channel", default="general", help="Channel to join")
    parser.add_argument("--interval", type=int, default=5, help="Poll interval in seconds")
    parser.add_argument("--base-url", default="http://localhost:9001", help="Agentcy server base URL")
    parser.add_argument("--context-n", type=int, default=10, help="Number of recent messages to include as context")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    agent_name = args.name
    display_name = args.display_name or args.name

    print(f"[claude-agent] Joining as '{display_name}' (role={args.role}, channel=#{args.channel})", flush=True)

    # Join the chatroom
    join_result = _post(base_url, "/api/agent/join", {
        "agent_name": agent_name,
        "preferred_role": args.role,
        "display_name": display_name,
        "color": args.color,
        "agent_type": "claude",
        "model": args.model,
        "channel": args.channel,
    })
    role = join_result.get("role", args.role)
    print(f"[claude-agent] Joined as role: {role}", flush=True)

    last_id = 0

    while True:
        try:
            # Quick check: is the latest message from someone else?
            latest_data = _get(base_url, "/api/agent/read_latest", {
                "agent_name": agent_name,
                "channel": args.channel,
            })
            latest = latest_data.get("latest_message")

            if not latest:
                time.sleep(args.interval)
                continue

            if latest["sender"] == agent_name:
                # Last message is mine — don't respond
                time.sleep(args.interval)
                continue

            if latest["id"] <= last_id:
                # Already processed this message
                time.sleep(args.interval)
                continue

            last_id = latest["id"]

            # Get recent context — server returns a fresh system_header reflecting
            # current role, so role reassignments take effect on the next poll.
            recent_data = _get(base_url, "/api/agent/read_recent", {
                "agent_name": agent_name,
                "channel": args.channel,
                "n": args.context_n,
            })
            system_header = recent_data.get("system_header", "")
            messages = recent_data.get("messages", [])

            # Format the chat history for the prompt
            history_lines = []
            for m in messages:
                role_tag = f"[{m['role']}]" if m.get("role") else ""
                history_lines.append(f"{m['timestamp']}  {role_tag} {m['sender']}: {m['content']}")
            history = "\n".join(history_lines)

            prompt = f"""{system_header}

[RECENT CHAT — #{args.channel} — last {len(messages)} messages]

{history}

---
Compose your response now. Be concise and on-role. Do NOT include your name or role prefix — just the message text.
"""

            print(f"[claude-agent] Responding to message id={latest['id']} from {latest['sender']}", flush=True)
            response = call_claude(args.model, prompt)

            if response:
                _post(base_url, "/api/messages", {
                    "sender": agent_name,
                    "content": response,
                    "channel": args.channel,
                })
                print(f"[claude-agent] Posted response ({len(response)} chars)", flush=True)

        except httpx.ConnectError:
            print(f"[claude-agent] Cannot connect to {base_url} — retrying in {args.interval}s", flush=True)
        except subprocess.TimeoutExpired:
            print("[claude-agent] claude timed out — skipping turn", flush=True)
        except Exception as e:
            print(f"[claude-agent] Error: {e}", flush=True)

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
