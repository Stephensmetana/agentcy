"""
db.py — SQLite data layer for Agentcy

All database operations live here. No business logic.
The DB file path is passed in, making it easy to point at
a workspace file or a test fixture.
"""

import json
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
    display_name          TEXT,
    color                 TEXT,
    role                  TEXT NOT NULL,
    agent_type            TEXT NOT NULL DEFAULT 'unknown',
    model                 TEXT,
    command               TEXT,
    pid                   INTEGER,
    status                TEXT NOT NULL DEFAULT 'active',
    channel               TEXT NOT NULL DEFAULT 'general',
    joined_at             TEXT NOT NULL,
    last_seen             TEXT,
    character_description TEXT
);

CREATE TABLE IF NOT EXISTS roles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT    NOT NULL DEFAULT '',
    rules       TEXT    NOT NULL DEFAULT '[]',
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    description TEXT    DEFAULT '',
    status      TEXT    NOT NULL DEFAULT 'todo',
    channel     TEXT    NOT NULL DEFAULT 'general',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS channel_notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    channel    TEXT    NOT NULL DEFAULT 'general',
    content    TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);
"""


class ChatDB:
    """Thin wrapper around SQLite. All methods are synchronous."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
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
            # Migrate old messages table — add channel column if missing
            msg_cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
            if "channel" not in msg_cols:
                conn.execute("ALTER TABLE messages ADD COLUMN channel TEXT NOT NULL DEFAULT 'general'")
            # Migrate old agents table — add new columns if missing
            agent_cols = {row[1] for row in conn.execute("PRAGMA table_info(agents)").fetchall()}
            for col, typedef in [
                ("character_description", "TEXT"),
                ("display_name", "TEXT"),
                ("color", "TEXT"),
                ("agent_type", "TEXT NOT NULL DEFAULT 'unknown'"),
                ("model", "TEXT"),
                ("command", "TEXT"),
                ("pid", "INTEGER"),
                ("status", "TEXT NOT NULL DEFAULT 'active'"),
                ("channel", "TEXT NOT NULL DEFAULT 'general'"),
            ]:
                if col not in agent_cols:
                    conn.execute(f"ALTER TABLE agents ADD COLUMN {col} {typedef}")
            # Seed the default channel
            conn.execute(
                "INSERT OR IGNORE INTO channels (name, created_at) VALUES ('general', ?)",
                (self._now(),),
            )
            # Migrate roles table — drop max_active if it still exists
            role_cols = {row[1] for row in conn.execute("PRAGMA table_info(roles)").fetchall()}
            if "max_active" in role_cols:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS roles_new (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        name        TEXT    NOT NULL UNIQUE,
                        description TEXT    NOT NULL DEFAULT '',
                        rules       TEXT    NOT NULL DEFAULT '[]',
                        created_at  TEXT    NOT NULL
                    );
                    INSERT INTO roles_new (id, name, description, rules, created_at)
                        SELECT id, name, description, rules, created_at FROM roles;
                    DROP TABLE roles;
                    ALTER TABLE roles_new RENAME TO roles;
                """)

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

    def get_recent_messages(self, channel: str = "general", n: int = 10) -> list[dict]:
        """Return the N most recent messages in a channel (chronological order)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, sender, role, content, channel "
                "FROM messages WHERE channel = ? ORDER BY id DESC LIMIT ?",
                (channel, n),
            ).fetchall()
            return [dict(r) for r in reversed(rows)]

    def get_latest_user_message(self, channel: str = "general") -> Optional[dict]:
        """Return the most recent human user message in a channel, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, timestamp, sender, role, content, channel "
                "FROM messages WHERE channel = ? AND sender = 'user' ORDER BY id DESC LIMIT 1",
                (channel,),
            ).fetchone()
            return dict(row) if row else None

    def get_message_by_id(self, message_id: int) -> Optional[dict]:
        """Return a single message by id, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, timestamp, sender, role, content, channel FROM messages WHERE id = ?",
                (message_id,),
            ).fetchone()
            return dict(row) if row else None

    def update_message(self, message_id: int, content: str) -> Optional[dict]:
        """Update a message's content. Returns the updated message or None if not found."""
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE messages SET content = ? WHERE id = ?",
                (content, message_id),
            )
            if cur.rowcount == 0:
                return None
        return self.get_message_by_id(message_id)

    def delete_message(self, message_id: int) -> bool:
        """Delete a message by id. Returns True if deleted."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
            return cur.rowcount > 0

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

    def rename_channel(self, channel_id: int, new_name: str) -> Optional[dict]:
        """Rename a channel by id. Returns updated channel or None if not found."""
        # Look up old name before modifying
        old = self.get_channel_by_id(channel_id)
        if not old:
            return None
        old_name = old["name"]
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "UPDATE channels SET name = ? WHERE id = ?",
                    (new_name, channel_id),
                )
                if cur.rowcount == 0:
                    return None
                # Also update channel column in messages (use old_name, not subquery)
                conn.execute(
                    "UPDATE messages SET channel = ? WHERE channel = ?",
                    (new_name, old_name),
                )
        except sqlite3.IntegrityError:
            raise ValueError(f"Channel {new_name!r} already exists")
        return self.get_channel_by_id(channel_id)

    def delete_channel(self, channel_id: int) -> bool:
        """Delete a channel and its messages. Returns True if deleted."""
        channel = self.get_channel_by_id(channel_id)
        if not channel:
            return False
        with self._connect() as conn:
            conn.execute("DELETE FROM messages WHERE channel = ?", (channel["name"],))
            conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        return True

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

    def register_agent(
        self,
        name: str,
        role: str,
        character_description: Optional[str] = None,
        display_name: Optional[str] = None,
        color: Optional[str] = None,
        agent_type: str = "unknown",
        model: Optional[str] = None,
        command: Optional[str] = None,
        channel: str = "general",
    ) -> dict:
        """Insert or update an agent record."""
        ts = self._now()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO agents
                   (name, display_name, color, role, agent_type, model, command,
                    status, channel, joined_at, last_seen, character_description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE
                   SET role = excluded.role,
                       last_seen = excluded.last_seen,
                       character_description = excluded.character_description,
                       display_name = COALESCE(excluded.display_name, agents.display_name),
                       color = COALESCE(excluded.color, agents.color),
                       agent_type = excluded.agent_type,
                       model = excluded.model,
                       command = excluded.command,
                       channel = excluded.channel,
                       status = 'active'
                """,
                (name, display_name, color, role, agent_type, model, command, channel, ts, ts, character_description),
            )
            return self.get_agent(name)

    def update_agent_seen(self, name: str) -> None:
        """Stamp last_seen for an active agent."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE agents SET last_seen = ? WHERE name = ?",
                (self._now(), name),
            )

    def update_agent(
        self,
        name: str,
        role: Optional[str] = None,
        status: Optional[str] = None,
        pid: Optional[int] = None,
        display_name: Optional[str] = None,
        color: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> Optional[dict]:
        """Partial update of an agent. Returns updated agent or None if not found."""
        agent = self.get_agent(name)
        if not agent:
            return None
        updates = {}
        if role is not None:
            updates["role"] = role
        if status is not None:
            updates["status"] = status
        if pid is not None:
            updates["pid"] = pid
        if display_name is not None:
            updates["display_name"] = display_name
        if color is not None:
            updates["color"] = color
        if channel is not None:
            updates["channel"] = channel
        if not updates:
            return agent
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE agents SET {set_clause} WHERE name = ?",
                (*updates.values(), name),
            )
        return self.get_agent(name)

    def delete_agent(self, name: str) -> bool:
        """Remove an agent record. Returns True if deleted."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM agents WHERE name = ?", (name,))
            return cur.rowcount > 0

    def get_agent(self, name: str) -> Optional[dict]:
        """Return a single agent by name, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT name, display_name, color, role, agent_type, model, command, "
                "pid, status, channel, joined_at, last_seen, character_description "
                "FROM agents WHERE name = ?",
                (name,),
            ).fetchone()
            return dict(row) if row else None

    def get_all_agents(self) -> list[dict]:
        """Return all registered agents."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, display_name, color, role, agent_type, model, command, "
                "pid, status, channel, joined_at, last_seen, character_description "
                "FROM agents ORDER BY joined_at"
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Role operations
    # ------------------------------------------------------------------

    def get_all_roles(self) -> list[dict]:
        """Return all roles ordered by id."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, description, rules, created_at FROM roles ORDER BY id"
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["rules"] = json.loads(d["rules"])
                result.append(d)
            return result

    def get_role_by_name(self, name: str) -> Optional[dict]:
        """Return a role by name, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, description, rules, created_at FROM roles WHERE name = ?",
                (name,),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["rules"] = json.loads(d["rules"])
            return d

    def create_role(self, name: str, description: str, rules: list) -> dict:
        """Create a new role. Raises ValueError if name already exists."""
        ts = self._now()
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "INSERT INTO roles (name, description, rules, created_at) VALUES (?, ?, ?, ?)",
                    (name, description, json.dumps(rules), ts),
                )
                return {
                    "id": cur.lastrowid,
                    "name": name,
                    "description": description,
                    "rules": rules,
                    "created_at": ts,
                }
        except sqlite3.IntegrityError:
            raise ValueError(f"Role {name!r} already exists")

    def update_role(
        self,
        name: str,
        description: Optional[str] = None,
        rules: Optional[list] = None,
    ) -> Optional[dict]:
        """Update a role. Returns updated role or None if not found."""
        role = self.get_role_by_name(name)
        if not role:
            return None
        updates = {}
        if description is not None:
            updates["description"] = description
        if rules is not None:
            updates["rules"] = json.dumps(rules)
        if not updates:
            return role
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE roles SET {set_clause} WHERE name = ?",
                (*updates.values(), name),
            )
        return self.get_role_by_name(name)

    def delete_role(self, name: str) -> bool:
        """Delete a role. Returns True if deleted."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM roles WHERE name = ?", (name,))
            return cur.rowcount > 0

    def seed_roles_from_list(self, roles: list[dict]) -> None:
        """Seed the roles table from a list of role dicts. Skips existing roles."""
        for role in roles:
            try:
                self.create_role(
                    name=role["name"],
                    description=role.get("description", ""),
                    rules=role.get("rules", []),
                )
            except ValueError:
                pass  # already exists

    def roles_are_seeded(self) -> bool:
        """Return True if the roles table has at least one entry."""
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0]
            return count > 0

    # ------------------------------------------------------------------
    # Task operations
    # ------------------------------------------------------------------

    def get_all_tasks(self, channel: Optional[str] = None) -> list[dict]:
        """Return all tasks, optionally filtered by channel."""
        with self._connect() as conn:
            if channel:
                rows = conn.execute(
                    "SELECT id, title, description, status, channel, created_at, updated_at "
                    "FROM tasks WHERE channel = ? ORDER BY id",
                    (channel,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, title, description, status, channel, created_at, updated_at "
                    "FROM tasks ORDER BY id"
                ).fetchall()
            return [dict(r) for r in rows]

    def get_task(self, task_id: int) -> Optional[dict]:
        """Return a task by id, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, title, description, status, channel, created_at, updated_at "
                "FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            return dict(row) if row else None

    def create_task(self, title: str, description: str = "", channel: str = "general", status: str = "todo") -> dict:
        """Create a new task."""
        ts = self._now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, description, status, channel, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (title, description, status, channel, ts, ts),
            )
            return {
                "id": cur.lastrowid,
                "title": title,
                "description": description,
                "status": status,
                "channel": channel,
                "created_at": ts,
                "updated_at": ts,
            }

    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> Optional[dict]:
        """Update a task. Returns updated task or None if not found."""
        task = self.get_task(task_id)
        if not task:
            return None
        updates = {"updated_at": self._now()}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if status is not None:
            updates["status"] = status
        if channel is not None:
            updates["channel"] = channel
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE tasks SET {set_clause} WHERE id = ?",
                (*updates.values(), task_id),
            )
        return self.get_task(task_id)

    def delete_task(self, task_id: int) -> bool:
        """Delete a task. Returns True if deleted."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Channel notes operations
    # ------------------------------------------------------------------

    def get_notes(self, channel: str = "general") -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, channel, content, created_at FROM channel_notes WHERE channel = ? ORDER BY id ASC",
                (channel,),
            ).fetchall()
            return [dict(r) for r in rows]

    def add_note(self, channel: str, content: str) -> dict:
        ts = self._now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO channel_notes (channel, content, created_at) VALUES (?, ?, ?)",
                (channel, content, ts),
            )
            return {"id": cur.lastrowid, "channel": channel, "content": content, "created_at": ts}

    def update_note(self, note_id: int, content: str) -> Optional[dict]:
        with self._connect() as conn:
            conn.execute("UPDATE channel_notes SET content = ? WHERE id = ?", (content, note_id))
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, channel, content, created_at FROM channel_notes WHERE id = ?", (note_id,)
            ).fetchone()
            return dict(row) if row else None

    def delete_note(self, note_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM channel_notes WHERE id = ?", (note_id,))
            return cur.rowcount > 0
