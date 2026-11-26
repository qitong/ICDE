"""ICDE Unified Agent Harness package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .approval_store import ApprovalStore, HarnessApprovalRecord
    from .events import (
        ApprovalCheckpoint,
        ApprovalStatus,
        HarnessEvent,
        HarnessEventType,
        ToolCallStatus,
        WorkspaceEventName,
    )
    from .opencode_adapter import HttpOpenCodeTransport, OpenCodeHarnessAdapter, OpenCodeTransport
    from .opencode_config import OpenCodeConfigBuilder, OpenCodeRuntimeBundle, PROVIDER_SPECS
    from .protocol import (
        ApprovalDecisionRequest,
        HarnessStatus,
        HarnessTurnRequest,
        HarnessTurnResult,
        ICDEHarnessAdapter,
    )
    from .workspace_guard import (
        RawFileDigest,
        RawSnapshot,
        ReadOnlyDatasetViolationError,
        WorkspaceGuard,
    )

__all__ = [
    "ApprovalCheckpoint",
    "ApprovalDecisionRequest",
    "ApprovalStatus",
    "ApprovalStore",
    "HarnessApprovalRecord",
    "HarnessEvent",
    "HarnessEventType",
    "HarnessStatus",
    "HarnessTurnRequest",
    "HarnessTurnResult",
    "HttpOpenCodeTransport",
    "ICDEHarnessAdapter",
    "OpenCodeConfigBuilder",
    "OpenCodeHarnessAdapter",
    "OpenCodeRuntimeBundle",
    "OpenCodeTransport",
    "PROVIDER_SPECS",
    "RawFileDigest",
    "RawSnapshot",
    "ReadOnlyDatasetViolationError",
    "ToolCallStatus",
    "WorkspaceEventName",
    "WorkspaceGuard",
]

_LAZY_SUBMODULES = {
    "ApprovalStore": ".approval_store",
    "HarnessApprovalRecord": ".approval_store",
    "ApprovalCheckpoint": ".events",
    "ApprovalStatus": ".events",
    "HarnessEvent": ".events",
    "HarnessEventType": ".events",
    "ToolCallStatus": ".events",
    "WorkspaceEventName": ".events",
    "HttpOpenCodeTransport": ".opencode_adapter",
    "OpenCodeHarnessAdapter": ".opencode_adapter",
    "OpenCodeTransport": ".opencode_adapter",
    "OpenCodeConfigBuilder": ".opencode_config",
    "OpenCodeRuntimeBundle": ".opencode_config",
    "PROVIDER_SPECS": ".opencode_config",
    "ApprovalDecisionRequest": ".protocol",
    "HarnessStatus": ".protocol",
    "HarnessTurnRequest": ".protocol",
    "HarnessTurnResult": ".protocol",
    "ICDEHarnessAdapter": ".protocol",
    "RawFileDigest": ".workspace_guard",
    "RawSnapshot": ".workspace_guard",
    "ReadOnlyDatasetViolationError": ".workspace_guard",
    "WorkspaceGuard": ".workspace_guard",
}


def __getattr__(name: str) -> Any:
    submodule_name = _LAZY_SUBMODULES.get(name)
    if submodule_name is not None:
        from importlib import import_module

        module = import_module(submodule_name, __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
