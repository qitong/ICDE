"""
End-to-end whitebox & blackbox tests for `OpenCodeHarnessAdapter` and FastAPI
`/api/harness/*` + `/api/chat/stream` endpoints using mocked `opencode serve`
HTTP/SSE transports (`httpx.MockTransport` and `OpenCodeTransport`).

Zero external API keys or patient files required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import httpx
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.harness.opencode_adapter import HttpOpenCodeTransport, OpenCodeHarnessAdapter
from app.harness.protocol import HarnessTurnRequest
from app.harness.workspace_guard import WorkspaceGuard
from app.main import app
from app.mcp.icde_mcp_server import ICDEMCPServer
from app.models.dataset import Dataset, DatasetFile, DatasetType
from app.models.project import Project
from app.routers.harness import get_harness_adapter
from app.schemas.chat import MentionRef
from app.services.file_parser import FileParser
from app.services.llm_service import LLMService


def _parse_sse_events(raw_body: str) -> List[Dict[str, Any]]:
    """Parse SSE `data: {...}` frames emitted by FastAPI StreamingResponse."""
    events: List[Dict[str, Any]] = []
    for line in raw_body.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


@pytest.fixture
def harness_fixture(test_db, test_upload_dir, sample_csv_content):
    """Set up synthetic project, RAW dataset, and configured multi-LLM providers."""
    llm_service = LLMService(test_db)
    llm_service.update_setting("openai", api_key="sk-test-openai", model="gpt-4o", enabled=True, is_default=True)
    llm_service.update_setting("claude", api_key="sk-test-claude", model="claude-sonnet-4-20250514", enabled=True)
    llm_service.update_setting("gemini", api_key="AIzaTestGemini", model="gemini-2.0-flash", enabled=True)
    llm_service.update_setting(
        "kimi",
        api_key="sk-test-kimi",
        model="moonshot-v1-32k",
        api_base_url="https://api.moonshot.cn/v1",
        enabled=True,
    )

    project = Project(name="Trial R1 Harness", description="Synthetic clinical project")
    test_db.add(project)
    test_db.commit()

    raw_dir = test_upload_dir / "raw_adsl"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_csv = raw_dir / "adsl.csv"
    raw_csv.write_text(sample_csv_content, encoding="utf-8")

    row_count, col_count, _, col_info_json = FileParser.parse_file(raw_csv)

    raw_ds = Dataset(
        name="ADSL",
        type=DatasetType.RAW,
        project_id=project.id,
        study_name="STUDY-R1",
        version_name="v1.0",
        patient_id_column="SUBJID",
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
        "db": test_db,
        "upload_dir": test_upload_dir,
        "project": project,
        "dataset": raw_ds,
        "raw_csv": raw_csv,
    }


def _build_mock_opencode_http_transport(
    db,
    upload_dir: Path,
    dataset_id: str,
    recorded_requests: List[Dict[str, Any]],
) -> HttpOpenCodeTransport:
    """
    Create an `HttpOpenCodeTransport` wired to an `httpx.MockTransport` that simulates
    `opencode serve` REST + SSE endpoints and invokes the real `ICDEMCPServer` tools!
    """
    mcp_server = ICDEMCPServer.from_session(db, upload_dir=upload_dir)

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method
        body_json = json.loads(request.content.decode("utf-8")) if request.content else None
        recorded_requests.append(
            {
                "method": method,
                "path": path,
                "headers": dict(request.headers),
                "body": body_json,
            }
        )

        if method == "GET" and path == "/session":
            return httpx.Response(200, json=[])

        if method == "POST" and path == "/session":
            return httpx.Response(200, json={"id": "ses_mock_001", "title": body_json.get("title")})

        if method == "POST" and path == "/session/ses_mock_001/message":
            # Execute real MCP calls just as OpenCode would over icde-mcp
            inspect_rpc = mcp_server.handle_rpc(
                {
                    "jsonrpc": "2.0",
                    "id": "c1",
                    "method": "tools/call",
                    "params": {"name": "icde_inspect_dataset", "arguments": {"dataset_id": dataset_id}},
                }
            )
            inspect_out = inspect_rpc["result"]["structuredContent"]

            save_rpc = mcp_server.handle_rpc(
                {
                    "jsonrpc": "2.0",
                    "id": "c2",
                    "method": "tools/call",
                    "params": {
                        "name": "icde_save_script",
                        "arguments": {
                            "name": "fas_derivation_r1",
                            "display_name": "FAS Derivation Script",
                            "description": "Filter RANDFL == 'Y' and PPROTFL != 'Y'",
                            "code": (
                                "import pandas as pd\n"
                                "def transform(df: pd.DataFrame) -> pd.DataFrame:\n"
                                "    return df[(df['RANDFL'] == 'Y') & (df['PPROTFL'] != 'Y')].copy()\n"
                            ),
                        },
                    },
                }
            )
            save_out = save_rpc["result"]["structuredContent"]
            script_id = save_out["script"]["id"]

            derive_rpc = mcp_server.handle_rpc(
                {
                    "jsonrpc": "2.0",
                    "id": "c3",
                    "method": "tools/call",
                    "params": {
                        "name": "icde_derive_dataset",
                        "arguments": {
                            "source_dataset_id": dataset_id,
                            "script_id": script_id,
                            "output_name": "ADSL_FAS",
                        },
                    },
                }
            )
            derive_out = derive_rpc["result"]["structuredContent"]

            approval_rpc = mcp_server.handle_rpc(
                {
                    "jsonrpc": "2.0",
                    "id": "c4",
                    "method": "tools/call",
                    "params": {
                        "name": "icde_request_approval",
                        "arguments": {
                            "action": "confirm_fas_cohort",
                            "title": "Confirm FAS Cohort Criteria",
                            "summary": "Retained 3/5 randomized subjects without protocol deviations.",
                            "options": ["Confirm FAS (n=3)", "Switch to Safety Set", "Reject"],
                        },
                    },
                }
            )
            approval_out = approval_rpc["result"]["structuredContent"]

            sse_frames = [
                {"type": "server.connected", "properties": {}},
                {
                    "type": "message.part.updated",
                    "properties": {
                        "part": {
                            "id": "prt_tool_1",
                            "sessionID": "ses_mock_001",
                            "type": "tool",
                            "callID": "call_inspect_1",
                            "tool": "icde-mcp_icde_inspect_dataset",
                            "state": {
                                "status": "running",
                                "title": "Inspecting @STUDY-R1/ADSL columns",
                                "input": {"dataset_id": dataset_id},
                            },
                        }
                    },
                },
                {
                    "type": "message.part.updated",
                    "properties": {
                        "part": {
                            "id": "prt_tool_1",
                            "sessionID": "ses_mock_001",
                            "type": "tool",
                            "callID": "call_inspect_1",
                            "tool": "icde-mcp_icde_inspect_dataset",
                            "state": {
                                "status": "completed",
                                "title": "Inspected ADSL (5 rows, 6 cols)",
                                "input": {"dataset_id": dataset_id},
                                "output": json.dumps(inspect_out),
                                "time": {"start": 1000, "end": 1018},
                            },
                        }
                    },
                },
                {
                    "type": "message.part.updated",
                    "properties": {
                        "part": {
                            "id": "prt_tool_2",
                            "sessionID": "ses_mock_001",
                            "type": "tool",
                            "callID": "call_save_2",
                            "tool": "icde-mcp_icde_save_script",
                            "state": {
                                "status": "completed",
                                "title": "Saved FAS Derivation Script",
                                "output": json.dumps(save_out),
                            },
                        }
                    },
                },
                {
                    "type": "message.part.updated",
                    "properties": {
                        "part": {
                            "id": "prt_tool_3",
                            "sessionID": "ses_mock_001",
                            "type": "tool",
                            "callID": "call_derive_3",
                            "tool": "icde-mcp_icde_derive_dataset",
                            "state": {
                                "status": "completed",
                                "title": "Derived ADSL_FAS (3 rows)",
                                "output": json.dumps(derive_out),
                            },
                        }
                    },
                },
                {
                    "type": "message.part.updated",
                    "properties": {
                        "part": {
                            "id": "prt_tool_4",
                            "sessionID": "ses_mock_001",
                            "type": "tool",
                            "callID": "call_appr_4",
                            "tool": "icde-mcp_icde_request_approval",
                            "state": {
                                "status": "completed",
                                "title": "Requested PI cohort confirmation",
                                "output": json.dumps(approval_out),
                            },
                        }
                    },
                },
                {
                    "type": "permission.asked",
                    "properties": {
                        "id": "perm_shell_01",
                        "sessionID": "ses_mock_001",
                        "permission": "bash",
                        "title": "Run R verification summary",
                        "patterns": ["Rscript summary.R"],
                    },
                },
                {
                    "type": "message.part.updated",
                    "properties": {
                        "part": {"id": "prt_txt_1", "sessionID": "ses_mock_001", "type": "text"},
                        "delta": "Inspected @ADSL (5 subjects), derived ADSL_FAS (3 subjects), ",
                    },
                },
                {
                    "type": "message.part.updated",
                    "properties": {
                        "part": {"id": "prt_txt_1", "sessionID": "ses_mock_001", "type": "text"},
                        "delta": "and queued cohort criteria for PI confirmation.",
                    },
                },
                {"type": "session.idle", "properties": {"sessionID": "ses_mock_001"}},
            ]
            sse_text = "".join(f"data: {json.dumps(frame)}\n\n" for frame in sse_frames)
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                content=sse_text.encode("utf-8"),
            )

        if method == "POST" and path.startswith("/session/ses_mock_001/permissions/"):
            return httpx.Response(200, json={"ok": True})

        return httpx.Response(404, json={"detail": f"Unhandled mock route {method} {path}"})

    return HttpOpenCodeTransport(
        base_url="http://opencode.mock.local",
        httpx_transport=httpx.MockTransport(handler),
        use_global_event_stream=False,
    )


class TestOpenCodeAdapterMultiProvider:
    """Verify multi-provider execution over mocked `opencode serve` HTTP/SSE wire protocol."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("provider", "expected_oc_provider", "expected_model"),
        [
            ("openai", "openai", "gpt-4o"),
            ("claude", "anthropic", "claude-sonnet-4-20250514"),
            ("gemini", "google", "gemini-2.0-flash"),
            ("kimi", "kimi", "moonshot-v1-32k"),
        ],
    )
    async def test_run_turn_across_all_providers(
        self,
        harness_fixture,
        provider,
        expected_oc_provider,
        expected_model,
    ):
        recorded: List[Dict[str, Any]] = []
        transport = _build_mock_opencode_http_transport(
            harness_fixture["db"],
            harness_fixture["upload_dir"],
            harness_fixture["dataset"].id,
            recorded,
        )
        adapter = OpenCodeHarnessAdapter(
            transport=transport,
            database_url="sqlite:///:memory:",
            upload_dir=harness_fixture["upload_dir"],
        )

        sha_before = WorkspaceGuard.compute_sha256(harness_fixture["raw_csv"])
        result = await adapter.run_turn(
            HarnessTurnRequest(
                message="Inspect @STUDY-R1/ADSL and build FAS cohort",
                provider=provider,
                project_id=harness_fixture["project"].id,
                mentions=[
                    MentionRef(
                        type="dataset",
                        id=harness_fixture["dataset"].id,
                        path="@STUDY-R1/ADSL",
                        name="ADSL",
                    )
                ],
            ),
            harness_fixture["db"],
        )

        assert result.provider == provider
        assert result.model == expected_model
        assert "ADSL_FAS (3 subjects)" in result.content
        assert len(result.pending_approvals) == 2  # MCP clinical checkpoint + OpenCode permission.asked
        assert WorkspaceGuard.compute_sha256(harness_fixture["raw_csv"]) == sha_before

        msg_posts = [r for r in recorded if r["path"].endswith("/message")]
        assert len(msg_posts) == 1
        assert msg_posts[0]["body"]["model"] == {
            "providerID": expected_oc_provider,
            "modelID": expected_model,
        }


