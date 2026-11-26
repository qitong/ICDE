"""Local ICDE Model Context Protocol (`icde-mcp`) bridge."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .icde_mcp_server import ICDEMCPServer, MCP_PROTOCOL_VERSION
    from .tools import ICDEMCPTools, TOOL_DEFINITIONS

__all__ = [
    "ICDEMCPServer",
    "ICDEMCPTools",
    "MCP_PROTOCOL_VERSION",
    "TOOL_DEFINITIONS",
]


def __getattr__(name: str) -> Any:
    if name in ("ICDEMCPServer", "MCP_PROTOCOL_VERSION"):
        from . import icde_mcp_server

        return getattr(icde_mcp_server, name)
    if name in ("ICDEMCPTools", "TOOL_DEFINITIONS"):
        from . import tools

        return getattr(tools, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
