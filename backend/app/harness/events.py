"""Standardized SSE event models and approval checkpoints for the ICDE Agent Harness."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


HarnessEventType = Literal[
    "content",
    "text_delta",
    "tool_call",
    "approval_required",
    "workspace_event",
    "done",
    "error",
]

ToolCallStatus = Literal["started", "completed", "error"]
ApprovalStatus = Literal["pending", "approved", "rejected"]
WorkspaceEventName = Literal[
    "dataset_derived",
    "script_saved",
    "lineage_updated",
    "canvas_updated",
]


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class ApprovalCheckpoint(BaseModel):
    """Tracked Human-in-the-loop clinical approval checkpoint."""

    model_config = ConfigDict(extra="ignore")

    approval_id: str = Field(default_factory=lambda: f"appr_{uuid.uuid4().hex[:12]}")
    action: str
    title: str
    summary: str
    options: List[str] = Field(default_factory=lambda: ["Approve", "Reject"])
    status: ApprovalStatus = "pending"
    selected_option: Optional[str] = None
    comment: Optional[str] = None
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    permission_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)
    resolved_at: Optional[str] = None


class HarnessEvent(BaseModel):
    """
    Unified SSE event payload emitted by any ICDEHarnessAdapter implementation.

    Supports backward-compatible `content` text chunks alongside structured
    `tool_call`, `approval_required`, and `workspace_event` frames.
    """

    model_config = ConfigDict(extra="ignore")

    type: HarnessEventType
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None

    # Streaming text fields (content / text_delta)
    content: Optional[str] = None
    delta: Optional[str] = None

    # Tool execution lifecycle (tool_call)
    call_id: Optional[str] = None
    tool_name: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    output: Optional[Any] = None
    duration_ms: Optional[int] = None

    # Human-in-the-loop clinical checkpoint (approval_required)
    approval_id: Optional[str] = None
    action: Optional[str] = None
    title: Optional[str] = None
    options: Optional[List[str]] = None

    # Workspace synchronization side-effects (workspace_event)
    event_name: Optional[WorkspaceEventName] = None
    dataset_id: Optional[str] = None
    script_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

    # Error diagnostics (error)
    error: Optional[str] = None
    code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event into a compact JSON-ready dictionary."""
        return self.model_dump(exclude_none=True)

    def to_sse(self) -> str:
        """Format event as an SSE `data:` frame."""
        return f"data: {json.dumps(self.to_dict(), ensure_ascii=False)}\n\n"

    @classmethod
    def content_chunk(
        cls,
        text: str,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> "HarnessEvent":
        """Create a backward-compatible streaming assistant text chunk."""
        return cls(
            type="content",
            content=text,
            delta=text,
            conversation_id=conversation_id,
            message_id=message_id,
        )

    @classmethod
    def text_delta_chunk(
        cls,
        delta: str,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> "HarnessEvent":
        """Create an explicit `text_delta` event while preserving `content` field."""
        return cls(
            type="text_delta",
            content=delta,
            delta=delta,
            conversation_id=conversation_id,
            message_id=message_id,
        )

    @classmethod
    def tool_call_event(
        cls,
        *,
        call_id: str,
        tool_name: str,
        status: ToolCallStatus,
        summary: str,
        arguments: Optional[Dict[str, Any]] = None,
        output: Optional[Any] = None,
        duration_ms: Optional[int] = None,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> "HarnessEvent":
        """Create a `tool_call` lifecycle event."""
        return cls(
            type="tool_call",
            call_id=call_id,
            tool_name=tool_name,
            status=status,
            summary=summary,
            arguments=arguments,
            output=output,
            duration_ms=duration_ms,
            conversation_id=conversation_id,
            message_id=message_id,
        )

    @classmethod
    def approval_required_event(
        cls,
        checkpoint: ApprovalCheckpoint,
        *,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> "HarnessEvent":
        """Create an `approval_required` checkpoint event."""
        return cls(
            type="approval_required",
            approval_id=checkpoint.approval_id,
            action=checkpoint.action,
            title=checkpoint.title,
            summary=checkpoint.summary,
            options=list(checkpoint.options),
            status=checkpoint.status,
            conversation_id=conversation_id or checkpoint.conversation_id,
            message_id=message_id,
        )

    @classmethod
    def workspace_event_chunk(
        cls,
        *,
        event_name: WorkspaceEventName,
        dataset_id: Optional[str] = None,
        script_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> "HarnessEvent":
        """Create a `workspace_event` notification for frontend refresh."""
        return cls(
            type="workspace_event",
            event_name=event_name,
            dataset_id=dataset_id,
            script_id=script_id,
            payload=payload,
            conversation_id=conversation_id,
            message_id=message_id,
        )

    @classmethod
    def done_event(
        cls,
        *,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> "HarnessEvent":
        """Create a stream completion event."""
        return cls(
            type="done",
            conversation_id=conversation_id,
            message_id=message_id,
        )

    @classmethod
    def error_event(
        cls,
        error: str,
        *,
        code: Optional[str] = None,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> "HarnessEvent":
        """Create a structured error event."""
        return cls(
            type="error",
            error=error,
            code=code,
            conversation_id=conversation_id,
            message_id=message_id,
        )
