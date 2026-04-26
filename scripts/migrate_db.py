"""
scripts/migrate_db.py — Migrate legacy chatroom.db to databases/agentcy.db.

What this does:
1. Reads all messages from the legacy chatroom.db at the project root
2. Creates the databases/ folder if needed
3. Initialises databases/agentcy.db with the full current schema
4. Creates a 'civitai-redesign' channel in the new DB
5. Copies all messages from legacy DB into 'civitai-redesign' channel
6. Copies all agents from legacy DB into the new agents table

Usage:
    python scripts/migrate_db.py                           # auto-detect paths
    python scripts/migrate_db.py chatroom.db databases/agentcy.db
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path so we can import ChatDB
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.api.db import ChatDB


def migrate(legacy_path: str, new_path: str) -> None:
    legacy = Path(legacy_path)
    if not legacy.exists():
        print(f"[migrate] Legacy DB not found at {legacy_path} — nothing to migrate.")
        return

    print(f"[migrate] Reading from: {legacy_path}")
    src = sqlite3.connect(str(legacy))
    src.row_factory = sqlite3.Row

    # Load messages
    try:
        messages = [dict(r) for r in src.execute(
            "SELECT timestamp, sender, role, content FROM messages ORDER BY id"
        ).fetchall()]
    except sqlite3.OperationalError:
        messages = []
    print(f"[migrate] Found {len(messages)} messages")

    # Load agents
    try:
        agents = [dict(r) for r in src.execute(
            "SELECT name, role, joined_at, last_seen, character_description FROM agents"
        ).fetchall()]
    except sqlite3.OperationalError:
        agents = []
    print(f"[migrate] Found {len(agents)} agents")

    src.close()

    # Initialise new DB
    print(f"[migrate] Writing to: {new_path}")
    db = ChatDB(new_path)

    # Create civitai-redesign channel
    target_channel = "civitai-redesign"
    try:
        db.create_channel(target_channel)
        print(f"[migrate] Created channel '{target_channel}'")
    except ValueError:
        print(f"[migrate] Channel '{target_channel}' already exists — skipping creation")

    # Migrate messages
    migrated_msgs = 0
    conn = sqlite3._connect = sqlite3.connect(new_path)  # noqa — reuse connection
    conn = sqlite3.connect(new_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    for m in messages:
        conn.execute(
            "INSERT INTO messages (timestamp, sender, role, content, channel) VALUES (?, ?, ?, ?, ?)",
            (m.get("timestamp"), m.get("sender"), m.get("role"), m.get("content"), target_channel),
        )
        migrated_msgs += 1
    conn.commit()
    print(f"[migrate] Migrated {migrated_msgs} messages → #{target_channel}")

    # Migrate agents
    migrated_agents = 0
    for a in agents:
        try:
            db.register_agent(
                name=a["name"],
                role=a["role"],
                character_description=a.get("character_description"),
            )
            migrated_agents += 1
        except Exception as e:
            print(f"[migrate]   Agent '{a['name']}' skipped: {e}")
    conn.close()
    print(f"[migrate] Migrated {migrated_agents} agents")
    print("[migrate] Done.")


if __name__ == "__main__":
    root = Path(__file__).parent.parent
    legacy = sys.argv[1] if len(sys.argv) > 1 else str(root / "chatroom.db")
    target = sys.argv[2] if len(sys.argv) > 2 else str(root / "databases" / "agentcy.db")
    migrate(legacy, target)
