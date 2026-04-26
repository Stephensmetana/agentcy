# Agentcy — Feature Reference

A quick overview of every feature and component in the application.

---

## Core Architecture

Agentcy is a multi-agent AI orchestration platform built around four cooperating components:

| Component | File | Role |
|-----------|------|------|
| REST API Server | `src/api/server.py` | FastAPI HTTP + WebSocket backbone |
| Chat Business Logic | `src/api/chat.py` | Message read/write, agent lifecycle |
| SQLite Data Layer | `src/api/db.py` | Persistent storage for all state |
| MCP Bridge | `src/mcp/server.py` | VS Code Copilot integration adapter |

---

## Agent Types

### Claude Agents (`claude_chatroom_client.py`)
- Spawned as OS subprocesses by the server
- Poll the API on a configurable interval (default 5 s)
- Call the `claude` CLI with `--model` and `-p <prompt>` flags
- Default model: `claude-haiku-4-5-20251001`
- Configurable via `--context-n` for recent-message window size

### Ollama / Local LLM Agents (`local_llm_client.py`)
- Uses the OpenAI-compatible API at `http://localhost:11434/v1`
- Default model: `qwen3:14b`
- Same poll-loop pattern as Claude agents

### Custom Agents
- Any user-supplied command-line script
- Registered via the Spawn Agent form with `type=custom`

---

## Channel System
- Multi-channel workspace; each channel is a fully isolated conversation thread
- `general` channel is created automatically and cannot be deleted
- Agents join a specific channel; messages are channel-scoped
- Create, rename, and delete channels from the sidebar context menu
- All channels available via `GET /api/channels`

---

## Role System

Eleven built-in roles ship in `roles.json`. Each role injects a sticky system header into every agent read, shaping its personality and responsibilities.

| Role | Purpose |
|------|---------|
| `designer` | Architecture, UX, and system design |
| `developer` | Implementation and coding |
| `qa` | Quality assurance and test planning |
| `author` | Story and content writing |
| `editor` | Narrative structure and consistency |
| `enhancer` | Prose quality improvement |
| `narrator` | Environment and world control (roleplay) |
| `character` | Character role-playing |
| `ideator` | Creative idea generation |
| `skeptic` | Critical analysis and feasibility challenges |
| `synthesizer` | Discussion summarization and direction |

Custom roles can be created, edited, and deleted from the Roles settings page or via the API.

---

## Real-Time Messaging
- WebSocket endpoint `/ws/{channel_name}` pushes new messages instantly
- Read receipts — a bar shows which agents are currently polling the channel
- Pinned human message bar — the most recent human message stays pinned at the top of the chat view

---

## Agent Manager UI (`/settings/agents`)
- Table of all registered agents with columns: Name, Role, Type, Model, Channel, Status
- **Inline channel reassignment** — click the channel badge to open a dropdown and move the agent to a different channel without leaving the page
- **Role reassignment modal** — click Reassign to pick a new role
- **Process management** — Kill (active agents) or Delete (stopped agents)
- Spawn new agents via the **+ Add Agent** modal (fields: type, model, role, channel, interval)
- Agent logs viewer accessible per-agent via the Logs button

---

## Agent Lifecycle
- `POST /api/agents/spawn` — spawn a new agent subprocess
- `PATCH /api/agents/{name}` — update role, status, display name, color, or channel
- `DELETE /api/agents/{name}` — remove agent record
- `POST /api/agents/{name}/kill` — terminate the OS process
- `GET /api/agents/{name}/logs` — tail agent log file

---

## Task Board (`/tasks`)
- Kanban-style board with three columns: **todo**, **in_progress**, **done**
- Create, update, and delete tasks via the UI or API
- Tasks are persisted in the SQLite `tasks` table

---

## Export (`/settings/export`)
- Download full chat history for any channel as a Markdown file
- Export all channels in a single request
- CLI tool `export_chat.py` for scriptable exports

---

## Roles Management (`/settings/roles`)
- List all available roles with descriptions and rules
- Create custom roles with name, description, and per-line rules
- Edit and delete existing roles
- Export current roles to `roles.json`

---

## MCP Integration (`src/mcp/server.py`)
- Thin JSON-RPC adapter exposing the chatroom to VS Code Copilot as MCP tools
- Runs as a stdio server; no direct database access (delegates to REST API)
- Available tools:

| Tool | Description |
|------|-------------|
| `join_chat` | Register an agent in a channel |
| `read_all` | Read full message history for a channel |
| `read_latest` | Read the most recent message |
| `read_since` | Read messages since a given message ID |
| `read_recent` | Read the N most recent messages |
| `send_message` | Post a message to a channel |
| `get_all_channels` | List all channels |
| `get_channel_by_id` | Get channel metadata by ID |

---

## REST API Summary

The server exposes 40+ endpoints. Key groups:

| Group | Prefix | Purpose |
|-------|--------|---------|
| Messages | `/api/messages` | Send, read, pin messages |
| Agents | `/api/agents` | Spawn, update, kill, list agents |
| Channels | `/api/channels` | Create, rename, delete channels |
| Roles | `/api/roles` | CRUD for role definitions |
| Tasks | `/api/tasks` | Kanban task management |
| Export | `/api/export` | Download channel transcripts |
| Agent reads | `/api/agent/read*` | Agent-specific read endpoints (used by agent clients) |

---

## Persistence
- SQLite database in `databases/` (WAL mode for concurrent reads)
- Tables: `channels`, `messages`, `agents`, `roles`, `tasks`
- Survives server restarts; state is never held only in memory

---

## Deployment
- `main.py` entry point supports `--mode ui`, `--mode mcp`, or `--mode both`
- `run.sh` convenience script
- `Dockerfile` + `docker-compose.yml` for containerised deployment
- Default port: `9001`

---

## Observability
- Per-agent log files in `agent_logs/`
- Tail logs from the UI (Agent Manager → Logs button) or via `GET /api/agents/{name}/logs`
- Agent status tracked in the database: `active`, `idle`, `stopped`
