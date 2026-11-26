# PRD: R1 OpenCode SDK + Local `icde-mcp` Agent Harness Integration

- **Document ID**: `PRD-R1-HARNESS`
- **Related Issue**: `qitong/ICDE#1`
- **Related ADR**: [0001-agent-harness-opencode-sdk.md](../adr/0001-agent-harness-opencode-sdk.md)
- **Status**: Approved for Implementation

---

## 1. Product Overview & Objective

Clinical investigators using ICDE need an AI copilot that goes beyond static Q&A: when a researcher references `@ADSL` and asks to build a Full Analysis Set (FAS) or summarize baseline demographics, the assistant must inspect column metadata, propose or save reusable transformation scripts, pause for PI confirmation on clinical cohort rules, execute derivations safely, and update the workspace lineage graph in real time—without ever altering original uploaded (`RAW`) clinical trial files.

R1 establishes this foundational **Agent Harness** layer using **OpenCode Headless Server (`opencode serve`)**, a local **ICDE MCP Server (`icde-mcp`)**, a strict **`WorkspaceGuard`**, and structured SSE UI components in the React chat panel.

---

## 2. User Stories

1. **Multi-Model Clinical Copilot (`US-01`)**: As a researcher, I can configure OpenAI, Claude, Gemini, or Kimi in LLM Settings and run agentic data workflows with any enabled provider without exposing plaintext API keys in workspace files.
2. **Dataset Schema & Lineage Inspection (`US-02`)**: As a researcher referencing `@Study_ABC/ADSL`, I can ask the assistant to inspect columns, missingness, and lineage; I see a live `tool_call` status badge (`icde_inspect_dataset`) in the chat bubble as it runs.
3. **Human-in-the-Loop Clinical Approval (`US-03`)**: As a Principal Investigator (PI), before the agent finalizes cohort inclusion/exclusion criteria or statistical model choices, I receive an interactive **Clinical Confirmation Card** (`approval_required`) inside the chat thread where I can approve, reject, or choose a specific option.
4. **Traceable Script & Dataset Derivation (`US-04`)**: As a biostatistician, when the agent saves a script or derives `ADSL_FAS`, ICDE atomically registers the `DERIVED` dataset, file metadata, and lineage in SQLite and automatically refreshes the Sidebar and Metadata/Lineage view via `workspace_event`.
5. **Guaranteed `RAW` Data Integrity (`US-05`)**: As a clinical data manager, I am guaranteed that no agent tool call, path traversal, or script execution can overwrite, modify, or delete any `RAW` source dataset file.

---

## 3. Technical Specification

### 3.1 Unified Harness Protocol (`backend/app/harness/`)
- **`events.py`**: Pydantic models for `HarnessEvent` (`content`, `tool_call`, `approval_required`, `workspace_event`, `done`, `error`), `ToolCallStatus`, `ApprovalOption`, `ApprovalCheckpoint`, and SSE serialization (`to_sse()`).
- **`protocol.py`**: Abstract `ICDEHarnessAdapter` interface defining:
  - `stream_turn(request, db) -> AsyncIterator[HarnessEvent]`
  - `run_turn(request, db) -> HarnessTurnResult`
  - `resolve_approval(approval_id, decision, selected_option, comment, db) -> ApprovalCheckpoint`
  - `health_status(db) -> HarnessStatus`
- **`workspace_guard.py`**:
  - `WorkspaceGuard`: Canonical path resolution (`Path.resolve()`), symlink/path-traversal rejection, `assert_writable(target_path)` raising `ReadOnlyDatasetViolationError` on any `RAW` dataset path, POSIX `0o444` read-only locking (`lock_raw_dataset_files` / `unlock_for_deletion`), and cryptographic SHA-256 verification (`snapshot_raw_files` / `verify_raw_files_unchanged`).
- **`opencode_config.py`**:
  - `OpenCodeConfigBuilder`: Maps decrypted `LLMSetting` (`openai`, `claude`, `gemini`, `kimi`) into runtime environment variables + placeholder-only `opencode.json` and project-aware `AGENTS.md` (documenting `@` mentions, available datasets/scripts, `RAW` immutability rules, and `icde-mcp` tools).
