"""NetCore IT support ticket MCP server (FastMCP, streamable HTTP).

Tickets live in Postgres (schema `itsm`, the source of truth) and are mirrored one-way to Jira Cloud.
Run: `python -m netcore_mcp` (or `make mcp-run`) -> http://localhost:9090/mcp
"""

from pathlib import Path

__version__ = "0.10.0"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
