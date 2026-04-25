"""
src/api/server.py — REST API + browser UI server.

This is the single source of truth for all business logic.
All other components (MCP bridge, agent clients) communicate via HTTP.

    python main.py ui databases/agentcy.db roles.json 8000
"""
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from src.api.db import ChatDB
from src.api.chat import ChatRoom


def create_ui_app(db_path: str, roles_path: str) -> FastAPI:
    app = FastAPI(title="Agentcy")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    db = ChatDB(db_path)
    room = ChatRoom(db, roles_path)

    @app.get("/api/messages")
    def get_messages():
        return db.get_all_messages()

    @app.get("/api/messages/since/{message_id}")
    def get_messages_since(message_id: int):
        return db.get_messages_since(message_id)

    @app.get("/api/latest")
    def get_latest():
        return db.get_latest_message() or {}

    @app.get("/api/agents")
    def get_agents():
        return db.get_all_agents()

    @app.post("/api/messages")
    def post_user_message(body: dict):
        content = body.get("content", "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="content is required")
        return room.send_user_message(content)

    ui_file = Path(__file__).parent.parent.parent / "ui" / "index.html"

    @app.get("/", response_class=HTMLResponse)
    def serve_ui():
        if not ui_file.exists():
            return HTMLResponse("<h1>ui/index.html missing</h1>", status_code=404)
        return HTMLResponse(ui_file.read_text(encoding="utf-8"))

    return app


if __name__ == "__main__":
    import uvicorn
    _db    = sys.argv[1] if len(sys.argv) > 1 else "databases/agentcy.db"
    _roles = sys.argv[2] if len(sys.argv) > 2 else "roles.json"
    _port  = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
    app = create_ui_app(_db, _roles)
    print(f"UI → http://localhost:{_port}  |  DB → {_db}")
    uvicorn.run(app, host="0.0.0.0", port=_port)
