"""
db.py — SQLite data layer for Agentcy

All database operations live here. No business logic.
The DB file path is passed in, making it easy to point at
a workspace file or a test fixture.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    created_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp  TEXT    NOT NULL,
    sender     TEXT    NOT NULL,
    role       TEXT,
    content    TEXT    NOT NULL,
    channel    TEXT    NOT NULL DEFAULT 'general'
);

CREATE TABLE IF NOT EXISTS agents (
    name                  TEXT PRIMARY KEY,
    role                  TEXT NOT NULL,
    joined_at             TEXT NOT NULL,
    last_seen             TEXT,
    character_description TEXT
);
"""


class ChatDB:
    """Thin wrapper around SQLite. All methods are synchronous."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # safe for concurrent readers
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            # Migration: add character_description column to pre-existing databases
            agent_cols = {row[1] for row in conn.execute("PRAGMA table_info(agents)").fetchall()}
            if "character_description" not in agent_cols:
                conn.execute("ALTER TABLE agents ADD COLUMN character_description TEXT")
            # Migration: add channel column to pre-existing databases
            msg_cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
            if "channel" not in msg_cols:
                conn.execute("ALTER TABLE messages ADD COLUMN channel TEXT NOT NULL DEFAULT 'general'")
            # Seed the default channel
            conn.execute(
                "INSERT OR IGNORE INTO channels (name, created_at) VALUES ('general', ?)",
                (self._now(),),
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Message operations
    # ------------------------------------------------------------------

    def insert_message(
        self,
        sender: str,
        content: str,
        role: Optional[str] = None,
        channel: str = "general",
    ) -> dict:
        """Append a message. Returns the saved row as a dict."""
        ts = self._now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO messages (timestamp, sender, role, content, channel) VALUES (?, ?, ?, ?, ?)",
                (ts, sender, role, content, channel),
            )
            return {
                "id": cur.lastrowid,
                "timestamp": ts,
                "sender": sender,
                "role": role,
                "content": content,
                "channel": channel,
            }

    def get_all_messages(self, channel: str = "general") -> list[dict]:
        """Return every message in a channel, in insertion order."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, sender, role, content, channel FROM messages "
                "WHERE channel = ? ORDER BY id",
                (channel,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_latest_message(self, channel: str = "general") -> Optional[dict]:
        """Return the most recent message in a channel, or None if empty."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, timestamp, sender, role, content, channel "
                "FROM messages WHERE channel = ? ORDER BY id DESC LIMIT 1",
                (channel,),
            ).fetchone()
            return dict(row) if row else None

    def get_messages_since(self, message_id: int, channel: str = "general") -> list[dict]:
        """Return all messages with id > message_id in a channel."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, sender, role, content, channel "
                "FROM messages WHERE id > ? AND channel = ? ORDER BY id",
                (message_id, channel),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Channel operations
    # ------------------------------------------------------------------

    def get_all_channels(self) -> list[dict]:
        """Return all channels ordered by id."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, created_at FROM channels ORDER BY id"
            ).fetchall()
            return [dict(r) for r in rows]

    def create_channel(self, name: str) -> dict:
        """Create a new channel. Raises ValueError if name already exists."""
        ts = self._now()
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "INSERT INTO channels (name, created_at) VALUES (?, ?)",
                    (name, ts),
                )
                return {"id": cur.lastrowid, "name": name, "created_at": ts}
        except sqlite3.IntegrityError:
            raise ValueError(f"Channel {name!r} already exists")

    def get_channel_by_id(self, channel_id: int) -> Optional[dict]:
        """Return a channel by its numeric id, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, created_at FROM channels WHERE id = ?",
                (channel_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_channel_by_name(self, name: str) -> Optional[dict]:
        """Return a channel by name, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, created_at FROM channels WHERE name = ?",
                (name,),
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # Agent operations
    # ------------------------------------------------------------------

    def register_agent(self, name: str, role: str, character_description: Optional[str] = None) -> dict:
        """Insert or update an agent record."""
        ts = self._now()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO agents (name, role, joined_at, last_seen, character_description)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE
                   SET role = excluded.role, last_seen = excluded.last_seen,
                       character_description = excluded.character_description""",
                (name, role, ts, ts, character_description),
            )
            return {"name": name, "role": role, "joined_at": ts, "character_description": character_description}

    def update_agent_seen(self, name: str) -> None:
        """Stamp last_seen for an active agent."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE agents SET last_seen = ? WHERE name = ?",
                (self._now(), name),
            )

    def get_agent(self, name: str) -> Optional[dict]:
        """Return a single agent by name, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT name, role, joined_at, last_seen, character_description FROM agents WHERE name = ?",
                (name,),
            ).fetchone()
            return dict(row) if row else None

    def get_all_agents(self) -> list[dict]:
        """Return all registered agents."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, role, joined_at, last_seen, character_description FROM agents ORDER BY joined_at"
            ).fetchall()
            return [dict(r) for r in rows]
