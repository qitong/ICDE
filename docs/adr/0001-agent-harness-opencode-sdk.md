# ADR 0001: Adopt OpenCode SDK + Local `icde-mcp` Bridge Behind Unified `ICDEHarnessAdapter`

- **Status**: Accepted
- **Date**: 2026-11-26
- **Issue**: `qitong/ICDE#1` (`[R1][Architecture] 底层 Agent Harness 选型（ADR）与统一执行底座接入`)
- **Deciders**: ICDE Core Architecture Team

---

## 1. Context & Problem Statement

ICDE (Integrated Clinical-Data Environment) enables clinical researchers and Principal Investigators (PIs) to transform raw clinical trial exports (CSV/Excel CRFs, CDISC SDTM/ADaM tables) into derived analysis cohorts (FAS, PPS, Safety sets), statistical summaries, and publication-ready outputs via natural language.

Prior to R1, `backend/app/services/llm_service.py` only supported stateless prompt stuffing: it concatenated project dataset names and `@`-mentioned column names into a static system prompt and streamed raw text chunks. It lacked core **Agent Harness** capabilities required for clinical data science:

1. **Autonomous Tool & Code Loop**: Unable to inspect dataset schemas on demand, author/patch Python or R transformation scripts, self-heal from syntax/key errors, or trigger reproducible derivations.
2. **Clinical Human-in-the-Loop (HITL) Checkpoints**: No structured mechanism to pause and request PI sign-off on high-stakes clinical decisions (e.g., inclusion/exclusion cohort criteria, primary endpoint statistical model selection).
3. **Strict `RAW` Data Immutability**: Clinical trial regulatory standards (ICH-GCP / 21 CFR Part 11 principles) require that uploaded `RAW` source datasets remain byte-for-byte immutable; transformations must exclusively produce versioned `DERIVED` datasets with full lineage in SQLite.
4. **Multi-LLM Neutrality**: ICDE already supports encrypted per-provider credentials in `llm_settings` across **OpenAI**, **Claude (Anthropic)**, **Gemini (Google)**, and **Kimi (Moonshot)**. The execution harness cannot lock ICDE into a single model vendor.
5. **Workspace & Canvas Synchronization**: Tool side effects (saving a reusable script, deriving a cohort dataset, updating lineage) must emit structured events over SSE so the React workspace refreshes automatically.

---

## 2. Decision Drivers

- **Multi-Provider Neutrality**: Native support for OpenAI, Anthropic Claude, Google Gemini, and OpenAI-compatible endpoints (Moonshot Kimi) using dynamic runtime credentials decrypted from SQLite `llm_settings`.
- **Coding & Self-Healing Ceiling**: First-class agentic file reading, patching, Python/R execution, traceback inspection, and context compaction for multi-step statistical pipelines.
- **Lineage & Metadata Integrity**: Every derived dataset and reusable script must be atomically registered in SQLite (`datasets`, `dataset_files`, `dataset_lineage`, `scripts`) rather than left as untracked ad-hoc files on disk.
- **Defense-in-Depth `RAW` Protection**: Guarantee zero mutation of `DatasetType.RAW` files across prompt, harness permission, MCP validation, POSIX file permission, and SHA-256 verification layers.
- **Testability in Headless CI**: Deterministic unit and end-to-end integration tests that run without external API keys or requiring a globally installed daemon in CI.

---

## 3. Considered Options & Comparison

| Dimension | **OpenCode SDK + `icde-mcp` (Selected)** | `LangGraph + Deep Agents` | `PydanticAI` | `claude-agent-sdk` |
|---|---|---|---|---|
| **Multi-LLM Neutrality** | **Excellent**: Native 75+ providers including OpenAI, Anthropic, Google Gemini, and OpenAI-compatible custom `baseURL` (Kimi/Moonshot). | **Good**: Via `langchain-*` chat model adapters. | **Good**: Built-in OpenAI, Anthropic, Gemini, OpenAI-compatible models. | **Disqualified**: Tightly coupled to Anthropic Claude models & runtime. |
| **Python / R Coding & Self-Healing Ceiling** | **Highest**: Production-hardened IDE agent loop (precise file read/edit/patch, shell execution, traceback self-repair, automatic long-context compaction). | **Moderate**: Requires custom-building code sandbox, diff/patch tools, and context compaction logic. | **Low–Moderate**: Lightweight structured tool calling; lacks built-in IDE coding loop or compaction. | **High**: Strong coding loop, but vendor-locked. |
| **SQLite Lineage Consistency** | **Strong via `icde-mcp`**: Domain mutations (`icde_save_script`, `icde_derive_dataset`) execute exclusively through ICDE's local MCP server backed by SQLAlchemy transactions. | **Strong**: In-process Python tool functions share SQLAlchemy session directly. | **Strong**: In-process Python tool functions share SQLAlchemy session. | **Moderate**: Requires external MCP bridge similar to OpenCode. |
| **Clinical HITL Checkpoints** | **Native + Domain-Aware**: Supports both OpenCode `/session/{id}/permissions/{permId}` (`ask` rules) and domain-level `icde_request_approval` MCP checkpoints. | **Native**: `interrupt()` + checkpointer state resumption. | **Manual**: Must build custom deferred tool-return state machine. | **Native**: Hook/permission callbacks, vendor-locked. |
| **`RAW` Read-Only Enforcement** | **Multi-Layer**: `opencode.json` path/tool `permission` rules + `WorkspaceGuard` path canonicalization + POSIX `0o444` + SHA-256 pre/post turn audit. | **App-Layer Only**: Relies on custom Python wrapper discipline unless OS sandbox added. | **App-Layer Only**: Relies on custom Python wrapper discipline. | **Config + Hooks**: Similar to OpenCode, vendor-locked. |
| **Operational Footprint** | Dual-process (`FastAPI` + headless `opencode serve`) abstracted behind `ICDEHarnessAdapter` with clean diagnostic/mock transport support. | Single Python process, higher custom agent-loop maintenance burden. | Single Python process, minimal coding-agent primitives. | Node/CLI subprocess + Anthropic API dependency. |

