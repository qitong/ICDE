# PRD: R2 — GitHub Actions CI, Test Isolation & Persistence Foundation Fixes

- **Issue**: `qitong/ICDE#2` (`[R2][Foundation] GitHub Actions CI 搭建、测试隔离与存量持久化断点收敛`)
- **Status**: In Implementation
- **Scope**: Medium (Foundation / CI Gatekeeper)

## 1. Problem Statement

Codebase audit identified six foundational gaps impacting engineering reliability, security hygiene, and frontend-backend persistence loops:

1. **Kimi Validation & Unarchived LLM Tests**: Moonshot Kimi does not support OpenAI `models.list()` for key checks in all configurations, and validation failures previously swallowed diagnostic context. Meanwhile, multi-provider LLM chat tests (`backend/tests/test_llm_chat.py`) were not yet integrated into the repository baseline.
2. **Ephemeral `LLM_ENCRYPTION_KEY` Across Restarts**: When `LLM_ENCRYPTION_KEY` is unset in the environment, `backend/app/services/llm_service.py` generated a fresh in-memory Fernet key on every process import/restart, rendering previously persisted encrypted provider API keys undecryptable after backend restarts.
3. **Dropped Non-Key Edits in `LLMSettingsModal`**: `frontend/src/components/modals/LLMSettingsModal.tsx` (`handleSave`) only included providers whose `api_key` input was edited in the current modal session, silently dropping standalone changes to `model`, `enabled`, `api_base_url`, or `is_default`.
4. **Unpersisted Script Tool Metadata**: `backend/app/routers/scripts.py` (`create_script` and `update_script`) omitted the five structured tool-calling metadata fields (`parameters_schema`, `returns_schema`, `functions`, `use_cases`, `example_calls`) already defined in Pydantic schemas and SQLAlchemy ORM.
5. **Lack of Test Filesystem & Secret Isolation**: Running `pytest` wrote dataset UUID directories directly into `backend/uploads/` and lacked isolated secret key / SQLite paths, risking workspace pollution during local and CI test runs.
6. **Missing Automated CI Pipeline**: The repository had no GitHub Actions workflow enforcing backend test execution, workspace cleanliness, or frontend lint/typecheck/build gates on pushes and pull requests.

## 2. Scope & Engineering Objectives

### 2.1 LLM Key Validation & Safe Diagnostic Reporting
- Validate Kimi API keys via a minimal chat completion (`max_tokens=5`) in `KimiProvider.validate_api_key()`, re-raising underlying exceptions so the caller receives actionable failure details.
- Enhance `POST /api/settings/llm/{provider}/validate` and `LLMSettingsModal` to return and display `error_type`, `error_detail`, `base_url`, `model`, and a safely masked key indicator.

### 2.2 Persistent Local Fernet Encryption Key Fallback
- When `LLM_ENCRYPTION_KEY` is not set in environment variables, `LLMService` loads an existing Fernet key or generates and persists one at a configurable path defaulting to `BASE_DIR / ".icde_secret_key"` with strict `0o600` file permissions.
- Ignore `.icde_secret_key` (and `.pytest_cache/`) in `.gitignore` and `backend/.gitignore`.

### 2.3 Full Provider Configuration Persistence
- Update `LLMSettingsModal.tsx` (`handleSave`) and verify `LLMService.update_setting` so changes to `model`, `enabled`, `api_base_url`, and `is_default` are persisted even when `api_key` is untouched (`null`/omitted), preserving existing encrypted keys in the database.

### 2.4 Script Structured Metadata Round-Trip Persistence
- Serialize and persist `parameters_schema`, `returns_schema`, `functions`, `use_cases`, and `example_calls` as UTF-8 JSON (`ensure_ascii=False`) in both `POST /api/scripts` and `PUT /api/scripts/{script_id}`.

### 2.5 Strict Test Isolation (`pytest`)
- Configure `backend/pytest.ini` with `asyncio_mode = auto` and `asyncio_default_fixture_loop_scope = function`.
- Register all SQLAlchemy models in `backend/tests/conftest.py` and enforce an `autouse` fixture redirecting `UPLOAD_DIR` (`app.config` and `app.routers.datasets`) and `SECRET_KEY_FILE` (`app.config` and `app.services.llm_service`) into `tmp_path`, ensuring zero writes to `backend/uploads/` or `backend/.icde_secret_key`.

### 2.6 GitHub Actions CI Gate
- Add `.github/workflows/ci.yml` running on `push` to `main` and `pull_request` with two parallel jobs:
  - `backend`: Ubuntu latest, Python 3.11, install `backend/requirements.txt`, run `pytest`, and verify `git status --porcelain` is empty and no untracked artifacts exist in `backend/uploads`.
  - `frontend`: Ubuntu latest, Node 20, `npm ci`, `npm run lint`, and `npm run build`.

## 3. Security & Privacy Requirements

1. **Zero Patient Data Exposure**: Tests use 100% synthetic in-memory SQLite and temporary directories (`tmp_path`). No real clinical datasets or `.db`/`.sqlite` files are read or committed.
2. **Safe API Key Masking**: HTTP responses and server logs must never expose raw API keys or key prefixes (first 8 characters). Keys may only be masked as `****<last4>` when `len(key) > 8`, or `***` otherwise. If an upstream SDK exception string contains the raw API key, scrub it before returning or logging.
3. **Secret Hygiene**: `.icde_secret_key` must be created with owner-only `0o600` permissions and excluded from version control via `.gitignore` and `backend/.gitignore`.

## 4. Acceptance Criteria

- [x] **AC-1**: Recreating `LLMService` (simulating backend restart without `LLM_ENCRYPTION_KEY` env var) reuses `.icde_secret_key` (`0o600`), decrypts previously saved provider API keys, and passes provider validation.
- [x] **AC-2**: Updating `model`, `enabled`, `api_base_url`, or `is_default` via `LLMSettingsModal` / `PUT /api/settings/llm` without re-entering `api_key` persists all updated fields while keeping `api_key_set == true` and preserving the encrypted key.
- [x] **AC-3**: Creating (`POST /api/scripts`) and updating (`PUT /api/scripts/{id}`) scripts with `parameters_schema`, `returns_schema`, `functions`, `use_cases`, and `example_calls` round-trips all five fields accurately on subsequent `GET` queries.
- [x] **AC-4**: `KimiProvider.validate_api_key()` and `POST /api/settings/llm/kimi/validate` validate via minimal chat completion (`max_tokens=5`), surface `error_type` / `error_detail` / `base_url` / `model` on failure, and safely mask keys (`****<last4>` or `***`).
- [x] **AC-5**: Running the full `pytest` suite leaves zero untracked files or directories in `backend/uploads/` and `git status --porcelain` clean; frontend `npm run lint` and `npm run build` pass; GitHub Actions CI (`backend` + `frontend`) is green.
