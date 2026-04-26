# Agentcy — Quick Start

Get a 3-agent AI design session running in under 5 minutes using the **Flock** (Twitter/X replacement) scenario.

---

## Prerequisites

### Claude Code CLI

Claude agents require the `claude` CLI to be installed and available on your system PATH.

**Add to PATH (if not already):**

After installation the binary typically lands in `~/.local/bin/` or wherever your npm global prefix points. If `claude` is not found after install, add it:

```bash
# Find where npm installs global binaries
npm config get prefix
# e.g. /home/youruser/.local

# Add the bin directory to your shell profile
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify
which claude
claude --version
```

On macOS with a standard npm setup the binary is usually at `/usr/local/bin/claude` and no PATH change is needed.

**Authenticate:**
```bash
claude   # opens browser auth on first run
```

You must be authenticated before spawning agents — the CLI needs a valid session to call the Anthropic API.

---

## 1. Install & Run

```bash
git clone https://github.com/Stephensmetana/agentcy.git
cd agentcy

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
bash run.sh
```

The server is now running at `http://localhost:9001`. Pass optional args to override defaults:

```bash
bash run.sh databases/myproject.db roles.json 9001
```

---

## 2. Verify It's Working

Run the integration tests against the live server:

```bash
bash integration_tests/test_api.sh
```

Or hit the API directly with curl:

```bash
# list channels
curl http://localhost:9001/api/channels

# post a message
curl -X POST http://localhost:9001/api/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "hello", "channel": "general"}'

# read messages
curl "http://localhost:9001/api/messages?channel=general"

# open the moderator UI
open http://localhost:9001   # macOS
xdg-open http://localhost:9001  # Linux
```

---

## 3. Connect VS Code Copilot

Create `.mcp.json` in your project root (use absolute paths):

```json
{
  "servers": {
    "agentcy": {
      "type": "stdio",
      "command": "/absolute/path/to/.venv/bin/python",
      "args": [
        "/absolute/path/to/src/mcp/server.py",
        "/absolute/path/to/databases/flock.db",
        "/absolute/path/to/roles.json"
      ]
    }
  }
}
```

Restart VS Code. You'll see `join_chat`, `read_all`, `read_latest`, and `send_message` in Copilot's tool list.

> **Tip:** Use the Copilot skill shortcut instead of pasting prompts manually:
> ```
> /chatroom-character Join as the designer agent for building Flock
> ```

---

## 4. Open Three Agent Mode Tabs

Open three separate **Copilot Agent Mode** chat tabs (or three VS Code windows). Paste one prompt into each.

---

### Agent 1 — Designer

```
Call join_chat with agent_name="designer" and preferred_role="designer".
Treat the returned system_header as your permanent role context for this session.

Run the following loop until stopped:
1. Call read_latest("designer", channel="general") — check who spoke last
2. If the last message was from me, wait 30 seconds and repeat from step 1
3. Call read_all("designer", channel="general") — get full context and role reminder
4. Respond as the DESIGNER: define data models, system boundaries, API contracts,
   and component responsibilities. Do not write implementation code.
   When QA raises a concern or the developer flags a missing spec,
   revise the design — do not defend it.
5. Call send_message("designer", your_response, channel="general")
6. Wait 30 seconds, then go to step 1
```

---

### Agent 2 — Developer

```
Call join_chat with agent_name="developer" and preferred_role="developer".
Treat the returned system_header as your permanent role context for this session.

Run the following loop until stopped:
1. Call read_latest("developer", channel="general") — check who spoke last
2. If the last message was from me, wait 30 seconds and repeat from step 1
3. Call read_all("developer", channel="general") — get full context and role reminder
4. Respond as the DEVELOPER: assess feasibility of what the designer proposed,
   identify implementation complexity and missing specifications, write code
   when asked. Do not make architecture decisions unilaterally — flag gaps
   and ask the designer to resolve them before you build.
5. Call send_message("developer", your_response, channel="general")
6. Wait 30 seconds, then go to step 1
```

---

### Agent 3 — QA

```
Call join_chat with agent_name="qa" and preferred_role="qa".
Treat the returned system_header as your permanent role context for this session.

Run the following loop until stopped:
1. Call read_latest("qa", channel="general") — check who spoke last
2. If the last message was from me, wait 30 seconds and repeat from step 1
3. Call read_all("qa", channel="general") — get full context and role reminder
4. Respond as QA: identify every edge case, load scenario, failure mode, and
   missing test case in what the designer proposed or the developer plans to build.
   Do not write production code. Do not accept vague answers — demand specifics
   before any design decision is locked. Your job is to make the design fail
   on paper, not in production.
5. Call send_message("qa", your_response, channel="general")
6. Wait 30 seconds, then go to step 1
```

---

## 5. Seed the Conversation

Once all three agents are running, paste this into the browser UI at `http://localhost:9001`:

```
We're building "Flock" — a Twitter/X replacement. v1 must support:

- User accounts and profiles
- Posts up to 280 characters with optional image or video attachment
- Follow / unfollow
- A ranked home feed showing posts from people you follow (newest first for now)
- Notifications: likes, follows, replies
- Basic search: users and posts by keyword

Start with the foundational decisions: data model, feed architecture, and the
API contract between the Feed Service and the client. What are the choices
we'll regret most if we get them wrong?
```

The agents will pick it up on their next poll and the conversation will start automatically.

---

## 6. Steer and Export

**Guide the conversation at any time** by posting from the browser UI:

| Goal | Example message |
|---|---|
| Add a constraint | `Budget constraint — no Kafka, no managed queues` |
| Inject a late requirement | `We also need direct messages for v1` |
| Force a decision | `Designer: QA has raised three open questions. Please resolve all three before we proceed` |
| Timebox a topic | `Let's table search for now and focus on the feed architecture` |

**Export the full transcript when you're done:**

```bash
.venv/bin/python export_chat.py databases/flock.db chat_logs/flock-$(date +%Y-%m-%d).md
```

---

## Want a Faster Setup? Use 2 Agents

Skip the QA tab and combine designer + QA into a single Architect agent for faster iteration:

**Agent 1 — Architect** *(designer + QA combined)*

```
Call join_chat with agent_name="architect" and preferred_role="designer".
Treat the returned system_header as your permanent role context for this session.

Run the following loop until stopped:
1. Call read_latest("architect", channel="general") — check who spoke last
2. If the last message was from me, wait 20 seconds and repeat from step 1
3. Call read_all("architect", channel="general") — get full context
4. Respond as the ARCHITECT: propose data models and system design, then
   immediately stress-test your own proposal before handing it off.
   Ask yourself: what breaks at scale? What's underspecified? What would a
   skeptical QA engineer demand you clarify? Revise before passing to the developer.
5. Call send_message("architect", your_response, channel="general")
6. Wait 20 seconds, then go to step 1
```

**Agent 2 — Developer** *(same prompt as the 3-agent version above)*

> **Tradeoff:** The architect self-edits, but it won't have the adversarial sharpness of a truly independent QA agent. Use 2 agents for exploration and prototyping; use 3 when production quality matters.

---

## What to Expect

Within the first few exchanges the conversation splits naturally:

- The **Designer** drafts an initial data model and feed architecture
- The **Developer** raises missing specs — pagination strategy? media storage? auth method?
- The **QA** agent stress-tests every assumption — what's the write amplification for a 50M-follower account? what happens when search indexes lag?

You'll watch the design evolve through genuine friction, not consensus. That friction is the point.
