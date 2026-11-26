"""
Whitebox unit tests and blackbox FastAPI TestClient tests for R2 foundation fixes (Issue #2):
1. Persistent Fernet encryption key file (.icde_secret_key, mode 0o600) across LLMService recreations
2. Partial LLM settings updates (model, enabled, api_base_url, is_default) preserving encrypted API keys
3. Script structured metadata (parameters_schema, returns_schema, functions, use_cases, example_calls) persistence
4. KimiProvider minimal chat validation, detailed error propagation, and safe API key masking
5. Strict test isolation ensuring zero writes to backend/uploads/ or backend/.icde_secret_key
"""

import io
import os
import stat
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.config import BASE_DIR
from app.database import get_db
from app.main import app
from app.routers.settings import mask_api_key
from app.services.llm_providers.kimi_provider import KIMI_API_BASE, KimiProvider
from app.services.llm_service import LLMService


@pytest.fixture
def client(test_db):
    """FastAPI TestClient wired to the isolated in-memory test database."""
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ============== Whitebox Unit Tests ==============

class TestPersistentEncryptionKey:
    """Whitebox tests for persistent Fernet key fallback."""

    def test_persisted_key_survives_service_recreation(
        self, test_db, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Encrypted API keys survive recreating LLMService instances via .icde_secret_key."""
        monkeypatch.delenv("LLM_ENCRYPTION_KEY", raising=False)
        key_file = tmp_path / "custom_secret" / ".icde_secret_key"
        assert not key_file.exists()

        # First service instance generates and saves the persistent key file with 0o600 permissions
        service_1 = LLMService(test_db, secret_key_file=key_file)
        assert key_file.exists()
        file_mode = stat.S_IMODE(key_file.stat().st_mode)
        assert file_mode == 0o600

        raw_key = "sk-kimi-synthetic-persistence-check-4321"
        service_1.update_setting(
            provider="kimi",
            api_key=raw_key,
            model="moonshot-v1-128k",
            enabled=True,
        )

        # Second service instance simulates a backend process restart reading the persisted key file
        service_2 = LLMService(test_db, secret_key_file=key_file)
        kimi_provider = service_2.get_provider("kimi")
        assert kimi_provider.api_key == raw_key
        assert kimi_provider.model == "moonshot-v1-128k"

    def test_env_encryption_key_takes_precedence(
        self, test_db, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Explicit LLM_ENCRYPTION_KEY env var takes precedence without writing key file."""
        explicit_key = Fernet.generate_key().decode()
        monkeypatch.setenv("LLM_ENCRYPTION_KEY", explicit_key)
        unused_key_file = tmp_path / "should_not_exist.key"

        service_1 = LLMService(test_db, secret_key_file=unused_key_file)
        assert not unused_key_file.exists()

        service_1.update_setting(provider="openai", api_key="sk-env-priority-9999", enabled=True)

        service_2 = LLMService(test_db, secret_key_file=unused_key_file)
        assert service_2.get_provider("openai").api_key == "sk-env-priority-9999"


class TestLLMSettingPartialUpdate:
    """Whitebox tests for updating non-key LLM setting fields."""

    def test_update_setting_preserves_encrypted_key(self, test_db):
        """Updating model/enabled/api_base_url/is_default with api_key=None keeps existing encrypted key."""
        service = LLMService(test_db)
        service.initialize_default_settings()

        service.update_setting(
            provider="kimi",
            api_key="sk-kimi-keep-me-8888",
            model="moonshot-v1-32k",
            enabled=True,
        )

        # Update model, base_url, and default flag without passing api_key
        updated = service.update_setting(
            provider="kimi",
            api_key=None,
            model="moonshot-v1-128k",
            api_base_url="https://custom.moonshot.example/v1",
            enabled=True,
            is_default=True,
        )

        assert updated.api_key_set is True
        assert updated.model == "moonshot-v1-128k"
        assert updated.api_base_url == "https://custom.moonshot.example/v1"
        assert updated.is_default is True
        assert service.get_default_provider() == "kimi"

        provider_instance = service.get_provider("kimi")
        assert provider_instance.api_key == "sk-kimi-keep-me-8888"
        assert provider_instance.api_base_url == "https://custom.moonshot.example/v1"


class TestKimiValidation:
    """Whitebox tests for KimiProvider key validation and safe key masking."""

    @pytest.mark.asyncio
    async def test_kimi_validate_api_key_success(self):
        """KimiProvider.validate_api_key uses minimal chat completion (max_tokens=5)."""
        with patch("openai.AsyncOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=MagicMock())

            provider = KimiProvider(api_key="sk-kimi-valid-test-1234", model="moonshot-v1-8k")
            result = await provider.validate_api_key()

            assert result is True
            mock_client.chat.completions.create.assert_awaited_once_with(
                model="moonshot-v1-8k",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
            )
            mock_client.models.list.assert_not_called()

    @pytest.mark.asyncio
    async def test_kimi_validate_api_key_raises_detailed_error(self):
        """KimiProvider.validate_api_key re-raises exceptions so callers inspect error details."""
        with patch("openai.AsyncOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(
                side_effect=RuntimeError("Error code: 401 - Invalid Authentication")
            )

            provider = KimiProvider(api_key="sk-kimi-bad-key-0000")
            with pytest.raises(RuntimeError, match="401 - Invalid Authentication"):
                await provider.validate_api_key()

    def test_mask_api_key_never_exposes_prefix(self):
        """mask_api_key only shows **** + last 4 chars when length > 8, else ***."""
        assert mask_api_key(None) == "***"
        assert mask_api_key("") == "***"
        assert mask_api_key("short123") == "***"  # length == 8 -> '***'
        masked = mask_api_key("sk-supersecretprefix-7890")
        assert masked == "****7890"
        assert "sk-" not in masked
        assert "supersecret" not in masked


# ============== Blackbox API Tests ==============

class TestSettingsAPIBlackbox:
    """Blackbox FastAPI TestClient tests for /api/settings/llm endpoints."""

    def test_encrypted_key_persists_across_requests(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ):
        """Keys saved in one HTTP request remain decryptable in subsequent requests via .icde_secret_key."""
        monkeypatch.delenv("LLM_ENCRYPTION_KEY", raising=False)

        put_resp = client.put(
            "/api/settings/llm",
            json={
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "api_key": "sk-proj-synthetic-roundtrip-5678",
                        "model": "gpt-4o",
                        "enabled": True,
                        "is_default": True,
                    }
                },
            },
        )
        assert put_resp.status_code == 200

        with patch("openai.AsyncOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.models.list = AsyncMock(return_value=MagicMock())

            val_resp = client.post("/api/settings/llm/openai/validate")
            assert val_resp.status_code == 200
            body = val_resp.json()
            assert body["valid"] is True
            assert body["debug"]["masked_key"] == "****5678"
            assert "sk-proj-" not in val_resp.text
            mock_client_cls.assert_called_once_with(api_key="sk-proj-synthetic-roundtrip-5678")

    def test_put_llm_settings_without_api_key_preserves_key(
        self, client: TestClient, test_db, monkeypatch: pytest.MonkeyPatch
    ):
        """PUT /api/settings/llm with model/enabled/is_default changes and null/omitted api_key keeps keys."""
        monkeypatch.delenv("LLM_ENCRYPTION_KEY", raising=False)

        # Step 1: Configure initial keys for openai and kimi
        init_resp = client.put(
            "/api/settings/llm",
            json={
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "api_key": "sk-openai-initial-secret-1111",
                        "model": "gpt-4o",
                        "enabled": True,
                        "is_default": True,
                    },
                    "kimi": {
                        "api_key": "sk-kimi-initial-secret-2222",
                        "model": "moonshot-v1-32k",
                        "enabled": True,
                        "is_default": False,
                    },
                },
            },
        )
        assert init_resp.status_code == 200

        # Step 2: Update model, enabled, api_base_url, and default_provider WITHOUT resending API keys
        # (openai omits api_key; kimi sends explicit api_key: null)
        update_resp = client.put(
            "/api/settings/llm",
            json={
                "default_provider": "kimi",
                "providers": {
                    "openai": {
                        "model": "gpt-4o-mini",
                        "enabled": False,
                        "is_default": False,
                    },
                    "kimi": {
                        "api_key": None,
                        "model": "moonshot-v1-128k",
                        "api_base_url": "https://api.moonshot.cn/v1",
                        "enabled": True,
                        "is_default": True,
                    },
                },
            },
        )
        assert update_resp.status_code == 200
        updated_data = update_resp.json()
        assert updated_data["default_provider"] == "kimi"

        # Step 3: Verify via GET /api/settings/llm
        get_resp = client.get("/api/settings/llm")
        assert get_resp.status_code == 200
        by_provider = {p["provider"]: p for p in get_resp.json()["providers"]}

        assert by_provider["openai"]["api_key_set"] is True
        assert by_provider["openai"]["api_key"] is None
        assert by_provider["openai"]["model"] == "gpt-4o-mini"
        assert by_provider["openai"]["enabled"] is False
        assert by_provider["openai"]["is_default"] is False

        assert by_provider["kimi"]["api_key_set"] is True
        assert by_provider["kimi"]["api_key"] is None
        assert by_provider["kimi"]["model"] == "moonshot-v1-128k"
        assert by_provider["kimi"]["api_base_url"] == "https://api.moonshot.cn/v1"
        assert by_provider["kimi"]["enabled"] is True
        assert by_provider["kimi"]["is_default"] is True

        # Confirm the underlying encrypted keys still decrypt to the original values
        verifier_service = LLMService(test_db)
        assert verifier_service.get_provider("kimi").api_key == "sk-kimi-initial-secret-2222"

    def test_validate_kimi_endpoint_valid_and_invalid(self, client: TestClient):
        """POST /api/settings/llm/kimi/validate handles valid and invalid keys with safe masking."""
        raw_secret = "sk-kimi-topsecretprefix-9012"
        put_resp = client.put(
            "/api/settings/llm/kimi",
            json={
                "api_key": raw_secret,
                "model": "moonshot-v1-32k",
                "enabled": True,
            },
        )
        assert put_resp.status_code == 200

        # Valid key case
        with patch("openai.AsyncOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=MagicMock())

            ok_resp = client.post("/api/settings/llm/kimi/validate")
            assert ok_resp.status_code == 200
            ok_data = ok_resp.json()
            assert ok_data["provider"] == "kimi"
            assert ok_data["valid"] is True
            assert ok_data["base_url"] == KIMI_API_BASE
            assert ok_data["model"] == "moonshot-v1-32k"
            assert ok_data["debug"]["masked_key"] == "****9012"
            assert "sk-kimi-" not in ok_resp.text
            assert raw_secret not in ok_resp.text

        # Invalid key case (even if upstream SDK echoes the raw key in its exception message)
        with patch("openai.AsyncOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(
                side_effect=PermissionError(f"401 Unauthorized for key {raw_secret}")
            )

            err_resp = client.post("/api/settings/llm/kimi/validate")
            assert err_resp.status_code == 200
            err_data = err_resp.json()
            assert err_data["provider"] == "kimi"
            assert err_data["valid"] is False
            assert err_data["error_type"] == "PermissionError"
            assert "401 Unauthorized" in err_data["error_detail"]
            assert err_data["base_url"] == KIMI_API_BASE
            assert err_data["model"] == "moonshot-v1-32k"
            assert err_data["debug"]["masked_key"] == "****9012"
            # Raw key and prefix must NEVER leak in HTTP response
            assert raw_secret not in err_resp.text
            assert "sk-kimi-" not in err_resp.text


class TestScriptMetadataPersistence:
    """Blackbox FastAPI TestClient tests for /api/scripts structured metadata fields."""

    def test_create_and_update_script_structured_metadata(self, client: TestClient):
        """POST /api/scripts and PUT /api/scripts/{id} round-trip all 5 structured metadata fields."""
        create_payload = {
            "name": "summarize_adsl_demographics",
            "display_name": "ADSL 基线人口学汇总",
            "description": "Compute baseline demographics summary table by treatment arm",
            "code": "def summarize_demographics(adsl_df, population='FAS'):\n    return adsl_df\n",
            "keywords": ["ADSL", "人口学", "demographics"],
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "adsl_df": {
                        "type": "DataFrame",
                        "description": "Subject-level analysis dataset",
                    },
                    "population": {
                        "type": "string",
                        "description": "Target analysis population",
                        "enum": ["ITT", "FAS", "SAS"],
                        "default": "FAS",
                    },
                },
                "required": ["adsl_df"],
            },
            "returns_schema": {
                "type": "DataFrame",
                "description": "Formatted baseline summary table",
                "properties": {
                    "arm": {"type": "string", "description": "Treatment group"},
                    "n": {"type": "int", "description": "Subject count"},
                },
            },
            "functions": [
                {
                    "name": "summarize_demographics",
                    "description": "Main entry point for baseline table generation",
                    "is_main": True,
                }
            ],
            "use_cases": [
                "生成临床研究基线人口学特征表（Table 14.1.1）",
                "Compare baseline age and sex across arms",
            ],
            "example_calls": [
                {
                    "input": "summarize_demographics(adsl_df, population='FAS')",
                    "output": "DataFrame(rows=8, cols=4)",
                    "description": "Standard FAS demographics summary",
                }
            ],
        }

        create_resp = client.post("/api/scripts", json=create_payload)
        assert create_resp.status_code == 201
        created = create_resp.json()
        script_id = created["id"]

        # Verify GET round-trip after POST
        get_resp = client.get(f"/api/scripts/{script_id}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()

        assert fetched["parameters_schema"]["required"] == ["adsl_df"]
        assert fetched["parameters_schema"]["properties"]["population"]["enum"] == ["ITT", "FAS", "SAS"]
        assert fetched["parameters_schema"]["properties"]["population"]["default"] == "FAS"
        assert fetched["returns_schema"]["type"] == "DataFrame"
        assert fetched["returns_schema"]["properties"]["n"]["type"] == "int"
        assert fetched["functions"] == [
            {
                "name": "summarize_demographics",
                "description": "Main entry point for baseline table generation",
                "is_main": True,
            }
        ]
        assert fetched["use_cases"] == create_payload["use_cases"]
        assert fetched["example_calls"] == create_payload["example_calls"]

        # Update all 5 structured metadata fields via PUT /api/scripts/{id}
        update_payload = {
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "adsl_df": {
                        "type": "DataFrame",
                        "description": "Updated subject dataset",
                    },
                    "include_p_value": {
                        "type": "boolean",
                        "description": "Whether to compute p-values",
                        "default": False,
                    },
                },
                "required": ["adsl_df", "include_p_value"],
            },
            "returns_schema": {
                "type": "dict",
                "description": "Summary table and metadata dictionary",
                "properties": {"table": {"type": "DataFrame"}},
            },
            "functions": [
                {
                    "name": "summarize_demographics",
                    "description": "Main entry point",
                    "is_main": True,
                },
                {
                    "name": "format_p_value",
                    "description": "Helper formatter",
                    "is_main": False,
                },
            ],
            "use_cases": ["Updated use case: CSR baseline summary with p-values"],
            "example_calls": [
                {
                    "input": "summarize_demographics(adsl_df, include_p_value=True)",
                    "output": "{'table': DataFrame(...)}",
                    "description": "With p-value column",
                }
            ],
        }

        put_resp = client.put(f"/api/scripts/{script_id}", json=update_payload)
        assert put_resp.status_code == 200

        # Partial update of description only must preserve all 5 structured metadata fields
        partial_resp = client.put(
            f"/api/scripts/{script_id}",
            json={"description": "Updated description only"},
        )
        assert partial_resp.status_code == 200

        final_get = client.get(f"/api/scripts/{script_id}")
        assert final_get.status_code == 200
        final_data = final_get.json()

        assert final_data["description"] == "Updated description only"
        assert final_data["parameters_schema"]["required"] == ["adsl_df", "include_p_value"]
        assert final_data["returns_schema"]["type"] == "dict"
        assert len(final_data["functions"]) == 2
        assert final_data["use_cases"] == ["Updated use case: CSR baseline summary with p-values"]
        assert final_data["example_calls"] == update_payload["example_calls"]


