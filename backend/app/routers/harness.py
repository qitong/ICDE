"""FastAPI endpoints for the ICDE Agent Harness (`/api/harness/*`)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.harness.approval_store import ApprovalStore
from app.harness.events import ApprovalCheckpoint, HarnessEvent
from app.harness.opencode_adapter import OpenCodeHarnessAdapter
from app.harness.protocol import (
    ApprovalDecisionRequest,
    HarnessStatus,
    HarnessTurnRequest,
    HarnessTurnResult,
    ICDEHarnessAdapter,
)
from app.mcp.icde_mcp_server import ICDEMCPServer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/harness", tags=["harness"])

_default_adapter = OpenCodeHarnessAdapter()


def get_harness_adapter() -> ICDEHarnessAdapter:
    """Dependency returning the active `ICDEHarnessAdapter` singleton."""
    return _default_adapter


@router.get("/status", response_model=HarnessStatus)
async def get_harness_status(
    db: Session = Depends(get_db),
    adapter: ICDEHarnessAdapter = Depends(get_harness_adapter),
) -> HarnessStatus:
    """Return active harness status, OpenCode server/binary health, MCP tools, and RAW guard state."""
    return await adapter.health_status(db)


@router.post("/stream")
async def stream_harness_turn(
    request: HarnessTurnRequest,
    db: Session = Depends(get_db),
    adapter: ICDEHarnessAdapter = Depends(get_harness_adapter),
) -> StreamingResponse:
    """Stream standardized `HarnessEvent` SSE chunks for an agent turn."""

    async def generate():
        try:
            async for event in adapter.stream_turn(request, db):
                yield event.to_sse()
        except Exception as exc:
            logger.error("Unhandled harness stream error: %s", exc)
            yield HarnessEvent.error_event(str(exc), code="STREAM_EXCEPTION").to_sse()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/turn", response_model=HarnessTurnResult)
async def run_harness_turn(
    request: HarnessTurnRequest,
    db: Session = Depends(get_db),
    adapter: ICDEHarnessAdapter = Depends(get_harness_adapter),
) -> HarnessTurnResult:
    """Run an agent turn synchronously and return all collected `HarnessEvent` items."""
    return await adapter.run_turn(request, db)


@router.get("/approvals/{approval_id}", response_model=ApprovalCheckpoint)
async def get_approval_checkpoint(
    approval_id: str,
    db: Session = Depends(get_db),
) -> ApprovalCheckpoint:
    """Retrieve a tracked clinical approval checkpoint by ID."""
    store = ApprovalStore(db)
    checkpoint = store.get(approval_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail=f"Approval checkpoint not found: {approval_id}")
    return checkpoint


@router.post("/approvals/{approval_id}", response_model=ApprovalCheckpoint)
async def resolve_approval_checkpoint(
    approval_id: str,
    decision: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    adapter: ICDEHarnessAdapter = Depends(get_harness_adapter),
) -> ApprovalCheckpoint:
    """Approve, reject, or select an option on a pending `approval_required` checkpoint."""
    try:
        return await adapter.resolve_approval(approval_id, decision, db)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/mcp")
async def handle_mcp_jsonrpc(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
) -> Optional[Dict[str, Any]]:
    """Expose `icde-mcp` over HTTP JSON-RPC 2.0 for remote OpenCode servers."""
    mcp_server = ICDEMCPServer.from_session(db)
    result = mcp_server.handle_rpc(payload)
    if result is None:
        return Response(status_code=204)  # type: ignore[return-value]
    return result
