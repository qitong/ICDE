"""SQLite-backed store for Human-in-the-loop clinical `ApprovalCheckpoint` records."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Column, String, Text
from sqlalchemy.orm import Session

from app.models.base import Base
from .events import ApprovalCheckpoint, ApprovalStatus, utc_now_iso


class HarnessApprovalRecord(Base):
    """Persisted approval checkpoint row shared across FastAPI and `icde-mcp`."""

    __tablename__ = "harness_approvals"

    approval_id = Column(String(64), primary_key=True)
    action = Column(String(120), nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    selected_option = Column(String(255), nullable=True)
    comment = Column(Text, nullable=True)
    conversation_id = Column(String(36), nullable=True)
    session_id = Column(String(128), nullable=True)
    permission_id = Column(String(128), nullable=True)
    created_at = Column(String(64), nullable=False)
    resolved_at = Column(String(64), nullable=True)


class ApprovalStore:
    """CRUD helper for `ApprovalCheckpoint` records with automatic table creation."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self._ensure_table()

    def _ensure_table(self) -> None:
        bind = self.db.get_bind()
        HarnessApprovalRecord.__table__.create(bind=bind, checkfirst=True)

    @staticmethod
    def _to_checkpoint(row: HarnessApprovalRecord) -> ApprovalCheckpoint:
        try:
            options = json.loads(row.options_json) if row.options_json else ["Approve", "Reject"]
        except json.JSONDecodeError:
            options = ["Approve", "Reject"]

        status_val: ApprovalStatus = "pending"
        if row.status in ("pending", "approved", "rejected"):
            status_val = row.status  # type: ignore[assignment]

        return ApprovalCheckpoint(
            approval_id=row.approval_id,
            action=row.action,
            title=row.title,
            summary=row.summary,
            options=options,
            status=status_val,
            selected_option=row.selected_option,
            comment=row.comment,
            conversation_id=row.conversation_id,
            session_id=row.session_id,
            permission_id=row.permission_id,
            created_at=row.created_at,
            resolved_at=row.resolved_at,
        )

    def create(
        self,
        *,
        action: str,
        title: str,
        summary: str,
        options: Optional[List[str]] = None,
        approval_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        permission_id: Optional[str] = None,
    ) -> ApprovalCheckpoint:
        """Persist a new `pending` approval checkpoint."""
        normalized_options = [str(opt) for opt in (options or ["Approve", "Reject"]) if str(opt).strip()]
        if not normalized_options:
            normalized_options = ["Approve", "Reject"]

        created_at = utc_now_iso()
        record = HarnessApprovalRecord(
            approval_id=approval_id or f"appr_{uuid.uuid4().hex[:12]}",
            action=action,
            title=title,
            summary=summary,
            options_json=json.dumps(normalized_options, ensure_ascii=False),
            status="pending",
            conversation_id=conversation_id,
            session_id=session_id,
            permission_id=permission_id,
            created_at=created_at,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return self._to_checkpoint(record)

    def get(self, approval_id: str) -> Optional[ApprovalCheckpoint]:
        """Fetch an approval checkpoint by ID."""
        row = (
            self.db.query(HarnessApprovalRecord)
            .filter(HarnessApprovalRecord.approval_id == approval_id)
            .first()
        )
        return self._to_checkpoint(row) if row else None

    def resolve(
        self,
        approval_id: str,
        *,
        decision: ApprovalStatus,
        selected_option: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> ApprovalCheckpoint:
        """Resolve an existing checkpoint as `approved` or `rejected`."""
        row = (
            self.db.query(HarnessApprovalRecord)
            .filter(HarnessApprovalRecord.approval_id == approval_id)
            .first()
        )
        if not row:
            raise KeyError(f"Approval checkpoint not found: {approval_id}")

        row.status = decision
        if selected_option is not None:
            row.selected_option = selected_option
        elif row.selected_option is None:
            row.selected_option = "Approve" if decision == "approved" else "Reject"
        if comment is not None:
            row.comment = comment
        row.resolved_at = datetime.now(timezone.utc).isoformat()

        self.db.commit()
        self.db.refresh(row)
        return self._to_checkpoint(row)