class TestHarnessFastAPIEndToEnd:
    """Blackbox FastAPI tests for `/api/harness/*` and `/api/chat/stream`."""

    def test_status_when_opencode_binary_unavailable(self, harness_fixture, monkeypatch):
        monkeypatch.delenv("OPENCODE_SERVER_URL", raising=False)
        monkeypatch.delenv("OPENCODE_BINARY", raising=False)
        monkeypatch.setattr("shutil.which", lambda _: None)

        unavailable_adapter = OpenCodeHarnessAdapter(upload_dir=harness_fixture["upload_dir"])
        app.dependency_overrides[get_db] = lambda: harness_fixture["db"]
        app.dependency_overrides[get_harness_adapter] = lambda: unavailable_adapter
        try:
            client = TestClient(app)
            resp = client.get("/api/harness/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["harness"] == "opencode"
            assert data["available"] is False
            assert data["mode"] == "unavailable"
            assert data["raw_guard_enabled"] is True
            assert data["protected_raw_datasets"] == 1
            assert "icde_derive_dataset" in data["mcp_tools"]
            assert data["diagnostic"]

            # Stream returns structured diagnostic error event instead of crashing
            stream_resp = client.post(
                "/api/harness/stream",
                json={"message": "Inspect ADSL", "provider": "openai"},
            )
            assert stream_resp.status_code == 200
            sse_events = _parse_sse_events(stream_resp.text)
            assert sse_events[0]["type"] == "error"
            assert sse_events[0]["code"] == "OPENCODE_UNAVAILABLE"
        finally:
            app.dependency_overrides.clear()

    def test_full_sse_stream_and_approval_resolution_end_to_end(self, harness_fixture):
        recorded: List[Dict[str, Any]] = []
        transport = _build_mock_opencode_http_transport(
            harness_fixture["db"],
            harness_fixture["upload_dir"],
            harness_fixture["dataset"].id,
            recorded,
        )
        adapter = OpenCodeHarnessAdapter(
            transport=transport,
            database_url="sqlite:///:memory:",
            upload_dir=harness_fixture["upload_dir"],
        )

        app.dependency_overrides[get_db] = lambda: harness_fixture["db"]
        app.dependency_overrides[get_harness_adapter] = lambda: adapter
        sha_before = WorkspaceGuard.compute_sha256(harness_fixture["raw_csv"])

        try:
            client = TestClient(app)

            # 1. Check /api/harness/status with active transport
            status_resp = client.get("/api/harness/status")
            assert status_resp.status_code == 200
            status_json = status_resp.json()
            assert status_json["available"] is True
            assert set(status_json["configured_providers"]) == {"openai", "claude", "gemini", "kimi"}

            # 2. Stream full closed-loop turn over /api/harness/stream
            stream_resp = client.post(
                "/api/harness/stream",
                json={
                    "message": "Read @STUDY-R1/ADSL, derive FAS dataset, and request PI confirmation",
                    "provider": "kimi",
                    "project_id": harness_fixture["project"].id,
                    "mentions": [
                        {
                            "type": "dataset",
                            "id": harness_fixture["dataset"].id,
                            "path": "@STUDY-R1/ADSL",
                            "name": "ADSL",
                        }
                    ],
                },
            )
            assert stream_resp.status_code == 200
            events = _parse_sse_events(stream_resp.text)
            event_types = [e["type"] for e in events]

            assert "tool_call" in event_types
            assert "workspace_event" in event_types
            assert "approval_required" in event_types
            assert "content" in event_types
            assert event_types[-1] == "done"

            ws_names = [e["event_name"] for e in events if e["type"] == "workspace_event"]
            assert "script_saved" in ws_names
            assert "dataset_derived" in ws_names
            assert "lineage_updated" in ws_names

            approvals = [e for e in events if e["type"] == "approval_required"]
            assert len(approvals) == 2

            # 3. Resolve both MCP clinical approval and OpenCode permission approval via API
            clinical_appr = next(a for a in approvals if a["action"] == "confirm_fas_cohort")
            perm_appr = next(a for a in approvals if a["action"] == "bash")

            resolve_clinical = client.post(
                f"/api/harness/approvals/{clinical_appr['approval_id']}",
                json={
                    "decision": "approved",
                    "selected_option": "Confirm FAS (n=3)",
                    "comment": "Approved by PI",
                },
            )
            assert resolve_clinical.status_code == 200
            assert resolve_clinical.json()["status"] == "approved"
            assert resolve_clinical.json()["selected_option"] == "Confirm FAS (n=3)"

            resolve_perm = client.post(
                f"/api/harness/approvals/{perm_appr['approval_id']}",
                json={
                    "decision": "approved",
                    "selected_option": "Always Allow",
                },
            )
            assert resolve_perm.status_code == 200
            assert resolve_perm.json()["status"] == "approved"
            assert any(
                r["path"] == "/session/ses_mock_001/permissions/perm_shell_01"
                and r["body"] == {"response": "always", "remember": True}
                for r in recorded
            )

            # 4. Also verify `/api/chat/stream` with `mode="harness"` routes through adapter
            chat_harness_resp = client.post(
                "/api/chat/stream",
                json={
                    "message": "Run follow-up check on @STUDY-R1/ADSL",
                    "provider": "openai",
                    "mode": "harness",
                },
            )
            assert chat_harness_resp.status_code == 200
            chat_events = _parse_sse_events(chat_harness_resp.text)
            assert any(e["type"] == "tool_call" for e in chat_events)
            assert chat_events[-1]["type"] == "done"

            # 5. Verify HTTP MCP endpoint (`/api/harness/mcp`)
            mcp_http_resp = client.post(
                "/api/harness/mcp",
                json={"jsonrpc": "2.0", "id": 99, "method": "tools/list"},
            )
            assert mcp_http_resp.status_code == 200
            assert len(mcp_http_resp.json()["result"]["tools"]) == 6

            # 6. Verify RAW source file remained byte-for-byte untouched throughout
            assert WorkspaceGuard.compute_sha256(harness_fixture["raw_csv"]) == sha_before
        finally:
            app.dependency_overrides.clear()
