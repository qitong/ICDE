# R2 Feature List & Test Traceability Matrix

- **PRD**: [docs/prd/r2-ci-and-foundation.md](../prd/r2-ci-and-foundation.md)
- **Tracking Issue**: `qitong/ICDE#2`

## Feature & Test Mapping

| ID | Feature / Requirement | Implementation Files | Whitebox Tests | Blackbox / Integration Tests |
|----|-----------------------|----------------------|----------------|------------------------------|
| **F-01** | **Kimi API Key Validation & Safe Diagnostics**: Minimal chat completion (`max_tokens=5`), exception propagation, safe key masking (`****` + last 4 chars only when length > 8, else `***`), and diagnostic metadata (`error_type`, `error_detail`, `base_url`, `model`) | `backend/app/services/llm_providers/kimi_provider.py`<br>`backend/app/routers/settings.py`<br>`frontend/src/types/index.ts`<br>`frontend/src/components/modals/LLMSettingsModal.tsx` | `test_foundation_fixes.py::TestKimiValidation::test_kimi_validate_api_key_success`<br>`test_foundation_fixes.py::TestKimiValidation::test_kimi_validate_api_key_raises_detailed_error`<br>`test_foundation_fixes.py::TestKimiValidation::test_mask_api_key_never_exposes_prefix` | `test_foundation_fixes.py::TestSettingsAPIBlackbox::test_validate_kimi_endpoint_valid_and_invalid`<br>`cd frontend && npm run lint && npm run build` |
| **F-02** | **Persistent `LLM_ENCRYPTION_KEY` Fallback**: Load or generate-and-save Fernet key at configurable `SECRET_KEY_FILE` (default `BASE_DIR / ".icde_secret_key"`, mode `0o600`) when `LLM_ENCRYPTION_KEY` env var is unset; ignore key file in git | `backend/app/config.py`<br>`backend/app/services/llm_service.py`<br>`.gitignore`<br>`backend/.gitignore` | `test_foundation_fixes.py::TestPersistentEncryptionKey::test_persisted_key_survives_service_recreation`<br>`test_foundation_fixes.py::TestPersistentEncryptionKey::test_env_encryption_key_takes_precedence` | `test_foundation_fixes.py::TestSettingsAPIBlackbox::test_encrypted_key_persists_across_requests` |
| **F-03** | **LLM Settings Non-Key Field Persistence**: Persist `model`, `enabled`, `api_base_url`, and `is_default` updates without requiring API key re-entry while preserving encrypted API keys | `frontend/src/components/modals/LLMSettingsModal.tsx`<br>`backend/app/services/llm_service.py`<br>`backend/app/routers/settings.py` | `test_foundation_fixes.py::TestLLMSettingPartialUpdate::test_update_setting_preserves_encrypted_key` | `test_foundation_fixes.py::TestSettingsAPIBlackbox::test_put_llm_settings_without_api_key_preserves_key` |
| **F-04** | **Script Structured Metadata Persistence**: Persist and update `parameters_schema`, `returns_schema`, `functions`, `use_cases`, and `example_calls` as UTF-8 JSON | `backend/app/routers/scripts.py` | `test_models.py::TestScriptModel` | `test_foundation_fixes.py::TestScriptMetadataPersistence::test_create_and_update_script_structured_metadata` |
| **F-05** | **Multi-Provider LLM Chat Baseline Suite**: Include provider connection, multi-turn context, provider switching, streaming, and conversation CRUD tests | `backend/tests/test_llm_chat.py`<br>`backend/pytest.ini`<br>`backend/tests/conftest.py` | `test_llm_chat.py::TestLLMConnection`<br>`test_llm_chat.py::TestMultiTurnConversation`<br>`test_llm_chat.py::TestProviderSwitching`<br>`test_llm_chat.py::TestConversationPersistence`<br>`test_llm_chat.py::TestStreamingChat`<br>`test_llm_chat.py::TestContextBuilding`<br>`test_llm_chat.py::TestLLMSettings` | Covered via `pytest` suite |
| **F-06** | **Strict Test Upload & Secret Isolation**: Monkeypatch `UPLOAD_DIR` and `SECRET_KEY_FILE` to `tmp_path` via `autouse` fixture; register all ORM models in `conftest.py` | `backend/tests/conftest.py`<br>`backend/pytest.ini` | `test_foundation_fixes.py::TestWorkspaceIsolation::test_uploads_and_secret_key_redirected_to_tmp_path` | `test_api.py` + CI post-test `git status --porcelain` & `backend/uploads` cleanliness check |
| **F-07** | **GitHub Actions CI Pipeline**: Automated `backend` (Python 3.11 + `pytest` + clean tree check) and `frontend` (Node 20 + `npm ci` + `npm run lint` + `npm run build`) workflows on `push` (`main`) and `pull_request` | `.github/workflows/ci.yml` | Local `pytest` & `git status --porcelain` verification | GitHub Actions `CI` workflow checks on PR against `main` |

## Checklist Status

- [x] `docs/prd/r2-ci-and-foundation.md` authored
- [x] `docs/features/r2-feature-list.md` authored
- [x] F-01: Kimi validation & safe error/key masking implemented
- [x] F-02: Persistent `.icde_secret_key` (`0o600`) & `.gitignore` entries implemented
- [x] F-03: `LLMSettingsModal.tsx` & `LLMService.update_setting` partial-save fix implemented
- [x] F-04: `routers/scripts.py` 5 structured metadata fields persisted on create/update
- [x] F-05: `test_llm_chat.py` integrated and passing
- [x] F-06: `pytest.ini` & `conftest.py` `autouse` isolation verified
- [x] F-07: `.github/workflows/ci.yml` configured for PR (`Closes #2`)