### Why Not the Alternatives?

- **`claude-agent-sdk`**: Violates ICDE's core multi-LLM requirement—clinical institutions frequently mandate specific approved endpoints (e.g., domestic Kimi/Moonshot, institutional OpenAI, or Gemini).
- **`PydanticAI`**: Ideal for typed extraction and single-turn tool invocation, but lacks built-in long-horizon coding loops, workspace patch tools, and context window compaction needed for M2/M3 multi-script biostatistics workflows.
- **`LangGraph + Deep Agents`**: Strong contender for deterministic state machines, and remains viable in the future behind `ICDEHarnessAdapter` for rigid SOP wizards. However, re-implementing a production-grade Python/R script authoring, patching, and self-healing runtime from scratch duplicates what OpenCode provides out of the box. Defining `ICDEHarnessAdapter` preserves future optionality while immediately unlocking OpenCode's coding ceiling.

---

## 4. Decision

We adopt **OpenCode Headless Server (`opencode serve`) + Async Python Client (`OpenCodeHarnessAdapter`) + Local ICDE MCP Bridge (`icde-mcp`)**, encapsulated behind a unified **`ICDEHarnessAdapter`** protocol.

### 4.1 System & Process Topology

```mermaid
sequenceDiagram
    participant UI as React Frontend (ChatPanel / Canvas)
    participant API as FastAPI (/api/harness & /api/chat)
    participant Guard as WorkspaceGuard + ConfigBuilder
    participant OC as OpenCode Headless Server (opencode serve)
    participant MCP as Local ICDE MCP Bridge (icde-mcp)
    participant DB as SQLite + Controlled Uploads

    UI->>API: POST /api/harness/stream (message, @mentions, provider)
    API->>Guard: Decrypt LLMSetting in-memory, snapshot RAW SHA-256, build ephemeral opencode.json & AGENTS.md
    API->>OC: Ensure session (POST /session) + subscribe SSE (GET /event) + prompt (POST /session/{id}/prompt_async)
    OC->>MCP: JSON-RPC tools/call (icde_inspect_dataset / icde_save_script / icde_derive_dataset / icde_request_approval)
    MCP->>Guard: Validate RAW immutability & canonical paths
    MCP->>DB: Atomic SQLAlchemy read/write (Dataset, DatasetFile, DatasetLineage, Script)
    MCP-->>OC: Structured tool output + workspace event metadata
    OC-->>API: OpenCode SSE parts (text, tool state, permission.asked)
    API-->>UI: Standardized HarnessEvent SSE (content, tool_call, workspace_event, approval_required, done)
    API->>Guard: Verify post-turn RAW SHA-256 unchanged
    UI->>API: Auto-refresh datasets/scripts/lineage on workspace_event; POST /api/harness/approvals/{id} on PI decision
```

### 4.2 Dynamic Multi-Provider Credential Injection

1. Credentials remain encrypted at rest in SQLite `llm_settings.api_key_encrypted` (Fernet).
2. At turn initialization, `OpenCodeConfigBuilder` decrypts only the active provider's key in memory and constructs an ephemeral runtime environment dictionary (`env`) passed to `opencode serve` / session transport:
   - **`openai`** → `provider: "openai"`, model `openai/<model>`, env `OPENAI_API_KEY` (+ optional `baseURL`).
   - **`claude` / `anthropic`** → `provider: "anthropic"`, model `anthropic/<model>`, env `ANTHROPIC_API_KEY` (+ optional `baseURL`).
   - **`gemini` / `google`** → `provider: "google"`, model `google/<model>`, env `GOOGLE_GENERATIVE_AI_API_KEY` & `GEMINI_API_KEY`.
   - **`kimi` / `moonshot`** → OpenAI-compatible provider `kimi` (`npm: "@ai-sdk/openai-compatible"`), `options.baseURL` defaulting to `https://api.moonshot.cn/v1` (or `LLMSetting.api_base_url`), env `MOONSHOT_API_KEY`.
3. Generated `opencode.json` files live exclusively in an ephemeral session directory (`tempfile` / runtime dir outside git) and reference `{env:VAR_NAME}` / `${VAR_NAME}` placeholders—**plaintext API keys are never written to `opencode.json`, `AGENTS.md`, logs, or the repository**.

