"""
src/api/server.py — REST API + browser UI server.

Single source of truth for all business logic.
All other components (MCP bridge, agent clients) communicate via HTTP.

    python main.py ui databases/agentcy.db roles.json 9001
"""
import asyncio
import json
import os
import signal
import subprocess
import sys
import random
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from src.api.db import ChatDB
from src.api.chat import ChatRoom
from src.api.roles import build_system_header

# ---------------------------------------------------------------------------
# Adjective/noun lists for random agent names
# ---------------------------------------------------------------------------
_ADJECTIVES = [
    "swift", "amber", "cosmic", "silent", "bold", "nimble", "iron", "golden",
    "crystal", "shadow", "bright", "velvet", "jade", "azure", "scarlet", "lunar",
    "storm", "frost", "ember", "silver", "obsidian", "radiant", "noble", "mystic",
]
_NOUNS = [
    "falcon", "tide", "forge", "wolf", "pine", "hawk", "reef", "prism",
    "veil", "crest", "peak", "gale", "moss", "flare", "drift", "echo",
    "basin", "grove", "ridge", "vale", "birch", "comet", "dune", "arch",
]
_AVATAR_COLORS = [
    "#d2a8ff", "#79c0ff", "#ffa657", "#ff7b72", "#56d364", "#f0883e",
    "#a5d6ff", "#3fb950", "#e3b341", "#bc8cff", "#58a6ff", "#ff9900",
]


def random_agent_name() -> str:
    return f"{random.choice(_ADJECTIVES)}-{random.choice(_NOUNS)}"


