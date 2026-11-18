"""Streamable HTTP transport, so remote MCP clients can use a hosted server.

Runs stateless with JSON responses: every request is independent, which lets the server sit
behind any load balancer and scale horizontally without sticky sessions.
"""

from starlette.requests import Request
from starlette.responses import JSONResponse

from brazil_data_mcp import __version__
from brazil_data_mcp.server import mcp


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "version": __version__})


def create_app(host: str = "0.0.0.0"):
    return mcp.streamable_http_app(stateless_http=True, json_response=True, host=host)