### 4.3 Standardized SSE Event Contract (`HarnessEvent`)

All streaming responses from `/api/harness/stream` (and `/api/chat/stream` when `mode="harness"`) emit `data: <JSON>\n\n` frames conforming to `HarnessEvent`:

| `type` | Purpose | Key Payload Fields |
|---|---|---|
| `content` | Streaming assistant text delta (backward-compatible with legacy `StreamChunk`) | `content`, `delta`, `conversation_id`, `message_id` |
| `tool_call` | Live tool invocation lifecycle | `call_id`, `tool_name`, `status` (`started` \| `completed` \| `error`), `summary`, `arguments`, `output` |
| `approval_required` | Clinical HITL checkpoint requiring PI confirmation | `approval_id`, `action`, `title`, `summary`, `options`, `status` (`pending`) |
| `workspace_event` | Side-effect notification triggering frontend Canvas/Sidebar refresh | `event_name` (`dataset_derived` \| `script_saved` \| `lineage_updated` \| `canvas_updated`), `dataset_id`, `script_id`, `payload` |
| `done` | Turn completion marker | `conversation_id`, `message_id` |
| `error` | Recoverable/terminal diagnostic error | `error`, `code`, `conversation_id` |

### 4.4 Local `icde-mcp` Server Surface

`backend/app/mcp/` implements a spec-compliant MCP JSON-RPC 2.0 server (`initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`) runnable both over **stdio** (`python -m app.mcp.icde_mcp_server`) for `opencode serve` local MCP mounting, over **HTTP** (`POST /api/harness/mcp`), and via direct Python invocation:

- `icde_list_datasets(project_id?)`: Enumerates datasets, study/version hierarchy, `RAW`/`DERIVED` type, and row/column counts.
- `icde_inspect_dataset(dataset_id)`: Returns parsed column schemas (`name`, `data_type`, `non_null_count`, `unique_count`, `sample_values`) and upstream/downstream lineage without mutating data.
- `icde_list_scripts(query?)`: Searches reusable transformation/analysis scripts by name, description, or keywords.
- `icde_save_script(...)`: Creates or versions a Python/R script in `scripts` with syntax validation and emits `script_saved`.
- `icde_derive_dataset(source_dataset_id, script_id, output_name)`: Snapshots source `RAW` hashes via `WorkspaceGuard`, executes `ScriptExecutor`, atomically writes `Dataset` (`DERIVED`), `DatasetFile`, and `DatasetLineage` records in SQLite, increments `script.usage_count`, verifies `RAW` hashes are unchanged, and emits `dataset_derived` + `lineage_updated`.
- `icde_request_approval(action, title, summary, options)`: Registers a tracked clinical approval checkpoint and emits `approval_required`.

### 4.5 Security & `RAW` Dataset Immutability Boundaries

`WorkspaceGuard` (`backend/app/harness/workspace_guard.py`) enforces four independent layers around `DatasetType.RAW`:

1. **Canonical Path & Traversal Guard**: Resolves symlinks and `..` segments via `Path.resolve()`. Any attempted write, overwrite, move, or delete targeting a `RAW` dataset directory or file raises `ReadOnlyDatasetViolationError` before I/O occurs.
2. **OpenCode Permission Rules**: Ephemeral `opencode.json` configures `permission` rules denying `edit`/`write` on `RAW` dataset globs and gating shell mutations while allowing `icde-mcp` read/derivation tools.
3. **OS File & Directory Mode Lock (`0o444` / `0o555`)**: `lock_raw_dataset_files()` strips write bits (`0o444` on files, `0o555` on directories) on `RAW` datasets before agent turns and on upload; `unlock_for_deletion()` restores `0o755` / `0o644` exclusively for explicit user-initiated dataset deletion.
4. **Cryptographic Pre/Post Turn Audit**: `snapshot_raw_files()` records SHA-256 digests + byte sizes of all `RAW` files prior to an agent turn or derivation; `verify_raw_files_unchanged()` asserts zero byte drift afterward, raising `ReadOnlyDatasetViolationError` on any tampering or deletion.

---

## 5. Consequences

### Positive
- Immediately equips ICDE with an extensible, multi-LLM agent runtime capable of dataset inspection, reusable script authoring, safe dataset derivation, and PI approval workflows.
- Guarantees regulatory-grade `RAW` dataset immutability and 100% SQLite lineage consistency through `icde-mcp` and `WorkspaceGuard`.
- Decouples FastAPI/React from OpenCode internals via `ICDEHarnessAdapter` and dependency-injected HTTP/SSE transports, enabling fast, deterministic offline CI testing.

### Negative / Mitigations
- **Host Binary Availability**: Developer laptops or minimal CI containers may not have the `opencode` binary pre-installed. *Mitigation*: `OpenCodeHarnessAdapter` detects binary/server availability via `/api/harness/status`, supports attaching to an external `OPENCODE_SERVER_URL`, provides a clear structured diagnostic when absent, and supports full transport injection for deterministic testing.
