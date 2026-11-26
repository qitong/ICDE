"""
Local ICDE MCP Server (`icde-mcp`) speaking JSON-RPC 2.0 over stdio and HTTP.

Supports:
- `initialize`
- `notifications/initialized` (and other JSON-RPC notifications)
- `ping`
- `tools/list`
- `tools/call`
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, IO, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .tools import EventSink, ICDEMCPTools, TOOL_DEFINITIONS


MCP_PROTOCOL_VERSION = "2024-11-05"


class ICDEMCPServer:
    """JSON-RPC 2.0 Model Context Protocol dispatcher for ICDE domain tools."""

    SERVER_NAME = "icde-mcp"
    SERVER_VERSION = "0.1.0"

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        upload_dir: Optional[Path] = None,
        event_sink: Optional[EventSink] = None,
        conversation_id: Optional[str] = None,
    ) -> None:
        self._session_factory = session_factory
        self._upload_dir = upload_dir
        self._event_sink = event_sink
        self._conversation_id = conversation_id
        self._initialized = False

    @classmethod
    def from_session(
        cls,
        db: Session,
        *,
        upload_dir: Optional[Path] = None,
        event_sink: Optional[EventSink] = None,
        conversation_id: Optional[str] = None,
    ) -> "ICDEMCPServer":
        """Create an MCP server bound to an existing SQLAlchemy `Session` (e.g. in tests/HTTP)."""
        server = cls(
            session_factory=lambda: db,
            upload_dir=upload_dir,
            event_sink=event_sink,
            conversation_id=conversation_id,
        )
        server._owns_session = False  # type: ignore[attr-defined]
        return server

    @staticmethod
    def list_tool_names() -> List[str]:
        """Return registered MCP tool names."""
        return [tool["name"] for tool in TOOL_DEFINITIONS]

    @staticmethod
    def list_tool_definitions() -> List[Dict[str, Any]]:
        """Return deep-copied MCP tool schema definitions."""
        return copy.deepcopy(TOOL_DEFINITIONS)

    def handle_rpc(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single JSON-RPC 2.0 message.
        Returns `None` for notifications (messages without an `id`).
        """
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id") if isinstance(request, dict) else None,
                "error": {"code": -32600, "message": "Invalid JSON-RPC 2.0 request"},
            }

        method = request.get("method")
        req_id = request.get("id")
        is_notification = "id" not in request or req_id is None
        params = request.get("params") or {}

        if not isinstance(method, str):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": "Missing method name"},
            }

        # Notifications produce no response frame
        if is_notification or method.startswith("notifications/"):
            if method == "notifications/initialized":
                self._initialized = True
            return None

        if method == "initialize":
            self._initialized = True
            requested_version = params.get("protocolVersion") or MCP_PROTOCOL_VERSION
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": requested_version,
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": self.SERVER_NAME,
                        "version": self.SERVER_VERSION,
                    },
                },
            }

        if method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {},
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": self.list_tool_definitions(),
                },
            }

        if method == "tools/call":
            if not isinstance(params, dict) or "name" not in params:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": "tools/call requires params.name"},
                }

            tool_name = params["name"]
            arguments = params.get("arguments") or {}
            if not isinstance(arguments, dict):
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": "params.arguments must be an object"},
                }

            owns_session = getattr(self, "_owns_session", True)
            db = self._session_factory()
            try:
                tools = ICDEMCPTools(
                    db,
                    upload_dir=self._upload_dir,
                    event_sink=self._event_sink,
                    conversation_id=self._conversation_id,
                )
                result_payload = tools.call_tool(tool_name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result_payload, ensure_ascii=False),
                            }
                        ],
                        "structuredContent": result_payload,
                        "isError": False,
                    },
                }
            except KeyError as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": str(exc)},
                }
            except Exception as exc:
                error_payload = {
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(error_payload, ensure_ascii=False),
                            }
                        ],
                        "structuredContent": error_payload,
                        "isError": True,
                    },
                }
            finally:
                if owns_session:
                    db.close()

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    def serve_stdio(
        self,
        stdin: Optional[IO[str]] = None,
        stdout: Optional[IO[str]] = None,
    ) -> None:
        """Run line-delimited MCP JSON-RPC 2.0 loop over stdio."""
        in_stream = stdin or sys.stdin
        out_stream = stdout or sys.stdout

        for raw_line in in_stream:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {exc}"},
                }
                out_stream.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
                out_stream.flush()
                continue

            response = self.handle_rpc(payload)
            if response is not None:
                out_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
                out_stream.flush()


def main() -> None:
    """CLI entrypoint for `python -m app.mcp.icde_mcp_server`."""
    from app.config import DATABASE_URL, UPLOAD_DIR
    from app.models.base import Base
    import app.models  # noqa: F401 - register ORM models

    db_url = os.environ.get("ICDE_DATABASE_URL") or os.environ.get("DATABASE_URL") or DATABASE_URL
    upload_path_str = os.environ.get("ICDE_UPLOAD_DIR")
    upload_dir = Path(upload_path_str) if upload_path_str else UPLOAD_DIR

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    server = ICDEMCPServer(session_factory=session_factory, upload_dir=upload_dir)
    server.serve_stdio()


if __name__ == "__main__":
    main()
