#!/usr/bin/env python3
"""
export_chat.py — Export the full chat log from Agentcy as Markdown.

Usage:
    python export_chat.py [db_path] [output_path]

Defaults:
    db_path     → databases/agentcy.db
    output_path → chat_export.md
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

from src.api.db import ChatDB


DEFAULT_DB     = "databases/agentcy.db"
DEFAULT_OUTPUT = "chat_export.md"


def format_timestamp(ts: str) -> str:
    """Convert ISO timestamp to a readable UTC string."""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except ValueError:
        return ts


def messages_to_markdown(messages: list[dict], db_path: str) -> str:
    lines: list[str] = []

    lines.append("# Agentcy — Full Chat Log")
    lines.append("")
    lines.append(f"**Source:** `{db_path}`  ")
    lines.append(f"**Exported:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ")
    lines.append(f"**Messages:** {len(messages)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for msg in messages:
        sender = msg.get("sender", "unknown")
        role   = msg.get("role") or ""
        ts     = format_timestamp(msg.get("timestamp", ""))
        content = msg.get("content", "")

        # Header line: sender (role) — timestamp
        if role and role != sender:
            header = f"### {sender} *({role})*"
        else:
            header = f"### {sender}"

        lines.append(header)
        lines.append(f"*{ts}*")
        lines.append("")
        lines.append(content)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    db_path     = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    output_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT

    db_file = Path(db_path)
    if not db_file.exists():
        print(f"Error: database file not found: {db_path}")
        sys.exit(1)

    db = ChatDB(db_path)
    messages = db.get_all_messages()

    if not messages:
        print("No messages found in the database.")
        sys.exit(0)

    markdown = messages_to_markdown(messages, db_path)

    out_file = Path(output_path)
    out_file.write_text(markdown, encoding="utf-8")

    print(f"Exported {len(messages)} messages → {out_file}")


if __name__ == "__main__":
    main()
