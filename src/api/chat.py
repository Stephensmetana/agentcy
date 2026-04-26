"""
chat.py — ChatRoom: the single business-logic class.

Sits between the MCP server (or tests) and the raw DB layer.
All methods are synchronous; the MCP server wraps them in async as needed.
"""

from typing import Optional

from src.api.db import ChatDB
from src.api.roles import assign_role, build_system_header, load_roles


class ChatRoom:
    """
    Encapsulates all chatroom operations.

    db         — ChatDB instance (SQLite)
    roles_path — path to roles.json (used for seeding the DB on first run)
    """

    def __init__(self, db: ChatDB, roles_path: str):
        self.db = db
        # Seed DB from JSON on first run; always load from DB thereafter
        if not db.roles_are_seeded():
            try:
                file_roles = load_roles(roles_path)
                db.seed_roles_from_list(file_roles)
            except (FileNotFoundError, Exception):
                pass
        self.roles_path = roles_path

    def _get_roles(self) -> list[dict]:
        """Load role definitions from DB."""
        return self.db.get_all_roles()

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def join(
        self,
        agent_name: str,
        preferred_role: Optional[str] = None,
        character_description: Optional[str] = None,
        display_name: Optional[str] = None,
        color: Optional[str] = None,
        agent_type: str = "unknown",
        model: Optional[str] = None,
        command: Optional[str] = None,
        channel: str = "general",
    ) -> dict:
        """
        Register an agent, assign a role, post a join notice, return the
        sticky system header.
        """
        roles = self._get_roles()
        active = [a for a in self.db.get_all_agents() if a.get("status") != "stopped"]
        role = assign_role(roles, active, preferred=preferred_role)

        self.db.register_agent(
            agent_name,
            role["name"],
            character_description=character_description,
            display_name=display_name,
            color=color,
            agent_type=agent_type,
            model=model,
            command=command,
            channel=channel,
        )
        self.db.insert_message(
            sender="system",
            content=f"{display_name or agent_name} joined as {role['name'].upper()}",
            role="system",
            channel=channel,
        )

        return {
            "agent_name": agent_name,
            "role": role["name"],
            "system_header": build_system_header(role, character_description=character_description),
        }

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def read_all(self, agent_name: str, channel: str = "general") -> str:
        """Return sticky system header + full chat history for a channel."""
        self.db.update_agent_seen(agent_name)
        header = self._header_for(agent_name, channel)
        messages = self.db.get_all_messages(channel=channel)
        chat_block = self._format_messages(messages)
        return f"{header}\n[CHAT LOG — {channel} — {len(messages)} messages]\n\n{chat_block}"

    def read_latest(self, agent_name: str, channel: str = "general") -> dict:
        """Return sticky system header + the single most recent message in a channel."""
        self.db.update_agent_seen(agent_name)
        header = self._header_for(agent_name, channel)
        latest = self.db.get_latest_message(channel=channel)
        return {
            "system_header": header,
            "channel": channel,
            "latest_message": latest,
        }

    def read_since(self, agent_name: str, last_id: int, channel: str = "general") -> dict:
        """Return all messages since last_id in a channel."""
        self.db.update_agent_seen(agent_name)
        header = self._header_for(agent_name, channel)
        messages = self.db.get_messages_since(last_id, channel=channel)
        return {
            "system_header": header,
            "channel": channel,
            "messages": messages,
        }

    def read_recent(self, agent_name: str, channel: str = "general", n: int = 10) -> dict:
        """Return last N messages in a channel with context for composing a response."""
        self.db.update_agent_seen(agent_name)
        header = self._header_for(agent_name, channel)
        messages = self.db.get_recent_messages(channel=channel, n=n)
        return {
            "system_header": header,
            "channel": channel,
            "messages": messages,
        }

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def send_message(self, agent_name: str, content: str, channel: str = "general") -> dict:
        """Append a message from a registered agent to a channel."""
        agent = self.db.get_agent(agent_name)
        role = agent["role"] if agent else None
        self.db.update_agent_seen(agent_name)
        return self.db.insert_message(sender=agent_name, content=content, role=role, channel=channel)

    def send_user_message(self, content: str, channel: str = "general") -> dict:
        """Append a message from the human user to a channel."""
        return self.db.insert_message(sender="user", content=content, role="user", channel=channel)

    # ------------------------------------------------------------------
    # Informational
    # ------------------------------------------------------------------

    def get_agents(self) -> list[dict]:
        return self.db.get_all_agents()

    def get_all_messages(self, channel: str = "general") -> list[dict]:
        return self.db.get_all_messages(channel=channel)

    def get_channels(self) -> list[dict]:
        return self.db.get_all_channels()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _header_for(self, agent_name: str, channel: str = "general") -> str:
        """Build the sticky header for a given agent, appending channel notes if any."""
        agent = self.db.get_agent(agent_name)
        if not agent:
            return ""
        roles = self._get_roles()
        role_def = next((r for r in roles if r["name"] == agent["role"]), None)
        if not role_def:
            return ""
        header = build_system_header(role_def, character_description=agent.get("character_description"))
        notes = self.db.get_notes(channel)
        if notes:
            notes_block = "\n".join(f"- {n['content']}" for n in notes)
            header += f"\n\n[CHANNEL NOTES — #{channel}]\n{notes_block}"
        return header

    @staticmethod
    def _format_messages(messages: list[dict]) -> str:
        if not messages:
            return "(no messages yet)"
        lines = []
        for m in messages:
            role_tag = f"[{m['role']}]" if m["role"] else ""
            lines.append(f"{m['timestamp']}  {role_tag} {m['sender']}: {m['content']}")
        return "\n".join(lines)
