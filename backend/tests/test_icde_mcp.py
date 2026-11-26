"""
Whitebox & blackbox tests for the local ICDE MCP Bridge (`backend/app/mcp/`):
- Direct Python callable invocation (`ICDEMCPTools`)
- Full MCP JSON-RPC 2.0 lifecycle (`initialize` -> `notifications/initialized` ->
  `tools/list` -> `tools/call`) over stdio and in-memory dispatch
- Byte-for-byte SHA-256 preservation of `RAW` datasets during `icde_derive_dataset`
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

from app.harness.approval_store import ApprovalStore
from app.harness.events import HarnessEvent
from app.harness.workspace_guard import ReadOnlyDatasetViolationError, WorkspaceGuard
from app.mcp.icde_mcp_server import ICDEMCPServer
from app.mcp.tools import ICDEMCPTools
from app.models.dataset import Dataset, DatasetFile, DatasetLineage, DatasetType
from app.models.project import Project
from app.models.script import Script
from app.services.file_parser import FileParser


@pytest.fixture
def mcp_env(test_db, test_upload_dir, sample_csv_content):
    """Create isolated synthetic project + RAW dataset for MCP tool testing."""
    project = Project(name="MCP Synthetic Trial", description="Trial for MCP bridge tests")
    test_db.add(project)
    test_db.commit()

    raw_folder = test_upload_dir / "raw_study_001"
    raw_folder.mkdir(parents=True, exist_ok=True)
    raw_csv = raw_folder / "adsl_raw.csv"
    raw_csv.write_text(sample_csv_content, encoding="utf-8")

    row_count, col_count, _, col_info_json = FileParser.parse_file(raw_csv)

    raw_dataset = Dataset(
        name="ADSL_RAW",
        type=DatasetType.RAW,
        project_id=project.id,
        study_name="TRIAL-MCP",
        version_name="v1.0",
        patient_id_column="SUBJID",
        folder_path=str(raw_folder),
        row_count=row_count,
        column_count=col_count,
        file_count=1,
        total_size=raw_csv.stat().st_size,
    )
    test_db.add(raw_dataset)
    test_db.commit()

    raw_file = DatasetFile(
        dataset_id=raw_dataset.id,
        file_name="adsl_raw.csv",
        original_name="ADSL_RAW.csv",
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

    try:
        yield {
            "db": test_db,
            "upload_dir": test_upload_dir,
            "project": project,
            "raw_dataset": raw_dataset,
            "raw_csv": raw_csv,
        }
    finally:
        WorkspaceGuard.unlock_for_deletion(raw_dataset)


class TestICDEMCPToolsDirect:
    """Test direct Python callable execution of all 6 ICDE MCP tools."""

    def test_list_and_inspect_dataset_preserve_raw_hash(self, mcp_env):
        db = mcp_env["db"]
        raw_csv: Path = mcp_env["raw_csv"]
        sha_before = WorkspaceGuard.compute_sha256(raw_csv)

        tools = ICDEMCPTools(db, upload_dir=mcp_env["upload_dir"])

        listed = tools.icde_list_datasets(project_id=mcp_env["project"].id)
        assert listed["count"] == 1
        assert listed["datasets"][0]["name"] == "ADSL_RAW"
        assert listed["datasets"][0]["type"] == "RAW"
        assert listed["datasets"][0]["read_only"] is True
        assert listed["datasets"][0]["row_count"] == 5

        inspected = tools.icde_inspect_dataset(mcp_env["raw_dataset"].id)
        col_names = [c["name"] for c in inspected["columns"]]
        assert col_names == ["SUBJID", "AGE", "SEX", "RANDFL", "PPROTFL", "SAFFL"]
        assert inspected["lineage"] == {"ancestors": [], "descendants": []}
        assert WorkspaceGuard.compute_sha256(raw_csv) == sha_before

    def test_save_and_list_scripts_emit_workspace_event_and_validate_syntax(self, mcp_env):
        captured: list[HarnessEvent] = []
        tools = ICDEMCPTools(
            mcp_env["db"],
            upload_dir=mcp_env["upload_dir"],
            event_sink=captured.append,
            conversation_id="conv_test_1",
        )

        # Reject broken Python syntax
        with pytest.raises(ValueError, match="Invalid Python script syntax"):
            tools.icde_save_script(
                name="broken_script",
                display_name="Broken",
                description="Broken syntax",
                code="def transform(df)\n    return df",
            )

        saved_v1 = tools.icde_save_script(
            name="derive_fas",
            display_name="FAS Cohort Filter",
            description="Include RANDFL == Y and exclude PPROTFL == Y",
            code=(
                "import pandas as pd\n"
                "def transform(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    return df[(df['RANDFL'] == 'Y') & (df['PPROTFL'] != 'Y')].copy()\n"
            ),
            keywords=["FAS", "cohort"],
        )
        assert saved_v1["action"] == "created"
        assert saved_v1["script"]["version"] == 1
        assert len(captured) == 1
        assert captured[0].type == "workspace_event"
        assert captured[0].event_name == "script_saved"

        # Updating same script increments version
        saved_v2 = tools.icde_save_script(
            name="derive_fas",
            display_name="FAS Cohort Filter v2",
            description="Updated FAS description",
            code=(
                "import pandas as pd\n"
                "def transform(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    return df[(df['RANDFL'] == 'Y') & (df['PPROTFL'] != 'Y')].copy()\n"
            ),
        )
        assert saved_v2["action"] == "updated"
        assert saved_v2["script"]["version"] == 2

        search_res = tools.icde_list_scripts(query="FAS")
        assert search_res["count"] == 1
        assert search_res["scripts"][0]["display_name"] == "FAS Cohort Filter v2"

    def test_derive_dataset_atomic_metadata_lineage_and_raw_immutability(self, mcp_env):
        db = mcp_env["db"]
        raw_csv: Path = mcp_env["raw_csv"]
        sha_before = WorkspaceGuard.compute_sha256(raw_csv)

        captured: list[HarnessEvent] = []
        tools = ICDEMCPTools(
            db,
            upload_dir=mcp_env["upload_dir"],
            event_sink=captured.append,
        )

        script_res = tools.icde_save_script(
            name="fas_population",
            display_name="FAS Population",
            description="Randomized subjects without major protocol deviations",
            code=(
                "import pandas as pd\n"
                "def transform(df: pd.DataFrame) -> pd.DataFrame:\n"
                "    return df[(df['RANDFL'] == 'Y') & (df['PPROTFL'] != 'Y')].copy()\n"
            ),
        )
        script_id = script_res["script"]["id"]
        captured.clear()

        derive_res = tools.icde_derive_dataset(
            source_dataset_id=mcp_env["raw_dataset"].id,
            script_id=script_id,
            output_name="ADSL_FAS",
        )

        # 1. Byte-for-byte SHA-256 of RAW file is unchanged
        assert WorkspaceGuard.compute_sha256(raw_csv) == sha_before

        # 2. Both Dataset (DERIVED), DatasetFile, and DatasetLineage exist in SQLite
        derived_id = derive_res["dataset"]["id"]
        ds_row = db.query(Dataset).filter(Dataset.id == derived_id).first()
        assert ds_row is not None
        assert ds_row.type == DatasetType.DERIVED
        assert ds_row.row_count == 3
        assert ds_row.column_count == 6
        assert ds_row.source_dataset_id == mcp_env["raw_dataset"].id
        assert ds_row.script_id == script_id

        file_rows = db.query(DatasetFile).filter(DatasetFile.dataset_id == derived_id).all()
        assert len(file_rows) == 1
        assert file_rows[0].parse_status == "parsed"
        assert file_rows[0].row_count == 3
        assert file_rows[0].column_info is not None

        lineage_row = (
            db.query(DatasetLineage)
            .filter(
                DatasetLineage.parent_id == mcp_env["raw_dataset"].id,
                DatasetLineage.child_id == derived_id,
            )
            .first()
        )
        assert lineage_row is not None
        assert lineage_row.relationship == "DERIVED_FROM"

        # 3. Script usage_count incremented
        script_row = db.query(Script).filter(Script.id == script_id).first()
        assert script_row.usage_count == 1

        # 4. Workspace events emitted: dataset_derived + lineage_updated
        event_names = [ev.event_name for ev in captured]
        assert event_names == ["dataset_derived", "lineage_updated"]

    def test_derive_dataset_blocks_malicious_script_writing_to_raw_file(self, mcp_env):
        db = mcp_env["db"]
        raw_csv: Path = mcp_env["raw_csv"]
        sha_before = WorkspaceGuard.compute_sha256(raw_csv)

        tools = ICDEMCPTools(db, upload_dir=mcp_env["upload_dir"])
        tamper_script = tools.icde_save_script(
            name="malicious_tamper",
            display_name="Tamper Attempt",
            description="Attempts to overwrite RAW file during transform",
            code=(
                f"def transform(df):\n"
                f"    open({str(raw_csv)!r}, 'w').write('CORRUPTED')\n"
                f"    return df\n"
            ),
        )

        with pytest.raises((ValueError, ReadOnlyDatasetViolationError)):
            tools.icde_derive_dataset(
                source_dataset_id=mcp_env["raw_dataset"].id,
                script_id=tamper_script["script"]["id"],
                output_name="SHOULD_NOT_EXIST",
            )

        assert WorkspaceGuard.compute_sha256(raw_csv) == sha_before
        assert (
            db.query(Dataset).filter(Dataset.name == "SHOULD_NOT_EXIST").first()
            is None
        )

    def test_derive_dataset_rejects_traversal_in_output_name(self, mcp_env):
        tools = ICDEMCPTools(mcp_env["db"], upload_dir=mcp_env["upload_dir"])
        script_res = tools.icde_save_script(
            name="noop_script",
            display_name="Noop",
            description="Identity transform",
            code="def transform(df): return df.copy()",
        )
        with pytest.raises(ReadOnlyDatasetViolationError):
            tools.icde_derive_dataset(
                source_dataset_id=mcp_env["raw_dataset"].id,
                script_id=script_res["script"]["id"],
                output_name="../raw_study_001/overwrite",
            )

    def test_request_approval_persists_checkpoint(self, mcp_env):
        captured: list[HarnessEvent] = []
        tools = ICDEMCPTools(
            mcp_env["db"],
            upload_dir=mcp_env["upload_dir"],
            event_sink=captured.append,
            conversation_id="conv_hitl",
        )
        res = tools.icde_request_approval(
            action="confirm_fas_criteria",
            title="Confirm FAS Inclusion/Exclusion Criteria",
            summary="Include RANDFL='Y' and exclude PPROTFL='Y' (3 of 5 subjects retained).",
            options=["Confirm FAS (n=3)", "Use ITT All Randomized (n=4)", "Reject"],
        )
        appr_id = res["approval"]["approval_id"]
        assert res["approval"]["status"] == "pending"
        assert len(captured) == 1
        assert captured[0].type == "approval_required"
        assert captured[0].approval_id == appr_id

        store = ApprovalStore(mcp_env["db"])
        stored = store.get(appr_id)
        assert stored is not None
        assert stored.title == "Confirm FAS Inclusion/Exclusion Criteria"


class TestICDEMCPJsonRpcServer:
    """End-to-end JSON-RPC 2.0 protocol tests (`initialize` -> `tools/list` -> `tools/call`) over stdio."""

    def test_full_mcp_stdio_jsonrpc_session(self, mcp_env):
        server = ICDEMCPServer.from_session(
            mcp_env["db"],
            upload_dir=mcp_env["upload_dir"],
        )

        requests = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
            },
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "icde_list_datasets",
                    "arguments": {"project_id": mcp_env["project"].id},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "icde_inspect_dataset",
                    "arguments": {"dataset_id": mcp_env["raw_dataset"].id},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "icde_save_script",
                    "arguments": {
                        "name": "rpc_fas_script",
                        "display_name": "RPC FAS Script",
                        "description": "Filter SAFFL == Y",
                        "code": "def transform(df):\n    return df[df['SAFFL'] == 'Y'].copy()\n",
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {
                    "name": "icde_request_approval",
                    "arguments": {
                        "action": "confirm_safety_set",
                        "title": "Confirm Safety Set",
                        "summary": "Retain SAFFL == 'Y' subjects (n=4).",
                        "options": ["Approve", "Reject"],
                    },
                },
            },
        ]

        stdin_buf = io.StringIO("\n".join(json.dumps(r) for r in requests) + "\n")
        stdout_buf = io.StringIO()
        server.serve_stdio(stdin=stdin_buf, stdout=stdout_buf)

        responses = [
            json.loads(line)
            for line in stdout_buf.getvalue().splitlines()
            if line.strip()
        ]
        # Notification produced no response, so 6 responses for ids 1..6
        assert [r["id"] for r in responses] == [1, 2, 3, 4, 5, 6]

        # 1. initialize
        assert responses[0]["result"]["serverInfo"]["name"] == "icde-mcp"

        # 2. tools/list
        tool_names = [t["name"] for t in responses[1]["result"]["tools"]]
        assert set(tool_names) == {
            "icde_list_datasets",
            "icde_inspect_dataset",
            "icde_list_scripts",
            "icde_save_script",
            "icde_derive_dataset",
            "icde_request_approval",
        }

        # 3 & 4. list & inspect
        assert responses[2]["result"]["isError"] is False
        assert responses[2]["result"]["structuredContent"]["count"] == 1
        assert len(responses[3]["result"]["structuredContent"]["columns"]) == 6

        # 5. save_script -> now call icde_derive_dataset with returned script_id
        script_id = responses[4]["result"]["structuredContent"]["script"]["id"]
        derive_resp = server.handle_rpc(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "icde_derive_dataset",
                    "arguments": {
                        "source_dataset_id": mcp_env["raw_dataset"].id,
                        "script_id": script_id,
                        "output_name": "ADSL_SAF",
                    },
                },
            }
        )
        assert derive_resp is not None
        assert derive_resp["result"]["isError"] is False
        assert derive_resp["result"]["structuredContent"]["dataset"]["row_count"] == 4
        assert len(derive_resp["result"]["structuredContent"]["_icde_events"]) == 2

        # 6. Unknown tool returns JSON-RPC -32601
        unknown_resp = server.handle_rpc(
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {"name": "nonexistent_tool", "arguments": {}},
            }
        )
        assert unknown_resp is not None
        assert unknown_resp["error"]["code"] == -32601

        # 7. Explicit `"id": null` is NOT swallowed as a notification; returns -32600 error
        null_id_resp = server.handle_rpc(
            {
                "jsonrpc": "2.0",
                "id": None,
                "method": "tools/list",
            }
        )
        assert null_id_resp is not None
        assert null_id_resp["id"] is None
        assert null_id_resp["error"]["code"] == -32600

    def test_derive_dataset_cleans_up_derived_dir_if_db_commit_raises(self, mcp_env, monkeypatch):
        db = mcp_env["db"]
        upload_dir: Path = mcp_env["upload_dir"]
        tools = ICDEMCPTools(db, upload_dir=upload_dir)
        script_res = tools.icde_save_script(
            name="commit_fail_script",
            display_name="Commit Fail",
            description="Valid transform whose DB commit fails",
            code="def transform(df):\n    return df.copy()\n",
        )

        existing_entries = set(upload_dir.iterdir())

        def boom_commit():
            raise RuntimeError("Simulated SQLite commit failure")

        monkeypatch.setattr(db, "commit", boom_commit)

        with pytest.raises(RuntimeError, match="Simulated SQLite commit failure"):
            tools.icde_derive_dataset(
                source_dataset_id=mcp_env["raw_dataset"].id,
                script_id=script_res["script"]["id"],
                output_name="ORPHAN_DERIVED",
            )

        # Ensure no orphan derived directory remained on disk
        assert set(upload_dir.iterdir()) == existing_entries

    def test_subprocess_cli_module_execution_no_circular_import(self, tmp_path: Path):
        """
        Blackbox regression test for [BLOCKING-1]:
        Spawn `[sys.executable, "-m", "app.mcp.icde_mcp_server"]` in a clean subprocess
        and verify `initialize` -> `notifications/initialized` -> `tools/list` -> `tools/call`.
        """
        backend_dir = Path(__file__).resolve().parents[1]
        subproc_db_file = tmp_path / "mcp_subproc_store"
        subproc_uploads = tmp_path / "mcp_subproc_uploads"
        subproc_uploads.mkdir(parents=True, exist_ok=True)

        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(backend_dir),
            "DATABASE_URL": f"sqlite:///{subproc_db_file}",
            "ICDE_DATABASE_URL": f"sqlite:///{subproc_db_file}",
            "ICDE_UPLOAD_DIR": str(subproc_uploads),
        }

        rpc_frames = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
            },
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "icde_save_script",
                    "arguments": {
                        "name": "subproc_fas",
                        "display_name": "Subprocess FAS",
                        "description": "Created over real stdio subprocess",
                        "code": "def transform(df):\n    return df\n",
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "icde_list_scripts",
                    "arguments": {"query": "Subprocess"},
                },
            },
        ]
        stdin_payload = "\n".join(json.dumps(f) for f in rpc_frames) + "\n"

        proc = subprocess.run(
            [sys.executable, "-m", "app.mcp.icde_mcp_server"],
            input=stdin_payload,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(backend_dir),
            timeout=20,
        )

        assert proc.returncode == 0, f"icde_mcp_server crashed with stderr:\n{proc.stderr}"
        lines = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        assert [msg["id"] for msg in lines] == [1, 2, 3, 4]
        assert lines[0]["result"]["serverInfo"]["name"] == "icde-mcp"
        assert len(lines[1]["result"]["tools"]) == 6
        assert lines[2]["result"]["isError"] is False
        assert lines[3]["result"]["structuredContent"]["count"] == 1
