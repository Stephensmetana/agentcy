"""
local_llm_client.py — Local LLM (Ollama) agent loop for Agentcy.

Spawns a persistent local LLM agent that:
1. Joins the chatroom via the REST API
2. Polls for new messages using read_latest
3. If the last message is NOT from itself, reads recent context
4. Calls the Ollama OpenAI-compatible API to generate a response
5. Posts the response back to the channel
6. Sleeps and repeats

Requirements:
    pip install openai httpx
    ollama serve  (must be running)
    ollama pull qwen3:14b  (or whichever model you want)

Usage (standalone):
    python local_llm_client.py \\
        --name amber-tide \\
        --model qwen3:14b \\
        --ollama-url http://localhost:11434 \\
        --role designer \\
        --channel general \\
        --interval 5 \\
        --base-url http://localhost:9001

The server can also spawn this script via POST /api/agents/spawn (type=ollama).
"""

import argparse
import sys
import time

import httpx

try:
    from openai import OpenAI
except ImportError:
    print("[llm-agent] 'openai' package not installed. Run: pip install openai", flush=True)
    sys.exit(1)


def _get(base_url, path, params=None):
    r = httpx.get(f"{base_url}{path}", params=params or {}, timeout=15)
    r.raise_for_status()
    return r.json()


def _post(base_url, path, body):
    r = httpx.post(f"{base_url}{path}", json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser(description="Local LLM (Ollama) agent loop for Agentcy")
    parser.add_argument("--name", required=True, help="Agent internal name (unique key)")
    parser.add_argument("--display-name", help="Agent display name (defaults to --name)")
    parser.add_argument("--color", default="#ffa657", help="Avatar color hex")
    parser.add_argument("--model", default="qwen3:14b", help="Ollama model name")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--role", default="developer", help="Preferred role")
    parser.add_argument("--channel", default="general", help="Channel to join")
    parser.add_argument("--interval", type=int, default=5, help="Poll interval in seconds")
    parser.add_argument("--base-url", default="http://localhost:9001", help="Agentcy server base URL")
    parser.add_argument("--context-n", type=int, default=10, help="Number of recent messages to include")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    ollama_url = args.ollama_url.rstrip("/")
    agent_name = args.name
    display_name = args.display_name or args.name

    # Ollama uses the OpenAI-compatible API
    llm = OpenAI(base_url=f"{ollama_url}/v1", api_key="ollama")

    print(f"[llm-agent] Joining as '{display_name}' (model={args.model}, role={args.role}, channel=#{args.channel})", flush=True)

    # Join the chatroom
    join_result = _post(base_url, "/api/agent/join", {
        "agent_name": agent_name,
        "preferred_role": args.role,
        "display_name": display_name,
        "color": args.color,
        "agent_type": "ollama",
        "model": args.model,
        "channel": args.channel,
    })
    system_header = join_result.get("system_header", "")
    role = join_result.get("role", args.role)
    print(f"[llm-agent] Joined as role: {role}", flush=True)

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
                time.sleep(args.interval)
                continue

            if latest["id"] <= last_id:
                time.sleep(args.interval)
                continue

            last_id = latest["id"]

            # Get recent context
            recent_data = _get(base_url, "/api/agent/read_recent", {
                "agent_name": agent_name,
                "channel": args.channel,
                "n": args.context_n,
            })
            messages = recent_data.get("messages", [])

            history_lines = []
            for m in messages:
                role_tag = f"[{m['role']}]" if m.get("role") else ""
                history_lines.append(f"{m['timestamp']}  {role_tag} {m['sender']}: {m['content']}")
            history = "\n".join(history_lines)

            system_prompt = f"""{system_header}

[RECENT CHAT — #{args.channel} — last {len(messages)} messages]

{history}"""

            user_prompt = "Compose your response now. Be concise and on-role. Reply with only the message text, no name/role prefix."

            print(f"[llm-agent] Responding to message id={latest['id']} from {latest['sender']}", flush=True)

            completion = llm.chat.completions.create(
                model=args.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1024,
                temperature=0.7,
            )
            response = completion.choices[0].message.content.strip()

            if response:
                _post(base_url, "/api/messages", {
                    "sender": agent_name,
                    "content": response,
                    "channel": args.channel,
                })
                print(f"[llm-agent] Posted response ({len(response)} chars)", flush=True)

        except httpx.ConnectError as e:
            if "11434" in str(e) or ollama_url in str(e):
                print(f"[llm-agent] Cannot connect to Ollama at {ollama_url} — retrying in {args.interval}s", flush=True)
            else:
                print(f"[llm-agent] Cannot connect to {base_url} — retrying in {args.interval}s", flush=True)
        except Exception as e:
            print(f"[llm-agent] Error: {e}", flush=True)

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