- **`opencode_adapter.py`**:
  - `OpenCodeHarnessAdapter`: Connects to `OPENCODE_SERVER_URL` or manages an ephemeral `opencode serve` subprocess when the `opencode` binary is installed; translates `/session`, `/session/{id}/message` (or `/prompt_async`), `/event`, and `/session/{id}/permissions/{permId}` streams plus `icde-mcp` workspace events into `HarnessEvent` chunks while persisting `Conversation` and `ChatMessage` rows. Supports injected async transports for 100% deterministic offline testing.

### 3.2 Local ICDE MCP Bridge (`backend/app/mcp/`)
- **`tools.py`**: Domain tool implementations (`ICDEMCPTools`) backed by SQLAlchemy `Session`, `WorkspaceGuard`, `FileParser`, and `ScriptExecutor`:
  1. `icde_list_datasets(project_id?)`
  2. `icde_inspect_dataset(dataset_id)`
  3. `icde_list_scripts(query?)`
  4. `icde_save_script(name, display_name, description, code, language?, keywords?, input_requirements?, output_description?, script_id?)`
  5. `icde_derive_dataset(source_dataset_id, script_id, output_name)`
  6. `icde_request_approval(action, title, summary, options?)`
- **`icde_mcp_server.py`**: Standard MCP JSON-RPC 2.0 dispatcher (`initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`) supporting stdio transport (`python -m app.mcp.icde_mcp_server`) and HTTP RPC mounting.

### 3.3 Backend API Endpoints (`backend/app/routers/harness.py` & `chat.py`)
- `GET /api/harness/status`: Returns active harness adapter (`opencode`), server reachability / binary presence, registered `icde-mcp` tool names, and `RAW` guard status.
- `POST /api/harness/stream`: Streams `HarnessEvent` SSE frames for an agent turn.
- `POST /api/harness/approvals/{approval_id}`: Resolves a pending `approval_required` checkpoint (`approved` / `rejected` + selected option) and forwards permission responses to OpenCode when linked to a session permission prompt.
- `POST /api/harness/mcp`: JSON-RPC 2.0 HTTP endpoint exposing `icde-mcp` for remote/HTTP OpenCode server configurations.
- `POST /api/chat/stream`: Preserves backward compatibility while supporting optional `mode="harness"` routing to `OpenCodeHarnessAdapter`.

### 3.4 Frontend Integration (`frontend/src/`)
- Extend `StreamChunk` and `Message` types with `toolCalls?: ToolCallItem[]` and `approvals?: ApprovalItem[]`.
- Add modular chat UI components under `frontend/src/components/chat/`:
  - `ToolCallBadge.tsx`: Displays tool name, status spinner/checkmark/error icon, and summary/output preview.
  - `ApprovalCard.tsx`: Interactive PI confirmation card with option selector and Approve / Reject actions wired to `POST /api/harness/approvals/{approval_id}`.
- Update `MessageBubble.tsx`, `ChatPanel.tsx`, `api.ts`, and `AppContext.tsx`:
  - Handle `tool_call`, `approval_required`, and `workspace_event` SSE chunks;
  - Automatically invoke `loadDatasets()`, `loadScripts()`, `loadProjectTree()`, and `viewDatasetMetadata()` refresh when `workspace_event` arrives.

---

## 4. Non-Functional & Security Requirements

- **Zero Patient Data in Tests**: All unit and integration tests operate exclusively on synthetic in-memory/tempdir CSV data (`SUBJID = P001..P005`) and temporary SQLite databases.
- **Secret Hygiene**: Zero plaintext API keys written to disk or git-tracked files; `opencode.json` uses `{env:...}` variable references.
- **Parallelism Isolation**: Modularized under `backend/app/harness/`, `backend/app/mcp/`, `backend/app/routers/harness.py`, and `frontend/src/components/chat/` with minimal clean hooks in shared entrypoints.
