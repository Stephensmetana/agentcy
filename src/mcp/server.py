"""
src/mcp/server.py — MCP bridge exposing the 4 chat tools to VS Code Copilot.

Tools:
    join_chat     — register agent, get role + system header
    read_all      — full history with sticky header
    read_latest   — latest message with sticky header
    send_message  — append a message

Run via stdio (standard MCP transport):
    python mcp_server.py [db_path] [roles_path]

VS Code Copilot .mcp.json config:
    {
      "servers": {
        "agentcy": {
          "type": "stdio",
          "command": "python",
          "args": ["<absolute-path>/src/mcp/server.py", "<absolute-path>/databases/agentcy.db", "<absolute-path>/roles.json"]
        }
      }
    }
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.api.chat import ChatRoom
from src.api.db import ChatDB


def build_server(db_path: str, roles_path: str) -> Server:
    """
    Construct and wire up the MCP Server.

    Separated from `run()` so unit tests can instantiate without running stdio.
    """
    db = ChatDB(db_path)
    room = ChatRoom(db, roles_path)
    server = Server("agentcy")

    # ------------------------------------------------------------------ tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="join_chat",
                description=(
                    "Join Agentcy. The server assigns you a role based on current "
                    "occupancy and returns a system header you MUST prepend to every prompt. "
                    "Call once at session start. Pass preferred_role to request a specific role. "
                    "Pass character_description to permanently embed a persona into every "
                    "subsequent read response — the server injects it into the sticky header "
                    "so you cannot forget it."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Your unique agent identifier (e.g. 'agent_1', 'copilot_dev')",
                        },
                        "preferred_role": {
                            "type": "string",
                            "description": "Optional. Requested role name. Granted if a slot is available.",
                        },
                        "character_description": {
                            "type": "string",
                            "description": (
                                "Optional. A persona prompt that will be injected into the "
                                "sticky system header on every read_all / read_latest call. "
                                "Use this to lock in a character you must play — e.g. "
                                "'You are Sherlock Holmes. Speak in deductive, precise language…'"
                            ),
                        },
                    },
                    "required": ["agent_name"],
                },
            ),
            Tool(
                name="read_all",
                description=(
                    "Read the entire chat history. Returns your sticky system header followed "
                    "by every message in order. Use before composing a full response."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Your agent identifier from join_chat",
                        }
                    },
                    "required": ["agent_name"],
                },
            ),
            Tool(
                name="read_latest",
                description=(
                    "Read only the most recent message plus your system header. "
                    "Use this for the quick check: 'is the last message mine?' before deciding "
                    "whether to respond. More efficient than read_all for polling."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Your agent identifier from join_chat",
                        }
                    },
                    "required": ["agent_name"],
                },
            ),
            Tool(
                name="send_message",
                description=(
                    "Append your message to the chat. Only call this when the latest message "
                    "is NOT from you. The server appends — you cannot edit previous messages."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Your agent identifier from join_chat",
                        },
                        "content": {
                            "type": "string",
                            "description": "Your message text",
                        },
                    },
                    "required": ["agent_name", "content"],
                },
            ),
        ]

    # --------------------------------------------------------------- handlers
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "join_chat":
            result = room.join(
                agent_name=arguments["agent_name"],
                preferred_role=arguments.get("preferred_role"),
                character_description=arguments.get("character_description"),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "read_all":
            text = room.read_all(agent_name=arguments["agent_name"])
            return [TextContent(type="text", text=text)]

        elif name == "read_latest":
            result = room.read_latest(agent_name=arguments["agent_name"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "send_message":
            result = room.send_message(
                agent_name=arguments["agent_name"],
                content=arguments["content"],
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    return server


async def run(db_path: str, roles_path: str) -> None:
    server = build_server(db_path, roles_path)
    async with stdio_server() as (read_stream, write_stream):
        init_opts = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_opts)


if __name__ == "__main__":
    _db = sys.argv[1] if len(sys.argv) > 1 else "databases/agentcy.db"
    _roles = sys.argv[2] if len(sys.argv) > 2 else "roles.json"
    asyncio.run(run(_db, _roles))
