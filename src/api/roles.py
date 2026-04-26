"""
roles.py — Role loading, assignment, and system header generation.

Roles are defined in the database (seeded from roles.json on first run).
This module picks the best role for a new agent and builds the sticky
system header that every agent receives on every read call.
"""

import json
from pathlib import Path
from typing import Optional


def load_roles(roles_path: str) -> list[dict]:
    """Load role definitions from a JSON file."""
    with open(roles_path, encoding="utf-8") as f:
        return json.load(f)


def assign_role(roles: list[dict], active_agents: list[dict], preferred: Optional[str] = None) -> dict:
    """
    Pick the best role for a joining agent.

    Strategy:
    1. If `preferred` is given, use it.
    2. Otherwise pick the role with the fewest current active agents.
    """
    counts: dict[str, int] = {}
    for agent in active_agents:
        counts[agent["role"]] = counts.get(agent["role"], 0) + 1

    if preferred:
        match = next((r for r in roles if r["name"] == preferred), None)
        if match:
            return match

    return min(roles, key=lambda r: counts.get(r["name"], 0))


def build_system_header(role: dict, character_description: Optional[str] = None) -> str:
    """
    Build the sticky system header block injected before every chat read.

    This is deliberately verbose so agents can't miss it even with long context.
    If character_description is provided it is injected as a mandatory persona block.
    """
    rules_block = "\n".join(f"  - {r}" for r in role["rules"])
    character_block = ""
    if character_description:
        character_block = f"""
╔══════════════════════════════════════════════════════════════╗
║  CHARACTER — YOU MUST EMBODY THIS PERSONA AT ALL TIMES      ║
╚══════════════════════════════════════════════════════════════╝

{character_description.strip()}

══════════════════════════════════════════════════════════════
"""
    return f"""╔══════════════════════════════════════════════════════════════╗
║  SYSTEM — YOUR ROLE (read this before every response)       ║
╚══════════════════════════════════════════════════════════════╝

ROLE:        {role['name'].upper()}
DESCRIPTION: {role['description']}

YOUR RULES:
{rules_block}

UNIVERSAL AGENT RULES (apply to every role):
  - Read the full chat before deciding to respond
  - Only respond if the LAST message is NOT from you
  - If the last message is yours → wait, do not respond yet
  - APPEND ONLY — never edit or reference editing previous messages
  - Do not repeat a point unless adding genuinely new information
  - Keep responses concise and clearly on-role
  - HUMAN PRIORITY — if the most recent message from sender='user' has not been
    explicitly addressed, address it BEFORE responding to other agents

══════════════════════════════════════════════════════════════
{character_block}"""
