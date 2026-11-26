# R1 Feature List & Test Traceability Matrix

- **Milestone**: R1 — OpenCode SDK + Local `icde-mcp` Agent Harness Foundation
- **Issue**: `qitong/ICDE#1`
- **ADR**: [docs/adr/0001-agent-harness-opencode-sdk.md](../adr/0001-agent-harness-opencode-sdk.md)
- **PRD**: [docs/prd/r1-opencode-harness.md](../prd/r1-opencode-harness.md)

---

## Feature-to-Test Traceability Checklist

| Feature ID | Category | Feature Description | Implementation Path(s) | Automated Verification | Status |
|---|---|---|---|---|---|
| `F-R1-01` | Architecture & Docs | ADR, PRD, and Feature Traceability documentation | `docs/adr/0001-agent-harness-opencode-sdk.md`, `docs/prd/r1-opencode-harness.md`, `docs/features/r1-feature-list.md` | Document review & CI check | Completed |
| `F-R1-02` | Harness Protocol | Standardized `HarnessEvent` models (`content`, `tool_call`, `approval_required`, `workspace_event`, `done`, `error`) & `ICDEHarnessAdapter` interface | `backend/app/harness/events.py`, `backend/app/harness/protocol.py` | `backend/tests/test_opencode_harness.py` | Completed |
| `F-R1-03` | Security Guard | `WorkspaceGuard` canonical path resolution, `../` traversal & symlink rejection on `DatasetType.RAW` | `backend/app/harness/workspace_guard.py` | `backend/tests/test_workspace_guard.py::TestWorkspaceGuardPathProtection` | Completed |
| `F-R1-04` | Security Guard | Cryptographic SHA-256 `snapshot_raw_files` / `verify_raw_files_unchanged` pre/post-turn audit & POSIX `0o444` lock helpers | `backend/app/harness/workspace_guard.py` | `backend/tests/test_workspace_guard.py::TestWorkspaceGuardIntegrityAndPermissions` | Completed |
| `F-R1-05` | Multi-LLM Config | `OpenCodeConfigBuilder` mapping OpenAI, Claude, Gemini, and Kimi (`api_base_url`) via runtime env vars without plaintext key leakage + `AGENTS.md` | `backend/app/harness/opencode_config.py` | `backend/tests/test_workspace_guard.py::TestOpenCodeConfigBuilder` | Completed |
| `F-R1-06` | MCP Bridge | `icde_list_datasets` & `icde_inspect_dataset` returning schema & lineage without mutating source files | `backend/app/mcp/tools.py` | `backend/tests/test_icde_mcp.py::TestICDEMCPToolsDirect::test_list_and_inspect_dataset_preserve_raw_hash` | Completed |
| `F-R1-07` | MCP Bridge | `icde_list_scripts` & `icde_save_script` creating/updating validated scripts in SQLite and emitting `script_saved` | `backend/app/mcp/tools.py` | `backend/tests/test_icde_mcp.py::TestICDEMCPToolsDirect::test_save_and_list_scripts_emit_workspace_event_and_validate_syntax` | Completed |
| `F-R1-08` | MCP Bridge | `icde_derive_dataset` enforcing `WorkspaceGuard` SHA-256 check, atomic `Dataset` + `DatasetFile` + `DatasetLineage` persistence, and `dataset_derived` + `lineage_updated` events | `backend/app/mcp/tools.py` | `backend/tests/test_icde_mcp.py::TestICDEMCPToolsDirect::test_derive_dataset_atomic_metadata_lineage_and_raw_immutability` | Completed |
| `F-R1-09` | MCP Bridge | `icde_request_approval` checkpoint creation & full JSON-RPC 2.0 (`initialize`, `tools/list`, `tools/call`) stdio/HTTP server | `backend/app/mcp/tools.py`, `backend/app/mcp/icde_mcp_server.py` | `backend/tests/test_icde_mcp.py::TestICDEMCPJsonRpcServer` | Completed |
| `F-R1-10` | OpenCode Adapter | `OpenCodeHarnessAdapter` headless server client (`/session`, `/event`, `/message`, `/permissions`), binary/URL health diagnostics, conversation persistence, and mockable transport | `backend/app/harness/opencode_adapter.py` | `backend/tests/test_opencode_harness.py::TestOpenCodeAdapterMultiProvider` | Completed |
| `F-R1-11` | FastAPI Endpoints | `GET /api/harness/status`, `POST /api/harness/stream`, `POST /api/harness/approvals/{id}`, `POST /api/harness/mcp`, and `/api/chat/stream` `mode="harness"` hook | `backend/app/routers/harness.py`, `backend/app/routers/chat.py`, `backend/app/main.py` | `backend/tests/test_opencode_harness.py::TestHarnessFastAPIEndToEnd` | Completed |
| `F-R1-12` | Frontend & CI | Structured `tool_call` badges, interactive `approval_required` cards, automatic `workspace_event` dataset/script/lineage refresh, and GitHub Actions CI | `frontend/src/components/chat/ToolCallBadge.tsx`, `ApprovalCard.tsx`, `MessageBubble.tsx`, `AppContext.tsx`, `.github/workflows/ci.yml` | `npm run lint`, `npm run build`, `.github/workflows/ci.yml` | Completed |
