"""
main.py — Entry point.

    python main.py mcp  [db] [roles]        # run MCP stdio server
    python main.py ui   [db] [roles] [port] # run UI HTTP server
    python main.py both [db] [roles] [port] # run both (UI in thread, MCP on stdio)
"""
import asyncio
import sys
import threading

DEFAULT_DB    = "databases/agentcy.db"
DEFAULT_ROLES = "roles.json"
DEFAULT_PORT  = 9001


def run_ui(db: str, roles: str, port: int) -> None:
    import uvicorn
    from src.api.server import create_ui_app
    uvicorn.run(create_ui_app(db, roles), host="0.0.0.0", port=port, log_level="warning")


def run_mcp(db: str, roles: str) -> None:
    from src.mcp.server import run
    asyncio.run(run(db, roles))


if __name__ == "__main__":
    mode  = sys.argv[1] if len(sys.argv) > 1 else "mcp"
    db    = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DB
    roles = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_ROLES
    port  = int(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_PORT

    if mode == "ui":
        run_ui(db, roles, port)

    elif mode == "mcp":
        run_mcp(db, roles)

    elif mode == "both":
        t = threading.Thread(target=run_ui, args=(db, roles, port), daemon=True)
        t.start()
        print(f"UI started at http://localhost:{port}", file=sys.stderr)
        run_mcp(db, roles)  # MCP blocks on stdio — runs in main thread

    else:
        print(f"Unknown mode: {mode!r}. Use: mcp | ui | both")
        sys.exit(1)