class TestWorkspaceIsolation:
    """Verify tests never pollute real backend/uploads/ or backend/.icde_secret_key."""

    def test_uploads_and_secret_key_redirected_to_tmp_path(
        self,
        client: TestClient,
        sample_csv_content: str,
        isolate_upload_and_secret_paths: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Creating datasets, uploading files, and saving encrypted keys stay strictly inside tmp_path."""
        monkeypatch.delenv("LLM_ENCRYPTION_KEY", raising=False)

        ds_resp = client.post("/api/datasets", json={"name": "Synthetic_Isolation_Check"})
        assert ds_resp.status_code == 201
        ds_id = ds_resp.json()["id"]

        files = {"files": ("synthetic.csv", io.BytesIO(sample_csv_content.encode()), "text/csv")}
        upload_resp = client.post(f"/api/datasets/{ds_id}/files", files=files)
        assert upload_resp.status_code == 200

        key_resp = client.put(
            "/api/settings/llm/openai",
            json={"api_key": "sk-isolated-temp-key-1234", "enabled": True},
        )
        assert key_resp.status_code == 200

        # Confirm files were written into the isolated tmp_path directory
        assert (isolate_upload_and_secret_paths["upload_dir"] / ds_id).is_dir()
        assert isolate_upload_and_secret_paths["secret_key_file"].is_file()

        # Confirm real workspace backend/uploads/ has zero test folders/files and no real .icde_secret_key
        real_uploads_dir = BASE_DIR / "uploads"
        entries = [p.name for p in real_uploads_dir.iterdir() if p.name != ".gitkeep"]
        assert entries == [], f"Unexpected test artifacts in backend/uploads: {entries}"
        assert not (BASE_DIR / ".icde_secret_key").exists()