def random_agent_color() -> str:
    return random.choice(_AVATAR_COLORS)


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        # channel_id → list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, ws: WebSocket, channel_id: str) -> None:
        await ws.accept()
        self._connections.setdefault(channel_id, []).append(ws)

    def disconnect(self, ws: WebSocket, channel_id: str) -> None:
        conns = self._connections.get(channel_id, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, payload: dict, channel_id: str) -> None:
        conns = self._connections.get(channel_id, [])
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in conns:
                conns.remove(ws)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def _format_export_md(messages: list[dict], channel_name: str) -> str:
    lines = [f"# Chat Export — #{channel_name}\n"]
    for m in messages:
        role_tag = f"[{m['role']}]" if m.get("role") else ""
        lines.append(f"**{m['sender']}** {role_tag}  _{m['timestamp']}_\n\n{m['content']}\n\n---\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_ui_app(db_path: str, roles_path: str) -> FastAPI:
    app = FastAPI(title="Agentcy")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    db = ChatDB(db_path)
    room = ChatRoom(db, roles_path)

    ui_file = Path(__file__).parent.parent.parent / "ui" / "index.html"

    def _serve_ui():
        if not ui_file.exists():
            return HTMLResponse("<h1>ui/index.html missing</h1>", status_code=404)
        return HTMLResponse(ui_file.read_text(encoding="utf-8"))

    # -----------------------------------------------------------------------
    # WebSocket
    # -----------------------------------------------------------------------

    @app.websocket("/ws/{channel_id}")
    async def ws_endpoint(websocket: WebSocket, channel_id: str):
        await manager.connect(websocket, channel_id)
        try:
            while True:
                await websocket.receive_text()  # keep-alive; clients send pings
        except WebSocketDisconnect:
            manager.disconnect(websocket, channel_id)

    # -----------------------------------------------------------------------
    # Messages
    # -----------------------------------------------------------------------

    @app.get("/api/messages")
    def get_messages(channel: str = Query(default="general")):
        return db.get_all_messages(channel=channel)

    @app.get("/api/messages/since/{message_id}")
    def get_messages_since(message_id: int, channel: str = Query(default="general")):
        return db.get_messages_since(message_id, channel=channel)

    @app.get("/api/messages/recent")
    def get_messages_recent(channel: str = Query(default="general"), n: int = Query(default=10)):
        return db.get_recent_messages(channel=channel, n=n)

    @app.get("/api/latest")
    def get_latest(channel: str = Query(default="general")):
        return db.get_latest_message(channel=channel) or {}

    @app.get("/api/pinned")
    def get_pinned(channel: str = Query(default="general")):
        """Return the most recent human user message for pinned display."""
        return db.get_latest_user_message(channel=channel) or {}

    @app.patch("/api/messages/{message_id}")
    async def update_message(message_id: int, body: dict):
        content = body.get("content", "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="content is required")
        msg = db.update_message(message_id, content)
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")
        await manager.broadcast({"type": "message_updated", "data": msg}, msg["channel"])
        return msg

    @app.delete("/api/messages/{message_id}")
    async def delete_message(message_id: int):
        msg = db.get_message_by_id(message_id)
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")
        db.delete_message(message_id)
        await manager.broadcast(
            {"type": "message_deleted", "data": {"id": message_id}}, msg["channel"]
        )
        return {"ok": True}

    @app.post("/api/messages")
    async def post_message(body: dict):
        content = body.get("content", "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="content is required")
        channel = body.get("channel", "general")
        sender = body.get("sender", "").strip()

        if sender and sender != "user":
            # Agent message
            msg = room.send_message(sender, content, channel=channel)
        else:
            # Human user message
            msg = room.send_user_message(content, channel=channel)

        await manager.broadcast({"type": "message", "data": msg}, channel)
        return msg

    # -----------------------------------------------------------------------
    # Agent join endpoint (used by HTTP-bridge MCP and client scripts)
    # -----------------------------------------------------------------------

    @app.post("/api/agent/join")
    async def agent_join(body: dict):
        agent_name = body.get("agent_name", "").strip()
        if not agent_name:
            raise HTTPException(status_code=400, detail="agent_name is required")
        result = room.join(
            agent_name=agent_name,
            preferred_role=body.get("preferred_role"),
            character_description=body.get("character_description"),
            display_name=body.get("display_name"),
            color=body.get("color"),
            agent_type=body.get("agent_type", "unknown"),
            model=body.get("model"),
            command=body.get("command"),
            channel=body.get("channel", "general"),
        )
        channel = body.get("channel", "general")
        # Broadcast the join system message
        msgs = db.get_all_messages(channel=channel)
        if msgs:
            await manager.broadcast({"type": "message", "data": msgs[-1]}, channel)
        return result

    @app.get("/api/agent/read_all")
    def agent_read_all(agent_name: str, channel: str = Query(default="general")):
        return {"text": room.read_all(agent_name, channel=channel)}

    @app.get("/api/agent/read_latest")
    def agent_read_latest(agent_name: str, channel: str = Query(default="general")):
        return room.read_latest(agent_name, channel=channel)

    @app.get("/api/agent/read_since")
    def agent_read_since(agent_name: str, last_id: int, channel: str = Query(default="general")):
        return room.read_since(agent_name, last_id, channel=channel)

    @app.get("/api/agent/read_recent")
    async def agent_read_recent(agent_name: str, channel: str = Query(default="general"), n: int = Query(default=10)):
        result = room.read_recent(agent_name, channel=channel, n=n)
        agent = db.get_agent(agent_name)
        if agent:
            await manager.broadcast({
                "type": "read_receipt",
                "agent_name": agent_name,
                "display_name": agent.get("display_name") or agent_name,
                "color": agent.get("color") or "#58a6ff",
                "channel": channel,
            }, channel)
        return result

    # -----------------------------------------------------------------------
    # Agents
    # -----------------------------------------------------------------------

    @app.get("/api/agents")
    def get_agents():
        return db.get_all_agents()

    @app.patch("/api/agents/{name}")
    def update_agent(name: str, body: dict):
        agent = db.update_agent(
            name,
            role=body.get("role"),
            status=body.get("status"),
            display_name=body.get("display_name"),
            color=body.get("color"),
            channel=body.get("channel"),
        )
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    @app.delete("/api/agents/{name}")
    def delete_agent(name: str):
        if not db.delete_agent(name):
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"ok": True}

    @app.post("/api/agents/spawn")
    async def spawn_agent(body: dict):
        """Spawn a new AI agent subprocess."""
        agent_type = body.get("type", "claude")
        model = body.get("model", "claude-haiku-4-5-20251001")
        role = body.get("role", "developer")
        channel = body.get("channel", "general")
        interval = int(body.get("interval", 5))
        custom_command = body.get("command", "")

        # Auto-assign name and color
        display_name = random_agent_name()
        # Ensure unique
        existing = {a["display_name"] for a in db.get_all_agents() if a.get("display_name")}
        attempts = 0
        while display_name in existing and attempts < 20:
            display_name = random_agent_name()
            attempts += 1
        color = random_agent_color()
        agent_name = display_name  # use as the internal key too

        base_url = "http://localhost:9001"
        scripts_dir = Path(__file__).parent.parent.parent

        if agent_type == "claude":
            cmd = [
                sys.executable,
                str(scripts_dir / "claude_chatroom_client.py"),
                "--name", agent_name,
                "--display-name", display_name,
                "--color", color,
                "--model", model,
                "--role", role,
                "--channel", channel,
                "--interval", str(interval),
                "--base-url", base_url,
            ]
        elif agent_type == "ollama":
            ollama_url = body.get("ollama_url", "http://localhost:11434")
            cmd = [
                sys.executable,
                str(scripts_dir / "local_llm_client.py"),
                "--name", agent_name,
                "--display-name", display_name,
                "--color", color,
                "--model", model,
                "--ollama-url", ollama_url,
                "--role", role,
                "--channel", channel,
                "--interval", str(interval),
                "--base-url", base_url,
            ]
        elif agent_type == "custom":
            if not custom_command:
                raise HTTPException(status_code=400, detail="command is required for custom agent type")
            cmd = custom_command.split()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown agent type: {agent_type!r}")

        # Allow tests (or custom deployments) to redirect logs via env var
        logs_dir = Path(os.environ.get("AGENTCY_LOGS_DIR", str(scripts_dir / "logs")))
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / f"{agent_name}.log"

        # Ensure ~/.local/bin is on PATH so `claude` can be found
        spawn_env = os.environ.copy()
        local_bin = str(Path.home() / ".local" / "bin")
        if local_bin not in spawn_env.get("PATH", ""):
            spawn_env["PATH"] = local_bin + ":" + spawn_env.get("PATH", "")

        try:
            log_file = open(log_path, "a")
            proc = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                cwd=str(scripts_dir),
                env=spawn_env,
            )
            pid = proc.pid
        except FileNotFoundError as e:
            raise HTTPException(status_code=500, detail=f"Failed to spawn agent: {e}")

        # Register agent in DB with PID
        db.register_agent(
            name=agent_name,
            role=role,
            display_name=display_name,
            color=color,
            agent_type=agent_type,
            model=model,
            command=" ".join(str(c) for c in cmd),
            channel=channel,
        )
        db.update_agent(agent_name, pid=pid, status="active")

        return {"agent_name": agent_name, "display_name": display_name, "color": color, "pid": pid}

    @app.delete("/api/agents/{name}/kill")
    def kill_agent(name: str):
        """Kill a running agent subprocess."""
        agent = db.get_agent(name)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        pid = agent.get("pid")
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass  # already dead
        db.update_agent(name, status="stopped", pid=None)
        return {"ok": True, "name": name}

    @app.get("/api/agents/{name}/logs")
    def get_agent_logs(name: str, tail: int = Query(default=100, ge=1, le=5000)):
        """Return the last N lines of an agent's log file."""
        scripts_dir = Path(__file__).parent.parent.parent
        logs_dir = Path(os.environ.get("AGENTCY_LOGS_DIR", str(scripts_dir / "logs")))
        log_path = logs_dir / f"{name}.log"
        if not log_path.exists():
            return PlainTextResponse("No log file found for this agent.\n")
        lines = log_path.read_text(errors="replace").splitlines()
        return PlainTextResponse("\n".join(lines[-tail:]) + "\n")

    # -----------------------------------------------------------------------
    # Channels
    # -----------------------------------------------------------------------

    @app.get("/api/channels")
    def get_channels():
        return db.get_all_channels()

    @app.get("/api/channels/{channel_id}")
    def get_channel(channel_id: int):
        ch = db.get_channel_by_id(channel_id)
        if not ch:
            raise HTTPException(status_code=404, detail="Channel not found")
        return ch

    @app.post("/api/channels")
    def create_channel(body: dict):
        name = body.get("name", "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        try:
            return db.create_channel(name)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    @app.patch("/api/channels/{channel_id}")
    def rename_channel(channel_id: int, body: dict):
        new_name = body.get("name", "").strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="name is required")
        try:
            ch = db.rename_channel(channel_id, new_name)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        if not ch:
            raise HTTPException(status_code=404, detail="Channel not found")
        return ch

    @app.delete("/api/channels/{channel_id}")
    def delete_channel(channel_id: int):
        ch = db.get_channel_by_id(channel_id)
        if not ch:
            raise HTTPException(status_code=404, detail="Channel not found")
        if not db.delete_channel(channel_id):
            raise HTTPException(status_code=404, detail="Channel not found")
        return {"ok": True}

    # -----------------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------------

    @app.get("/api/export")
    def export_channel(channel: str = Query(...), fmt: str = Query(default="md")):
        """Export all messages from a channel as markdown (download)."""
        messages = db.get_all_messages(channel=channel)
        content = _format_export_md(messages, channel)
        filename = f"chat_export_{channel}.md"
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/export/all")
    def export_all():
        """Export all channels as a single markdown file."""
        channels = db.get_all_channels()
        parts = []
        for ch in channels:
            messages = db.get_all_messages(channel=ch["name"])
            parts.append(_format_export_md(messages, ch["name"]))
        content = "\n\n".join(parts)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": 'attachment; filename="chat_export_all.md"'},
        )

    # -----------------------------------------------------------------------
    # Roles
    # -----------------------------------------------------------------------

    @app.get("/api/roles")
    def get_roles():
        return db.get_all_roles()

    @app.post("/api/roles")
    def create_role(body: dict):
        name = body.get("name", "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        try:
            return db.create_role(
                name=name,
                description=body.get("description", ""),
                rules=body.get("rules", []),
            )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    @app.put("/api/roles/{name}")
    def update_role(name: str, body: dict):
        role = db.update_role(
            name,
            description=body.get("description"),
            rules=body.get("rules"),
        )
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return role

    @app.delete("/api/roles/{name}")
    def delete_role(name: str):
        if not db.delete_role(name):
            raise HTTPException(status_code=404, detail="Role not found")
        return {"ok": True}

    @app.get("/api/roles/export")
    def export_roles():
        """Export all roles as roles.json (download)."""
        roles = db.get_all_roles()
        # Strip DB-specific fields
        export = [
            {k: v for k, v in r.items() if k not in ("id", "created_at")}
            for r in roles
        ]
        return Response(
            content=json.dumps(export, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="roles.json"'},
        )

    # -----------------------------------------------------------------------
    # Tasks
    # -----------------------------------------------------------------------

    @app.get("/api/tasks")
    def get_tasks(channel: Optional[str] = Query(default=None)):
        return db.get_all_tasks(channel=channel)

    @app.get("/api/tasks/{task_id}")
    def get_task(task_id: int):
        task = db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @app.post("/api/tasks")
    def create_task(body: dict):
        title = body.get("title", "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="title is required")
        return db.create_task(
            title=title,
            description=body.get("description", ""),
            channel=body.get("channel", "general"),
            status=body.get("status", "todo"),
        )

    @app.patch("/api/tasks/{task_id}")
    def update_task(task_id: int, body: dict):
        task = db.update_task(
            task_id,
            title=body.get("title"),
            description=body.get("description"),
            status=body.get("status"),
            channel=body.get("channel"),
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @app.delete("/api/tasks/{task_id}")
    def delete_task(task_id: int):
        if not db.delete_task(task_id):
            raise HTTPException(status_code=404, detail="Task not found")
        return {"ok": True}

    # -----------------------------------------------------------------------
    # Channel notes
    # -----------------------------------------------------------------------

    @app.get("/api/notes")
    def get_notes(channel: str = Query(default="general")):
        return db.get_notes(channel)

    @app.post("/api/notes")
    def add_note(body: dict):
        channel = body.get("channel", "general")
        content = body.get("content", "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="content is required")
        return db.add_note(channel, content)

    @app.patch("/api/notes/{note_id}")
    def update_note(note_id: int, body: dict):
        content = body.get("content", "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="content is required")
        note = db.update_note(note_id, content)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return note

    @app.delete("/api/notes/{note_id}")
    def delete_note(note_id: int):
        if not db.delete_note(note_id):
            raise HTTPException(status_code=404, detail="Note not found")
        return {"ok": True}

    # -----------------------------------------------------------------------
    # SPA: serve index.html for all browser routes
    # -----------------------------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    def serve_root():
        return _serve_ui()

    @app.get("/channel/{channel_id:path}", response_class=HTMLResponse)
    def serve_channel(channel_id: str):  # noqa: ARG001
        return _serve_ui()

    @app.get("/settings", response_class=HTMLResponse)
    def serve_settings():
        return _serve_ui()

    @app.get("/settings/{page:path}", response_class=HTMLResponse)
    def serve_settings_page(page: str):  # noqa: ARG001
        return _serve_ui()

    @app.get("/tasks", response_class=HTMLResponse)
    def serve_tasks():
        return _serve_ui()

    @app.get("/tasks/{task_id}", response_class=HTMLResponse)
    def serve_task_detail(task_id: str):  # noqa: ARG001
        return _serve_ui()

    return app


if __name__ == "__main__":
    import uvicorn
    _db    = sys.argv[1] if len(sys.argv) > 1 else "databases/agentcy.db"
    _roles = sys.argv[2] if len(sys.argv) > 2 else "roles.json"
    _port  = int(sys.argv[3]) if len(sys.argv) > 3 else 9001
    app = create_ui_app(_db, _roles)
    print(f"UI → http://localhost:{_port}  |  DB → {_db}")
    uvicorn.run(app, host="0.0.0.0", port=_port)
