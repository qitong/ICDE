"""Unified Agent Harness protocol and request/response contracts for ICDE."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.schemas.chat import MentionRef
from .events import ApprovalCheckpoint, HarnessEvent


class HarnessTurnRequest(BaseModel):
    """Request payload for running or streaming an agent harness turn."""

    model_config = ConfigDict(extra="ignore")

    message: str = Field(..., min_length=1)
    mentions: List[MentionRef] = Field(default_factory=list)
    conversation_id: Optional[str] = None
    provider: Optional[str] = None
    project_id: Optional[str] = None
    session_id: Optional[str] = None


class ApprovalDecisionRequest(BaseModel):
    """User / PI decision payload for resolving an `approval_required` checkpoint."""

    model_config = ConfigDict(extra="ignore")

    decision: Literal["approved", "rejected"]
    selected_option: Optional[str] = None
    comment: Optional[str] = None


class HarnessStatus(BaseModel):
    """Diagnostic and capability status of the active ICDE Agent Harness."""

    model_config = ConfigDict(extra="ignore")

    harness: str = "opencode"
    available: bool
    mode: Literal["remote_server", "local_binary", "mock_transport", "unavailable"]
    server_url: Optional[str] = None
    binary_path: Optional[str] = None
    mcp_server: str = "icde-mcp"
    mcp_tools: List[str] = Field(default_factory=list)
    raw_guard_enabled: bool = True
    protected_raw_datasets: int = 0
    configured_providers: List[str] = Field(default_factory=list)
    diagnostic: Optional[str] = None


class HarnessTurnResult(BaseModel):
    """Aggregated non-streaming result of an agent harness turn."""

    model_config = ConfigDict(extra="ignore")

    conversation_id: str
    message_id: str
    content: str
    provider: Optional[str] = None
    model: Optional[str] = None
    events: List[HarnessEvent] = Field(default_factory=list)
    pending_approvals: List[ApprovalCheckpoint] = Field(default_factory=list)


class ICDEHarnessAdapter(ABC):
    """
    Unified interface decoupling ICDE API routers from underlying agent runtimes
    (OpenCode Headless Server, future LangGraph SOP engines, or test doubles).
    """

    @abstractmethod
    def stream_turn(
        self,
        request: HarnessTurnRequest,
        db: Session,
    ) -> AsyncIterator[HarnessEvent]:
        """Stream standardized `HarnessEvent` chunks for a single user turn."""

    @abstractmethod
    async def run_turn(
        self,
        request: HarnessTurnRequest,
        db: Session,
    ) -> HarnessTurnResult:
        """Execute a turn and collect all events into a single `HarnessTurnResult`."""

    @abstractmethod
    async def resolve_approval(
        self,
        approval_id: str,
        decision: ApprovalDecisionRequest,
        db: Session,
    ) -> ApprovalCheckpoint:
        """Resolve a pending Human-in-the-loop approval checkpoint."""

    @abstractmethod
    async def health_status(self, db: Session) -> HarnessStatus:
        """Inspect active runtime connectivity, MCP tool registry, and guard state."""
