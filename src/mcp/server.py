"""
src/mcp/server.py — MCP bridge (thin HTTP client over the Agentcy REST API).

Every tool call is an HTTP request to the running REST server.
The REST server must be started before this MCP bridge runs.

Tools:
    join_chat        — register agent, get role + system header
    read_all         — full channel history with sticky header
    read_latest      — latest message with sticky header
    read_since       — all messages after a given id (efficient delta polling)
    read_recent      — last N messages with sticky header (context window)
    send_message     — append a message to a channel
    get_all_channels — list all channels
    get_channel_by_id— get a single channel by numeric id

MCP config (.mcp.json):
    {
      "servers": {
        "agentcy": {
          "type": "stdio",
          "command": "python",
          "args": ["<path>/src/mcp/server.py", "--base-url", "http://localhost:9001"]
        }
      }
    }

Legacy direct-DB mode still works for backward compatibility:
    python src/mcp/server.py databases/agentcy.db roles.json
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


# ---------------------------------------------------------------------------
# HTTP client helpers
# ---------------------------------------------------------------------------

def _get(base_url: str, path: str, params: Optional[dict] = None) -> dict | list:
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{base_url}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()


def _post(base_url: str, path: str, body: dict) -> dict:
    with httpx.Client(timeout=15) as client:
        resp = client.post(f"{base_url}{path}", json=body)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# MCP server factory
# ---------------------------------------------------------------------------

def build_server(base_url: str) -> Server:
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
                    "so you cannot forget it. Pass channel to specify which channel to join."
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
                            "description": "Optional. A persona prompt injected into the sticky header on every read.",
                        },
                        "channel": {
                            "type": "string",
                            "description": "Channel to join. Defaults to 'general'. Use get_all_channels to list available channels.",
                        },
                    },
                    "required": ["agent_name"],
                },
            ),
            Tool(
                name="read_all",
                description=(
                    "Read the entire chat history for a channel. Returns your sticky system "
                    "header followed by every message in order. Use before composing a full response."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_name": {"type": "string", "description": "Your agent identifier from join_chat"},
                        "channel": {"type": "string", "description": "Channel to read. Defaults to 'general'."},
                    },
                    "required": ["agent_name"],
                },
            ),
            Tool(
                name="read_latest",
                description=(
                    "Read only the most recent message plus your system header for a channel. "
                    "Use for the quick 'is the last message mine?' check before deciding to respond."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_name": {"type": "string"},
                        "channel": {"type": "string", "description": "Channel to read. Defaults to 'general'."},
                    },
                    "required": ["agent_name"],
                },
            ),
            Tool(
                name="read_since",
                description=(
                    "Return all messages after a given message id in a channel. "
                    "More efficient than read_all for polling — store your last_id and only "
                    "fetch the delta each loop."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_name": {"type": "string"},
                        "last_id": {"type": "integer", "description": "Return messages with id > this value"},
                        "channel": {"type": "string", "description": "Channel to read. Defaults to 'general'."},
                    },
                    "required": ["agent_name", "last_id"],
                },
            ),
            Tool(
                name="read_recent",
                description=(
                    "Return the last N messages in a channel with your system header. "
                    "Use this to build context before composing a response. "
                    "Recommended flow: read_latest → decide to respond → read_recent → compose."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_name": {"type": "string"},
                        "channel": {"type": "string", "description": "Channel to read. Defaults to 'general'."},
                        "n": {"type": "integer", "description": "Number of recent messages to return. Defaults to 10."},
                    },
                    "required": ["agent_name"],
                },
            ),
            Tool(
                name="send_message",
                description=(
                    "Append your message to a channel. Only call this when the latest message "
                    "is NOT from you. The server appends — you cannot edit previous messages."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_name": {"type": "string"},
                        "content": {"type": "string", "description": "Your message text"},
                        "channel": {"type": "string", "description": "Channel to post in. Defaults to 'general'."},
                    },
                    "required": ["agent_name", "content"],
                },
            ),
            Tool(
                name="get_all_channels",
                description="Return the list of all channels. Use this to discover available channels and their ids.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="get_channel_by_id",
                description="Return details for a specific channel by its numeric id.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {"type": "integer", "description": "The numeric channel id"},
                    },
                    "required": ["channel_id"],
                },
            ),
        ]

    # --------------------------------------------------------------- handlers

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name == "join_chat":
                result = _post(base_url, "/api/agent/join", {
                    "agent_name": arguments["agent_name"],
                    "preferred_role": arguments.get("preferred_role"),
                    "character_description": arguments.get("character_description"),
                    "channel": arguments.get("channel", "general"),
                })
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "read_all":
                result = _get(base_url, "/api/agent/read_all", {
                    "agent_name": arguments["agent_name"],
                    "channel": arguments.get("channel", "general"),
                })
                return [TextContent(type="text", text=result.get("text", ""))]

            elif name == "read_latest":
                result = _get(base_url, "/api/agent/read_latest", {
                    "agent_name": arguments["agent_name"],
                    "channel": arguments.get("channel", "general"),
                })
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "read_since":
                result = _get(base_url, "/api/agent/read_since", {
                    "agent_name": arguments["agent_name"],
                    "last_id": arguments["last_id"],
                    "channel": arguments.get("channel", "general"),
                })
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "read_recent":
                result = _get(base_url, "/api/agent/read_recent", {
                    "agent_name": arguments["agent_name"],
                    "channel": arguments.get("channel", "general"),
                    "n": arguments.get("n", 10),
                })
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "send_message":
                result = _post(base_url, "/api/messages", {
                    "sender": arguments["agent_name"],
                    "content": arguments["content"],
                    "channel": arguments.get("channel", "general"),
                })
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "get_all_channels":
                result = _get(base_url, "/api/channels")
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "get_channel_by_id":
                result = _get(base_url, f"/api/channels/{arguments['channel_id']}")
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except httpx.HTTPStatusError as e:
            return [TextContent(type="text", text=f"API error: {e.response.status_code} — {e.response.text}")]
        except httpx.ConnectError:
            return [TextContent(type="text", text=f"Cannot connect to Agentcy server at {base_url}. Make sure it is running: python main.py ui")]

    return server


async def run(base_url: str) -> None:
    server = build_server(base_url)
    async with stdio_server() as (read_stream, write_stream):
        init_opts = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_opts)


if __name__ == "__main__":
    # Support two argument styles:
    #   python src/mcp/server.py --base-url http://localhost:9001
    #   python src/mcp/server.py [db_path] [roles_path]  (legacy — auto-detects)
    args = sys.argv[1:]
    if args and args[0] == "--base-url":
        _base_url = args[1] if len(args) > 1 else "http://localhost:9001"
    elif args and (args[0].startswith("http://") or args[0].startswith("https://")):
        _base_url = args[0]
    else:
        # Legacy: db_path was first arg; ignore it and use default base_url
        _base_url = "http://localhost:9001"

    asyncio.run(run(_base_url))
