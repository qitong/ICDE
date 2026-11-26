"""
Whitebox & blackbox tests for `WorkspaceGuard` (`DatasetType.RAW` immutability)
and `OpenCodeConfigBuilder` (multi-LLM config generation without secret leakage).

All fixtures use 100% synthetic in-memory SQLite + temporary directories.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import pytest

from app.harness.opencode_config import DEFAULT_KIMI_BASE_URL, OpenCodeConfigBuilder
from app.harness.workspace_guard import ReadOnlyDatasetViolationError, WorkspaceGuard
from app.models.dataset import Dataset, DatasetFile, DatasetType
from app.models.project import Project
from app.models.script import Script
from app.schemas.chat import MentionRef
from app.services.file_parser import FileParser
from app.services.llm_service import LLMService


@pytest.fixture
def raw_dataset_bundle(test_db, test_upload_dir, sample_csv_content):
    """Create a synthetic project with a RAW dataset and a writable sibling area."""
    project = Project(name="Synthetic Oncology Study", description="Synthetic test project")
    test_db.add(project)
    test_db.commit()

    raw_dir = test_upload_dir / "raw_adsl_ds"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_csv = raw_dir / "adsl.csv"
    raw_csv.write_text(sample_csv_content, encoding="utf-8")

    row_count, col_count, _, col_info_json = FileParser.parse_file(raw_csv)

    raw_ds = Dataset(
        name="ADSL_RAW",
        type=DatasetType.RAW,
        project_id=project.id,
        study_name="SYNTH-001",
        version_name="v1.0",
        folder_path=str(raw_dir),
        row_count=row_count,
        column_count=col_count,
        file_count=1,
        total_size=raw_csv.stat().st_size,
    )
    test_db.add(raw_ds)
    test_db.commit()

    raw_file = DatasetFile(
        dataset_id=raw_ds.id,
        file_name="adsl.csv",
        original_name="ADSL.csv",
        file_path=str(raw_csv),
        file_type="csv",
        file_size=raw_csv.stat().st_size,
        row_count=row_count,
        column_count=col_count,
        column_info=col_info_json,
        parse_status="parsed",
    )
    test_db.add(raw_file)
    test_db.commit()

    return {
        "project": project,
        "dataset": raw_ds,
        "file": raw_file,
        "raw_dir": raw_dir,
        "raw_csv": raw_csv,
    }


class TestWorkspaceGuardPathProtection:
    """Verify canonical path resolution, traversal (`../`), and symlink protections."""

    def test_direct_write_to_raw_file_and_folder_rejected(self, test_db, test_upload_dir, raw_dataset_bundle):
        guard = WorkspaceGuard(test_db, workspace_root=test_upload_dir)

        with pytest.raises(ReadOnlyDatasetViolationError) as exc_file:
            guard.assert_writable(raw_dataset_bundle["raw_csv"])
        assert exc_file.value.dataset_id == raw_dataset_bundle["dataset"].id

        with pytest.raises(ReadOnlyDatasetViolationError):
            guard.assert_writable(raw_dataset_bundle["raw_dir"])

        with pytest.raises(ReadOnlyDatasetViolationError):
            guard.assert_writable(raw_dataset_bundle["raw_dir"] / "injected_extra.csv")

    def test_relative_path_traversal_into_raw_rejected(self, test_db, test_upload_dir, raw_dataset_bundle):
        derived_dir = test_upload_dir / "derived_work" / "nested"
        derived_dir.mkdir(parents=True, exist_ok=True)
        guard = WorkspaceGuard(test_db, workspace_root=derived_dir)

        traversal_target = "../../raw_adsl_ds/adsl.csv"
        with pytest.raises(ReadOnlyDatasetViolationError) as exc_info:
            guard.assert_writable(traversal_target, base_dir=derived_dir)
        assert exc_info.value.dataset_id == raw_dataset_bundle["dataset"].id

    def test_symlink_pointing_to_raw_file_rejected(self, test_db, test_upload_dir, raw_dataset_bundle):
        sandbox_dir = test_upload_dir / "agent_sandbox"
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        symlink_file = sandbox_dir / "innocent_looking.csv"
        symlink_file.symlink_to(raw_dataset_bundle["raw_csv"])

        guard = WorkspaceGuard(test_db, workspace_root=sandbox_dir)
        with pytest.raises(ReadOnlyDatasetViolationError):
            guard.assert_writable(symlink_file)

    def test_deleting_ancestor_directory_of_raw_dataset_rejected(
        self, test_db, test_upload_dir, raw_dataset_bundle
    ):
        guard = WorkspaceGuard(test_db, workspace_root=test_upload_dir)
        with pytest.raises(ReadOnlyDatasetViolationError):
            guard.assert_writable(test_upload_dir, is_directory_delete=True)

    def test_sibling_derived_dataset_path_is_allowed(self, test_db, test_upload_dir, raw_dataset_bundle):
        guard = WorkspaceGuard(test_db, workspace_root=test_upload_dir)
        derived_target = test_upload_dir / "derived_fas_001" / "fas.csv"
        resolved = guard.assert_writable(derived_target)
        assert resolved == derived_target.resolve(strict=False)


class TestWorkspaceGuardIntegrityAndPermissions:
    """Verify cryptographic SHA-256 snapshots and POSIX `0o444` file locking."""

    def test_sha256_snapshot_detects_modification_deletion_and_injection(
        self, test_db, test_upload_dir, raw_dataset_bundle
    ):
        guard = WorkspaceGuard(test_db, workspace_root=test_upload_dir)
        raw_csv: Path = raw_dataset_bundle["raw_csv"]
        original_text = raw_csv.read_text(encoding="utf-8")

        snapshot = guard.snapshot_raw_files()
        assert guard.verify_raw_files_unchanged(snapshot) is True

        # 1. Single-character modification triggers violation
        raw_csv.write_text(original_text + "P999,40,F,Y,N,Y\n", encoding="utf-8")
        with pytest.raises(ReadOnlyDatasetViolationError, match="altered"):
            guard.verify_raw_files_unchanged(snapshot)

        # Restore exact content -> verification succeeds again
        raw_csv.write_text(original_text, encoding="utf-8")
        assert guard.verify_raw_files_unchanged(snapshot) is True

        # 2. Injecting an extra file inside RAW folder triggers violation
        rogue_file = raw_dataset_bundle["raw_dir"] / "rogue.txt"
        rogue_file.write_text("tamper", encoding="utf-8")
        with pytest.raises(ReadOnlyDatasetViolationError, match="inventory changed"):
            guard.verify_raw_files_unchanged(snapshot)
        rogue_file.unlink()

        # 3. Deleting RAW file triggers violation
        raw_csv.unlink()
        with pytest.raises(ReadOnlyDatasetViolationError, match="deleted"):
            guard.verify_raw_files_unchanged(snapshot)

    def test_lock_raw_dataset_files_0o444_and_unlock_for_deletion(
        self, test_db, test_upload_dir, raw_dataset_bundle
    ):
        guard = WorkspaceGuard(test_db, workspace_root=test_upload_dir)
        raw_csv: Path = raw_dataset_bundle["raw_csv"]

        locked = guard.lock_raw_dataset_files()
        assert raw_csv in locked
        assert (raw_csv.stat().st_mode & 0o777) == 0o444

        if os.geteuid() != 0:
            with pytest.raises(PermissionError):
                raw_csv.write_text("overwrite attempt", encoding="utf-8")

        unlocked = guard.unlock_for_deletion(raw_dataset_bundle["dataset"])
        assert raw_csv in unlocked
        assert (raw_csv.stat().st_mode & 0o200) != 0


class TestOpenCodeConfigBuilder:
    """Verify multi-LLM provider mapping, secret isolation, and `opencode.json` + `AGENTS.md`."""

    @pytest.mark.parametrize(
        ("icde_provider", "model", "secret_key", "base_url", "expected_oc_provider", "expected_env_var"),
        [
            ("openai", "gpt-4o", "sk-openai-super-secret-111", None, "openai", "OPENAI_API_KEY"),
            (
                "claude",
                "claude-sonnet-4-20250514",
                "sk-ant-super-secret-222",
                None,
                "anthropic",
                "ANTHROPIC_API_KEY",
            ),
            (
                "gemini",
                "gemini-2.0-flash",
                "AIzaSyGeminiSuperSecret333",
                None,
                "google",
                "GOOGLE_GENERATIVE_AI_API_KEY",
            ),
            (
                "kimi",
                "moonshot-v1-32k",
                "sk-kimi-super-secret-444",
                "https://api.moonshot.cn/v1",
                "kimi",
                "MOONSHOT_API_KEY",
            ),
        ],
    )
    def test_multi_provider_mapping_never_writes_plaintext_keys(
        self,
        test_db,
        test_upload_dir,
        raw_dataset_bundle,
        icde_provider,
        model,
        secret_key,
        base_url,
        expected_oc_provider,
        expected_env_var,
    ):
        llm_service = LLMService(test_db)
        llm_service.update_setting(
            provider=icde_provider,
            api_key=secret_key,
            model=model,
            enabled=True,
            is_default=True,
            api_base_url=base_url,
        )

        script = Script(
            name="fas_filter",
            display_name="FAS Filter",
            description="Filter randomized subjects without major protocol deviations",
            code="def transform(df): return df[df['RANDFL'] == 'Y']",
        )
        test_db.add(script)
        test_db.commit()

        builder = OpenCodeConfigBuilder(
            test_db,
            database_url="sqlite:///:memory:",
            upload_dir=test_upload_dir,
        )
        bundle = builder.build(
            provider_name=icde_provider,
            project_id=raw_dataset_bundle["project"].id,
            mentions=[
                MentionRef(
                    type="dataset",
                    id=raw_dataset_bundle["dataset"].id,
                    path="@SYNTH-001/ADSL_RAW",
                    name="ADSL_RAW",
                )
            ],
        )

        try:
            assert bundle.config_path.exists()
            assert bundle.agents_md_path.exists()

            config_raw = bundle.config_path.read_text(encoding="utf-8")
            agents_raw = bundle.agents_md_path.read_text(encoding="utf-8")

            # Crucial hygiene guarantee: zero plaintext API key leakage to disk
            assert secret_key not in config_raw
            assert secret_key not in agents_raw

            # Runtime env holds decrypted key in memory
            assert bundle.env[expected_env_var] == secret_key
            if icde_provider == "gemini":
                assert bundle.env["GEMINI_API_KEY"] == secret_key

            parsed_cfg = json.loads(config_raw)
            assert parsed_cfg["model"] == f"{expected_oc_provider}/{model}"
            provider_block = parsed_cfg["provider"][expected_oc_provider]
            assert provider_block["options"]["apiKey"] == f"{{env:{expected_env_var}}}"

            if icde_provider == "kimi":
                assert provider_block["npm"] == "@ai-sdk/openai-compatible"
                assert provider_block["options"]["baseURL"] == DEFAULT_KIMI_BASE_URL

            # Verify icde-mcp server registration & RAW deny permissions
            assert "icde-mcp" in parsed_cfg["mcp"]
            raw_dir_resolved = str(raw_dataset_bundle["raw_dir"].resolve())
            assert parsed_cfg["permission"]["edit"][raw_dir_resolved] == "deny"
            assert parsed_cfg["permission"]["edit"][f"{raw_dir_resolved}/**"] == "deny"

            # Verify AGENTS.md includes @-mentioned columns & read-only instructions
            assert "ADSL_RAW" in agents_raw
            assert "SUBJID" in agents_raw
            assert "READ-ONLY" in agents_raw
        finally:
            workspace_dir = bundle.workspace_dir
            bundle.cleanup()
            assert not workspace_dir.exists()

    def test_missing_or_disabled_provider_raises_value_error(self, test_db, test_upload_dir):
        llm_service = LLMService(test_db)
        llm_service.initialize_default_settings()
        builder = OpenCodeConfigBuilder(test_db, upload_dir=test_upload_dir)

        with pytest.raises(ValueError, match="API key not configured"):
            builder.build(provider_name="openai")

        llm_service.update_setting(provider="claude", api_key="sk-ant-test", enabled=False)
        with pytest.raises(ValueError, match="disabled"):
            builder.build(provider_name="claude")
