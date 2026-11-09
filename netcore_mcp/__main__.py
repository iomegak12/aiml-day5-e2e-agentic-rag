"""Run the ticket MCP server with uvicorn: python -m netcore_mcp  ->  http://0.0.0.0:9090/mcp"""

from __future__ import annotations

import logging

import uvicorn

from netcore_mcp.config import get_settings
from netcore_mcp.server import create_server


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # stateless streamable HTTP: every request is self-contained (the agent opens one short session per call)
    app = create_server().http_app(path="/mcp", transport="http", stateless_http=True)
    uvicorn.run(app, host=settings.mcp_host, port=settings.mcp_port, log_level=settings.log_level.lower(),
                access_log=False)


if __name__ == "__main__":
    main()
