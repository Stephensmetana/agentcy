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

    db       — ChatDB instance (SQLite)
    roles    — list of role dicts loaded from roles.json
    """

    def __init__(self, db: ChatDB, roles_path: str):
        self.db = db
        self.roles = load_roles(roles_path)

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def join(self, agent_name: str, preferred_role: Optional[str] = None, character_description: Optional[str] = None) -> dict:
        """
        Register an agent, assign a role, post a join notice, return the
        sticky system header.

        Returns:
            {
                "agent_name": str,
                "role": str,
                "system_header": str,   ← inject this into every subsequent prompt
            }
        """
        active = self.db.get_all_agents()
        role = assign_role(self.roles, active, preferred=preferred_role)

        self.db.register_agent(agent_name, role["name"], character_description=character_description)
        self.db.insert_message(
            sender="system",
            content=f"{agent_name} joined as {role['name'].upper()}",
            role="system",
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
        """
        Return sticky system header + full chat history for a channel.

        Every agent read goes through here so the header is always present.
        """
        self.db.update_agent_seen(agent_name)
        header = self._header_for(agent_name)
        messages = self.db.get_all_messages(channel=channel)
        chat_block = self._format_messages(messages)
        return f"{header}\n[CHAT LOG — {channel} — {len(messages)} messages]\n\n{chat_block}"

    def read_latest(self, agent_name: str, channel: str = "general") -> dict:
        """
        Return sticky system header + the single most recent message in a channel.

        Use this for the quick 'should I respond?' check inside the agent loop.
        """
        self.db.update_agent_seen(agent_name)
        header = self._header_for(agent_name)
        latest = self.db.get_latest_message(channel=channel)
        return {
            "system_header": header,
            "channel": channel,
            "latest_message": latest,
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

    def _header_for(self, agent_name: str) -> str:
        """Build the sticky header for a given agent. Graceful if unknown."""
        agent = self.db.get_agent(agent_name)
        if not agent:
            return ""
        role_def = next((r for r in self.roles if r["name"] == agent["role"]), None)
        if not role_def:
            return ""
        return build_system_header(role_def, character_description=agent.get("character_description"))

    @staticmethod
    def _format_messages(messages: list[dict]) -> str:
        if not messages:
            return "(no messages yet)"
        lines = []
        for m in messages:
            role_tag = f"[{m['role']}]" if m["role"] else ""
            lines.append(f"{m['timestamp']}  {role_tag} {m['sender']}: {m['content']}")
        return "\n".join(lines)
