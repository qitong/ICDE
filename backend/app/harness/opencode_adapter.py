"""
Async OpenCode Headless Server (`opencode serve`) client & `ICDEHarnessAdapter` implementation.

Supports:
1. Attaching to an external `OPENCODE_SERVER_URL` via `httpx` async REST + SSE (`/session`,
   `/session/{id}/message`, `/session/{id}/prompt_async`, `/event`, `/session/{id}/permissions/{permId}`).
2. Spawning an ephemeral `opencode serve` subprocess when the `opencode` binary is available on PATH,
   reliably terminating it via `close()` or retaining a bounded session lease while an OpenCode
   `permission.asked` checkpoint awaits PI approval.
3. Full dependency-injected `OpenCodeTransport` / `httpx.AsyncBaseTransport` support for 100%
   deterministic offline testing in CI.
4. Pre-turn OS `0o444`/`0o555` locking + cryptographic SHA-256 verification via `WorkspaceGuard`.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shutil
import socket
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, Set, Tuple, runtime_checkable

import httpx
from sqlalchemy.orm import Session

from app.config import DATABASE_URL, UPLOAD_DIR
from app.mcp.tools import TOOL_DEFINITIONS
from app.models.chat import ChatMessage, Conversation, LLMSetting

from .approval_store import ApprovalStore
from .events import ApprovalCheckpoint, HarnessEvent
from .opencode_config import OpenCodeConfigBuilder, OpenCodeRuntimeBundle
from .protocol import (
    ApprovalDecisionRequest,
    HarnessStatus,
    HarnessTurnRequest,
    HarnessTurnResult,
    ICDEHarnessAdapter,
)
from .workspace_guard import ReadOnlyDatasetViolationError, WorkspaceGuard

logger = logging.getLogger(__name__)

MCP_SERVER_NAME = "icde-mcp"
MAX_ACTIVE_PERMISSION_LEASES = 16
PERMISSION_LEASE_TTL_SECONDS = 600.0


@runtime_checkable
class OpenCodeTransport(Protocol):
    """Pluggable async transport interface talking to `opencode serve`."""

    async def check_health(self) -> bool:
        """Return True if the OpenCode server is reachable."""

    async def create_session(
        self,
        *,
        title: str,
        directory: str,
        env: Dict[str, str],
    ) -> str:
        """Create or allocate an OpenCode session ID."""

    def stream_prompt(
        self,
        *,
        session_id: str,
        prompt: str,
        provider_id: str,
        model_id: str,
        directory: str,
        env: Dict[str, str],
    ) -> AsyncIterator[Dict[str, Any]]:
        """Send user prompt and yield raw OpenCode server events until turn completion."""

    async def respond_permission(
        self,
        *,
        session_id: str,
        permission_id: str,
        response: str,
        remember: bool = False,
    ) -> Dict[str, Any]:
        """Forward a permission approval/rejection (`allow` | `always` | `reject`) to OpenCode."""

    async def close(self) -> None:
        """Release any underlying subprocess or network resources owned by this transport."""


@dataclass
class _ActiveSessionLease:
    """Retains a live `local_binary` transport + workspace bundle while permissions are pending."""

    session_id: str
    transport: OpenCodeTransport
    bundle: Optional[OpenCodeRuntimeBundle]
    pending_permission_ids: Set[str] = field(default_factory=set)
    created_monotonic: float = field(default_factory=time.monotonic)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _build_auth_headers(password: Optional[str] = None, username: str = "opencode") -> Dict[str, str]:
    pw = password if password is not None else os.environ.get("OPENCODE_SERVER_PASSWORD")
    if not pw:
        return {}
    token = base64.b64encode(f"{username}:{pw}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


async def _iter_sse_json(response: httpx.Response) -> AsyncIterator[Dict[str, Any]]:
    """Parse SSE `data: {...}` frames from an `httpx.Response` stream."""
    data_lines: List[str] = []
    async for raw_line in response.aiter_lines():
        line = raw_line.rstrip("\r")
        if not line:
            if data_lines:
                joined = "\n".join(data_lines).strip()
                data_lines.clear()
                if joined and joined != "[DONE]":
                    try:
                        parsed = json.loads(joined)
                        if isinstance(parsed, dict):
                            yield parsed
                    except json.JSONDecodeError:
                        logger.debug("Skipping non-JSON SSE payload: %s", joined[:120])
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    if data_lines:
        joined = "\n".join(data_lines).strip()
        if joined and joined != "[DONE]":
            try:
                parsed = json.loads(joined)
                if isinstance(parsed, dict):
                    yield parsed
            except json.JSONDecodeError:
                pass


class HttpOpenCodeTransport:
    """
    Production HTTP + SSE transport talking to `opencode serve`.

    Can attach to an existing `base_url`, spawn an ephemeral `opencode serve` subprocess
    when `binary_path` is provided, or run against an injected `httpx.AsyncBaseTransport`
    in automated tests.
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        binary_path: Optional[str] = None,
        httpx_transport: Optional[httpx.AsyncBaseTransport] = None,
        timeout: float = 120.0,
        use_global_event_stream: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.binary_path = binary_path
        self._httpx_transport = httpx_transport
        self._timeout = timeout
        self._use_global_event_stream = use_global_event_stream
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._owns_server_process: bool = False

    def _make_client(self, base_url: str, directory: Optional[str] = None) -> httpx.AsyncClient:
        headers = _build_auth_headers()
        if directory:
            headers["x-opencode-directory"] = directory
        return httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            transport=self._httpx_transport,
            timeout=httpx.Timeout(self._timeout),
        )

    async def _ensure_server(self, directory: str, env: Dict[str, str]) -> str:
        if self._owns_server_process and self._proc is not None and self._proc.returncode is not None:
            # Previously spawned subprocess died; reset before respawning
            self._proc = None
            self.base_url = None
            self._owns_server_process = False

        if self.base_url:
            return self.base_url
        if not self.binary_path:
            raise RuntimeError("Neither OPENCODE_SERVER_URL nor 'opencode' binary is available.")

        port = _find_free_port()
        merged_env = {**os.environ, **env}
        proc = await asyncio.create_subprocess_exec(
            self.binary_path,
            "serve",
            "--hostname",
            "127.0.0.1",
            "--port",
            str(port),
            cwd=directory,
            env=merged_env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        url = f"http://127.0.0.1:{port}"
        self._proc = proc
        self._owns_server_process = True
        self.base_url = url

        try:
            # Wait up to 10 seconds for `opencode serve` to listen
            async with self._make_client(url, directory=directory) as client:
                for _ in range(40):
                    if proc.returncode is not None:
                        stderr_bytes = await proc.stderr.read() if proc.stderr else b""
                        raise RuntimeError(
                            f"'opencode serve' exited prematurely (code={proc.returncode}): "
                            f"{stderr_bytes.decode('utf-8', errors='replace')[:300]}"
                        )
                    try:
                        resp = await client.get("/session")
                        if resp.status_code < 500:
                            return url
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.25)

            raise RuntimeError("Timed out waiting for 'opencode serve' HTTP server to start.")
        except Exception:
            await self.close()
            raise

    async def close(self) -> None:
        """Terminate and reap any owned `opencode serve` child process."""
        proc = self._proc
        self._proc = None
        was_owned = self._owns_server_process
        self._owns_server_process = False
        if was_owned:
            self.base_url = None

        if proc is not None:
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        pass

    async def check_health(self) -> bool:
        if self.base_url:
            try:
                async with self._make_client(self.base_url) as client:
                    resp = await client.get("/session")
                    return resp.status_code < 500
            except httpx.HTTPError:
                return False
        return bool(self.binary_path and Path(self.binary_path).exists())

    async def create_session(
        self,
        *,
        title: str,
        directory: str,
        env: Dict[str, str],
    ) -> str:
        url = await self._ensure_server(directory, env)
        async with self._make_client(url, directory=directory) as client:
            resp = await client.post("/session", json={"title": title})
            resp.raise_for_status()
            body = resp.json()
            session_id = body.get("id") or (body.get("data") or {}).get("id")
            if not session_id:
                raise RuntimeError(f"OpenCode /session response missing id: {body}")
            return str(session_id)

    async def stream_prompt(
        self,
        *,
        session_id: str,
        prompt: str,
        provider_id: str,
        model_id: str,
        directory: str,
        env: Dict[str, str],
    ) -> AsyncIterator[Dict[str, Any]]:
        url = await self._ensure_server(directory, env)
        payload = {
            "model": {
                "providerID": provider_id,
                "modelID": model_id,
            },
            "parts": [
                {
                    "type": "text",
                    "text": prompt,
                }
            ],
        }

        if self._use_global_event_stream:
            async for ev in self._stream_via_global_event_bus(
                url=url,
                session_id=session_id,
                payload=payload,
                directory=directory,
            ):
                yield ev
            return

        async with self._make_client(url, directory=directory) as client:
            async with client.stream(
                "POST",
                f"/session/{session_id}/message",
                json=payload,
                headers={"Accept": "text/event-stream, application/json"},
            ) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "text/event-stream" in content_type:
                    async for sse_event in _iter_sse_json(resp):
                        yield sse_event
                else:
                    raw_bytes = await resp.aread()
                    body = json.loads(raw_bytes.decode("utf-8"))
                    if isinstance(body, dict):
                        if "events" in body and isinstance(body["events"], list):
                            for item in body["events"]:
                                if isinstance(item, dict):
                                    yield item
                        elif "parts" in body and isinstance(body["parts"], list):
                            for part in body["parts"]:
                                if isinstance(part, dict):
                                    yield {
                                        "type": "message.part.updated",
                                        "properties": {"part": part},
                                    }
                        else:
                            yield body

    async def _stream_via_global_event_bus(
        self,
        *,
        url: str,
        session_id: str,
        payload: Dict[str, Any],
        directory: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to `GET /event` SSE and trigger `POST /session/{id}/prompt_async`."""
        queue: asyncio.Queue[Optional[Dict[str, Any]]] = asyncio.Queue()
        connected = asyncio.Event()

        async def _listen_events() -> None:
            try:
                async with self._make_client(url, directory=directory) as sse_client:
                    async with sse_client.stream("GET", "/event") as sse_resp:
                        sse_resp.raise_for_status()
                        connected.set()
                        async for ev in _iter_sse_json(sse_resp):
                            ev_type = ev.get("type", "")
                            props = ev.get("properties") or {}
                            ev_session = (
                                props.get("sessionID")
                                or (props.get("part") or {}).get("sessionID")
                                or (props.get("info") or {}).get("sessionID")
                                or ev.get("sessionID")
                            )
                            if ev_session and ev_session != session_id:
                                continue
                            await queue.put(ev)
                            if ev_type in ("session.idle", "session.error", "done"):
                                break
                            if ev_type == "session.status":
                                status_obj = props.get("status") or {}
                                if status_obj.get("type") == "idle":
                                    break
            finally:
                connected.set()
                await queue.put(None)

        listener_task = asyncio.create_task(_listen_events())
        try:
            await asyncio.wait_for(connected.wait(), timeout=5.0)
            async with self._make_client(url, directory=directory) as post_client:
                resp = await post_client.post(f"/session/{session_id}/prompt_async", json=payload)
                if resp.status_code in (404, 405):
                    resp = await post_client.post(f"/session/{session_id}/message", json=payload)
                resp.raise_for_status()

            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            if not listener_task.done():
                listener_task.cancel()
                try:
                    await listener_task
                except asyncio.CancelledError:
                    pass

    async def respond_permission(
        self,
        *,
        session_id: str,
        permission_id: str,
        response: str,
        remember: bool = False,
    ) -> Dict[str, Any]:
        if not self.base_url:
            return {"forwarded": False, "reason": "No active OpenCode server URL"}
        async with self._make_client(self.base_url) as client:
            resp = await client.post(
                f"/session/{session_id}/permissions/{permission_id}",
                json={"response": response, "remember": remember},
            )
            resp.raise_for_status()
            if not resp.content:
                return {"forwarded": True}
            return resp.json()


class OpenCodeHarnessAdapter(ICDEHarnessAdapter):
    """
    Unified `ICDEHarnessAdapter` backed by OpenCode Headless Server + `icde-mcp` + `WorkspaceGuard`.
    """

    def __init__(
        self,
        *,
        server_url: Optional[str] = None,
        binary_path: Optional[str] = None,
        transport: Optional[OpenCodeTransport] = None,
        database_url: Optional[str] = None,
        upload_dir: Optional[Path] = None,
        mcp_http_url: Optional[str] = None,
    ) -> None:
        self._explicit_server_url = server_url
        self._explicit_binary_path = binary_path
        self._injected_transport = transport
        self._database_url = database_url
        self._upload_dir = upload_dir
        self._mcp_http_url = mcp_http_url
        self._active_leases: Dict[str, _ActiveSessionLease] = {}

    def _resolve_runtime_target(self) -> Tuple[str, Optional[str], Optional[str], Optional[OpenCodeTransport]]:
        """
        Determine runtime mode: `(mode, server_url, binary_path, transport)`.
        """
        if self._injected_transport is not None:
            return "mock_transport", self._explicit_server_url, self._explicit_binary_path, self._injected_transport

        server_url = self._explicit_server_url or os.environ.get("OPENCODE_SERVER_URL")
        if server_url:
            transport = HttpOpenCodeTransport(
                base_url=server_url,
                use_global_event_stream=True,
            )
            return "remote_server", server_url, None, transport

        binary = self._explicit_binary_path or os.environ.get("OPENCODE_BINARY") or shutil.which("opencode")
        if binary:
            transport = HttpOpenCodeTransport(
                binary_path=binary,
                use_global_event_stream=True,
            )
            return "local_binary", None, binary, transport

        return "unavailable", None, None, None

    @staticmethod
    async def _close_transport(transport: Optional[OpenCodeTransport]) -> None:
        if transport is None:
            return
        close_fn = getattr(transport, "close", None)
        if callable(close_fn):
            result = close_fn()
            if asyncio.iscoroutine(result):
                await result

    async def _release_lease(self, session_id: str) -> None:
        lease = self._active_leases.pop(session_id, None)
        if lease is None:
            return
        try:
            await self._close_transport(lease.transport)
        finally:
            if lease.bundle is not None:
                lease.bundle.cleanup()

    async def _prune_leases(self) -> None:
        now = time.monotonic()
        expired = [
            sid
            for sid, lease in self._active_leases.items()
            if (now - lease.created_monotonic) > PERMISSION_LEASE_TTL_SECONDS
        ]
        for sid in expired:
            await self._release_lease(sid)

        while len(self._active_leases) >= MAX_ACTIVE_PERMISSION_LEASES:
            oldest_sid = min(
                self._active_leases,
                key=lambda k: self._active_leases[k].created_monotonic,
            )
            await self._release_lease(oldest_sid)

    async def close_all_leases(self) -> None:
        """Close all retained `local_binary` permission leases and clean up bundles."""
        for sid in list(self._active_leases.keys()):
            await self._release_lease(sid)

    async def health_status(self, db: Session) -> HarnessStatus:
        mode, server_url, binary_path, transport = self._resolve_runtime_target()
        guard = WorkspaceGuard(db, workspace_root=self._upload_dir or UPLOAD_DIR)
        raw_count = len(guard.list_raw_datasets())

        configured_providers = [
            row.provider
            for row in db.query(LLMSetting).filter(LLMSetting.enabled == True).all()  # noqa: E712
            if row.api_key_encrypted
        ]

        available = False
        diagnostic: Optional[str] = None
        if transport is not None:
            available = await transport.check_health()
            if not available and mode == "remote_server":
                diagnostic = f"OpenCode server at {server_url} is unreachable."
        else:
            diagnostic = (
                "OpenCode binary ('opencode') is not found on PATH and OPENCODE_SERVER_URL is not set. "
                "Start 'opencode serve' and set OPENCODE_SERVER_URL, or install the OpenCode CLI."
            )

        return HarnessStatus(
            harness="opencode",
            available=available,
            mode=mode,  # type: ignore[arg-type]
            server_url=server_url,
            binary_path=binary_path,
            mcp_server=MCP_SERVER_NAME,
            mcp_tools=[tool["name"] for tool in TOOL_DEFINITIONS],
            raw_guard_enabled=True,
            protected_raw_datasets=raw_count,
            configured_providers=configured_providers,
            diagnostic=diagnostic,
        )

    async def stream_turn(
        self,
        request: HarnessTurnRequest,
        db: Session,
    ) -> AsyncIterator[HarnessEvent]:
        """
        Execute an agent turn and yield standardized `HarnessEvent` chunks.
        """
        await self._prune_leases()
        guard = WorkspaceGuard(db, workspace_root=self._upload_dir or UPLOAD_DIR)
        approval_store = ApprovalStore(db)

        # 1. Pre-turn cryptographic snapshot AND OS-level read-only lock (0o444 files + 0o555 dirs)
        raw_snapshot = guard.snapshot_raw_files()
        guard.lock_raw_dataset_files()

        # 2. Get or create Conversation + persist user & placeholder assistant messages
        conversation: Optional[Conversation] = None
        if request.conversation_id:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == request.conversation_id)
                .first()
            )
        if not conversation:
            conversation = Conversation(project_id=request.project_id)
            db.add(conversation)
            db.commit()
            db.refresh(conversation)

        existing_msg_count = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation.id)
            .count()
        )

        user_msg = ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content=request.message,
            mentions=(
                json.dumps([m.model_dump() for m in request.mentions], ensure_ascii=False)
                if request.mentions
                else None
            ),
        )
        db.add(user_msg)
        db.commit()

        assistant_msg = ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content="",
            provider=request.provider,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        mode, _, _, transport = self._resolve_runtime_target()
        if transport is None:
            diag = (
                "OpenCode runtime is unavailable: 'opencode' binary not found on PATH and "
                "OPENCODE_SERVER_URL is not configured."
            )
            assistant_msg.status = "error"
            assistant_msg.error_message = diag
            db.commit()
            yield HarnessEvent.error_event(
                diag,
                code="OPENCODE_UNAVAILABLE",
                conversation_id=conversation.id,
                message_id=assistant_msg.id,
            )
            return

        config_builder = OpenCodeConfigBuilder(
            db,
            database_url=self._database_url or DATABASE_URL,
            upload_dir=self._upload_dir or UPLOAD_DIR,
            mcp_http_url=self._mcp_http_url,
        )

        bundle: Optional[OpenCodeRuntimeBundle] = None
        session_id: Optional[str] = None
        pending_permission_ids: Set[str] = set()
        retain_lease = False
        full_content_parts: List[str] = []
        seen_part_lengths: Dict[str, int] = {}
        emitted_tool_states: Set[Tuple[str, str]] = set()
        emitted_side_events: Set[str] = set()

        try:
            bundle = config_builder.build(
                provider_name=request.provider,
                project_id=request.project_id,
                mentions=request.mentions,
                require_api_key=(mode != "mock_transport"),
            )
            assistant_msg.provider = bundle.icde_provider
            assistant_msg.model = bundle.model_name

            session_id = request.session_id or await transport.create_session(
                title=conversation.title or request.message[:50],
                directory=str(bundle.workspace_dir),
                env=bundle.env,
            )

            enriched_prompt = self._build_turn_prompt(request)

            async for raw_event in transport.stream_prompt(
                session_id=session_id,
                prompt=enriched_prompt,
                provider_id=bundle.opencode_provider,
                model_id=bundle.model_name,
                directory=str(bundle.workspace_dir),
                env=bundle.env,
            ):
                for translated in self._translate_raw_event(
                    raw_event,
                    conversation_id=conversation.id,
                    message_id=assistant_msg.id,
                    session_id=session_id,
                    approval_store=approval_store,
                    seen_part_lengths=seen_part_lengths,
                    emitted_tool_states=emitted_tool_states,
                    emitted_side_events=emitted_side_events,
                    pending_permission_ids=pending_permission_ids,
                ):
                    if translated.type in ("content", "text_delta") and translated.content:
                        full_content_parts.append(translated.content)
                    yield translated

            # 3. Verify post-turn RAW dataset immutability
            guard.verify_raw_files_unchanged(raw_snapshot)

            assistant_msg.content = "".join(full_content_parts)
            assistant_msg.status = "success"
            if not conversation.title and existing_msg_count == 0:
                conversation.title = request.message[:50] + (
                    "..." if len(request.message) > 50 else ""
                )
            db.commit()

            # Retain live subprocess + workspace bundle ONLY if an OpenCode session permission
            # checkpoint is pending in local_binary (or owned subprocess) mode.
            owns_proc = bool(getattr(transport, "_owns_server_process", False))
            if session_id and pending_permission_ids and (mode == "local_binary" or owns_proc):
                self._active_leases[session_id] = _ActiveSessionLease(
                    session_id=session_id,
                    transport=transport,
                    bundle=bundle,
                    pending_permission_ids=set(pending_permission_ids),
                )
                retain_lease = True

            yield HarnessEvent.done_event(
                conversation_id=conversation.id,
                message_id=assistant_msg.id,
            )

        except ReadOnlyDatasetViolationError as exc:
            assistant_msg.status = "error"
            assistant_msg.error_message = str(exc)
            db.commit()
            yield HarnessEvent.error_event(
                str(exc),
                code="RAW_DATASET_VIOLATION",
                conversation_id=conversation.id,
                message_id=assistant_msg.id,
            )
        except ValueError as exc:
            assistant_msg.status = "error"
            assistant_msg.error_message = str(exc)
            db.commit()
            yield HarnessEvent.error_event(
                str(exc),
                code="CONFIGURATION_ERROR",
                conversation_id=conversation.id,
                message_id=assistant_msg.id,
            )
        except Exception as exc:
            logger.error("OpenCode harness stream error: %s", exc)
            assistant_msg.status = "error"
            assistant_msg.error_message = str(exc)
            db.commit()
            yield HarnessEvent.error_event(
                str(exc),
                code="HARNESS_RUNTIME_ERROR",
                conversation_id=conversation.id,
                message_id=assistant_msg.id,
            )
        finally:
            if not retain_lease:
                try:
                    await self._close_transport(transport)
                finally:
                    if bundle is not None:
                        bundle.cleanup()

    async def run_turn(
        self,
        request: HarnessTurnRequest,
        db: Session,
    ) -> HarnessTurnResult:
        """Execute a turn and collect streamed `HarnessEvent` items into `HarnessTurnResult`."""
        events: List[HarnessEvent] = []
        text_chunks: List[str] = []
        conversation_id = request.conversation_id or ""
        message_id = ""
        approval_store = ApprovalStore(db)
        pending_approvals: List[ApprovalCheckpoint] = []

        async for ev in self.stream_turn(request, db):
            events.append(ev)
            if ev.conversation_id:
                conversation_id = ev.conversation_id
            if ev.message_id:
                message_id = ev.message_id
            if ev.type in ("content", "text_delta") and ev.content:
                text_chunks.append(ev.content)
            elif ev.type == "approval_required" and ev.approval_id:
                cp = approval_store.get(ev.approval_id)
                if cp:
                    pending_approvals.append(cp)

        msg_row = (
            db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
            if message_id
            else None
        )
        return HarnessTurnResult(
            conversation_id=conversation_id,
            message_id=message_id,
            content="".join(text_chunks),
            provider=msg_row.provider if msg_row else request.provider,
            model=msg_row.model if msg_row else None,
            events=events,
            pending_approvals=pending_approvals,
        )

    async def resolve_approval(
        self,
        approval_id: str,
        decision: ApprovalDecisionRequest,
        db: Session,
    ) -> ApprovalCheckpoint:
        """Resolve a pending `ApprovalCheckpoint` and forward to OpenCode permissions API if linked."""
        store = ApprovalStore(db)
        checkpoint = store.resolve(
            approval_id,
            decision=decision.decision,
            selected_option=decision.selected_option,
            comment=decision.comment,
        )

        if checkpoint.session_id and checkpoint.permission_id:
            lease = self._active_leases.get(checkpoint.session_id)
            target_transport: Optional[OpenCodeTransport] = (
                lease.transport if lease is not None else self._resolve_runtime_target()[3]
            )

            if target_transport is not None:
                oc_response = "allow" if decision.decision == "approved" else "reject"
                if (
                    decision.decision == "approved"
                    and decision.selected_option
                    and "always" in decision.selected_option.lower()
                ):
                    oc_response = "always"
                try:
                    await target_transport.respond_permission(
                        session_id=checkpoint.session_id,
                        permission_id=checkpoint.permission_id,
                        response=oc_response,
                        remember=(oc_response == "always"),
                    )
                except Exception as exc:
                    logger.warning("Failed to forward permission resolution to OpenCode: %s", exc)
                finally:
                    if lease is not None:
                        lease.pending_permission_ids.discard(checkpoint.permission_id)
                        if not lease.pending_permission_ids:
                            await self._release_lease(checkpoint.session_id)

        return checkpoint

    @staticmethod
    def _build_turn_prompt(request: HarnessTurnRequest) -> str:
        if not request.mentions:
            return request.message
        mention_lines = [
            f"- [{m.type}] {m.path} (id={m.id})"
            for m in request.mentions
        ]
        return (
            f"{request.message}\n\n"
            f"[Referenced Workspace Items]\n" + "\n".join(mention_lines)
        )

    @staticmethod
    def _normalize_tool_name(raw_name: str) -> str:
        for prefix in ("icde-mcp_", "icde-mcp:", "icde-mcp."):
            if raw_name.startswith(prefix):
                return raw_name[len(prefix):]
        return raw_name

    def _translate_raw_event(
        self,
        raw_event: Dict[str, Any],
        *,
        conversation_id: str,
        message_id: str,
        session_id: str,
        approval_store: ApprovalStore,
        seen_part_lengths: Dict[str, int],
        emitted_tool_states: Set[Tuple[str, str]],
        emitted_side_events: Set[str],
        pending_permission_ids: Optional[Set[str]] = None,
    ) -> List[HarnessEvent]:
        """Translate OpenCode SSE / REST payloads into standardized `HarnessEvent` frames."""
        out: List[HarnessEvent] = []
        ev_type = str(raw_event.get("type") or "")
        props = raw_event.get("properties") if isinstance(raw_event.get("properties"), dict) else {}

        # Ignore transport-level heartbeats / idle markers (caller handles loop termination)
        if ev_type in ("server.connected", "server.heartbeat", "session.idle", "session.status", "done"):
            return out

        # 1. Direct standardized events (e.g. from test transports or direct relays)
        if ev_type in ("content", "text_delta"):
            text_val = raw_event.get("content") or raw_event.get("delta") or props.get("delta") or ""
            if text_val:
                out.append(
                    HarnessEvent.content_chunk(
                        str(text_val),
                        conversation_id=conversation_id,
                        message_id=message_id,
                    )
                )
            return out

        if ev_type == "tool_call":
            call_id = str(raw_event.get("call_id") or f"call_{uuid.uuid4().hex[:8]}")
            tool_name = self._normalize_tool_name(str(raw_event.get("tool_name") or "tool"))
            status_raw = str(raw_event.get("status") or "started")
            status_norm = (
                "completed"
                if status_raw == "completed"
                else ("error" if status_raw in ("error", "failed") else "started")
            )
            state_key = (call_id, status_norm)
            if state_key not in emitted_tool_states:
                emitted_tool_states.add(state_key)
                output_val = raw_event.get("output")
                out.append(
                    HarnessEvent.tool_call_event(
                        call_id=call_id,
                        tool_name=tool_name,
                        status=status_norm,  # type: ignore[arg-type]
                        summary=str(raw_event.get("summary") or f"{tool_name} ({status_norm})"),
                        arguments=raw_event.get("arguments"),
                        output=self._strip_internal_events(output_val),
                        duration_ms=raw_event.get("duration_ms"),
                        conversation_id=conversation_id,
                        message_id=message_id,
                    )
                )
                out.extend(
                    self._extract_embedded_mcp_events(
                        output_val,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        emitted_side_events=emitted_side_events,
                    )
                )
            return out

        if ev_type == "workspace_event":
            ev_name = raw_event.get("event_name")
            if ev_name:
                dedup_key = json.dumps(
                    [ev_name, raw_event.get("dataset_id"), raw_event.get("script_id")],
                    sort_keys=True,
                )
                if dedup_key not in emitted_side_events:
                    emitted_side_events.add(dedup_key)
                    out.append(
                        HarnessEvent.workspace_event_chunk(
                            event_name=ev_name,
                            dataset_id=raw_event.get("dataset_id"),
                            script_id=raw_event.get("script_id"),
                            payload=raw_event.get("payload"),
                            conversation_id=conversation_id,
                            message_id=message_id,
                        )
                    )
            return out

        if ev_type == "approval_required":
            appr_id = raw_event.get("approval_id")
            perm_id_opt = raw_event.get("permission_id")
            existing_cp = approval_store.get(str(appr_id)) if appr_id else None
            if existing_cp is None:
                existing_cp = approval_store.create(
                    approval_id=str(appr_id) if appr_id else None,
                    action=str(raw_event.get("action") or "clinical_confirmation"),
                    title=str(raw_event.get("title") or "Confirmation Required"),
                    summary=str(raw_event.get("summary") or ""),
                    options=raw_event.get("options") or ["Approve", "Reject"],
                    conversation_id=conversation_id,
                    session_id=session_id,
                    permission_id=str(perm_id_opt) if perm_id_opt else None,
                )
            if existing_cp.permission_id and pending_permission_ids is not None:
                pending_permission_ids.add(existing_cp.permission_id)
            dedup_key = f"approval:{existing_cp.approval_id}"
            if dedup_key not in emitted_side_events:
                emitted_side_events.add(dedup_key)
                out.append(
                    HarnessEvent.approval_required_event(
                        existing_cp,
                        conversation_id=conversation_id,
                        message_id=message_id,
                    )
                )
            return out

        # 2. OpenCode native `message.part.updated` events
        if ev_type == "message.part.updated":
            part = props.get("part") if isinstance(props.get("part"), dict) else {}
            part_type = part.get("type")
            part_id = str(part.get("id") or "default_part")

            if part_type == "text":
                delta = props.get("delta")
                if isinstance(delta, str) and delta:
                    seen_part_lengths[part_id] = seen_part_lengths.get(part_id, 0) + len(delta)
                    out.append(
                        HarnessEvent.content_chunk(
                            delta,
                            conversation_id=conversation_id,
                            message_id=message_id,
                        )
                    )
                else:
                    full_text = str(part.get("text") or "")
                    prev_len = seen_part_lengths.get(part_id, 0)
                    if len(full_text) > prev_len:
                        new_slice = full_text[prev_len:]
                        seen_part_lengths[part_id] = len(full_text)
                        out.append(
                            HarnessEvent.content_chunk(
                                new_slice,
                                conversation_id=conversation_id,
                                message_id=message_id,
                            )
                        )

            elif part_type == "tool":
                call_id = str(part.get("callID") or part.get("id") or f"call_{uuid.uuid4().hex[:8]}")
                raw_tool_name = str(part.get("tool") or "tool")
                tool_name = self._normalize_tool_name(raw_tool_name)
                state = part.get("state") if isinstance(part.get("state"), dict) else {}
                raw_status = str(state.get("status") or "running")
                if raw_status in ("pending", "running", "started"):
                    norm_status = "started"
                elif raw_status == "completed":
                    norm_status = "completed"
                else:
                    norm_status = "error"

                state_key = (call_id, norm_status)
                if state_key not in emitted_tool_states:
                    emitted_tool_states.add(state_key)
                    raw_output = state.get("output") if norm_status == "completed" else state.get("error")
                    parsed_output: Any = raw_output
                    if isinstance(raw_output, str):
                        try:
                            parsed_output = json.loads(raw_output)
                        except json.JSONDecodeError:
                            parsed_output = raw_output

                    title = state.get("title") or f"{tool_name} ({norm_status})"
                    time_info = state.get("time") if isinstance(state.get("time"), dict) else {}
                    duration_ms: Optional[int] = None
                    if "start" in time_info and "end" in time_info:
                        try:
                            duration_ms = max(0, int(time_info["end"]) - int(time_info["start"]))
                        except (TypeError, ValueError):
                            duration_ms = None

                    out.append(
                        HarnessEvent.tool_call_event(
                            call_id=call_id,
                            tool_name=tool_name,
                            status=norm_status,  # type: ignore[arg-type]
                            summary=str(title),
                            arguments=state.get("input") if isinstance(state.get("input"), dict) else None,
                            output=self._strip_internal_events(parsed_output),
                            duration_ms=duration_ms,
                            conversation_id=conversation_id,
                            message_id=message_id,
                        )
                    )
                    if norm_status == "completed":
                        out.extend(
                            self._extract_embedded_mcp_events(
                                parsed_output,
                                conversation_id=conversation_id,
                                message_id=message_id,
                                emitted_side_events=emitted_side_events,
                            )
                        )
            return out

        # 3. OpenCode native `permission.asked` / `permission.updated` events
        if ev_type in ("permission.asked", "permission.updated"):
            perm_id = str(props.get("id") or f"perm_{uuid.uuid4().hex[:8]}")
            perm_action = str(props.get("permission") or props.get("type") or "permission_request")
            perm_title = str(props.get("title") or f"Approve {perm_action}")
            patterns = props.get("patterns") or props.get("pattern") or []
            summary = (
                f"OpenCode requested permission '{perm_action}'"
                + (f" for {patterns}" if patterns else "")
            )
            checkpoint = approval_store.create(
                action=perm_action,
                title=perm_title,
                summary=summary,
                options=["Approve", "Always Allow", "Reject"],
                conversation_id=conversation_id,
                session_id=session_id,
                permission_id=perm_id,
            )
            if pending_permission_ids is not None:
                pending_permission_ids.add(perm_id)
            dedup_key = f"approval:{checkpoint.approval_id}"
            if dedup_key not in emitted_side_events:
                emitted_side_events.add(dedup_key)
                out.append(
                    HarnessEvent.approval_required_event(
                        checkpoint,
                        conversation_id=conversation_id,
                        message_id=message_id,
                    )
                )
            return out

        # 4. OpenCode native `session.error` / `error`
        if ev_type in ("session.error", "error"):
            err_obj = props.get("error") or raw_event.get("error") or "Unknown OpenCode session error"
            if isinstance(err_obj, dict):
                err_msg = str(err_obj.get("message") or err_obj.get("name") or err_obj)
            else:
                err_msg = str(err_obj)
            out.append(
                HarnessEvent.error_event(
                    err_msg,
                    code=str(raw_event.get("code") or "OPENCODE_SESSION_ERROR"),
                    conversation_id=conversation_id,
                    message_id=message_id,
                )
            )
            return out

        return out

    @staticmethod
    def _strip_internal_events(output: Any) -> Any:
        if isinstance(output, dict) and "_icde_events" in output:
            return {k: v for k, v in output.items() if k != "_icde_events"}
        return output

    @staticmethod
    def _extract_embedded_mcp_events(
        output: Any,
        *,
        conversation_id: str,
        message_id: str,
        emitted_side_events: Set[str],
    ) -> List[HarnessEvent]:
        """Extract `_icde_events` emitted by `icde-mcp` tool results into SSE events."""
        payload_dict: Optional[Dict[str, Any]] = None
        if isinstance(output, dict):
            payload_dict = output
        elif isinstance(output, str):
            try:
                parsed = json.loads(output)
                if isinstance(parsed, dict):
                    payload_dict = parsed
            except json.JSONDecodeError:
                payload_dict = None

        if not payload_dict:
            return []

        # Unwrap MCP tools/call `structuredContent` if present
        if "structuredContent" in payload_dict and isinstance(payload_dict["structuredContent"], dict):
            payload_dict = payload_dict["structuredContent"]

        raw_events = payload_dict.get("_icde_events")
        if not isinstance(raw_events, list):
            return []

        extracted: List[HarnessEvent] = []
        for item in raw_events:
            if not isinstance(item, dict) or "type" not in item:
                continue
            dedup_key = json.dumps(
                [
                    item.get("type"),
                    item.get("approval_id"),
                    item.get("event_name"),
                    item.get("dataset_id"),
                    item.get("script_id"),
                ],
                sort_keys=True,
            )
            if dedup_key in emitted_side_events:
                continue
            emitted_side_events.add(dedup_key)

            merged = {
                **item,
                "conversation_id": conversation_id,
                "message_id": message_id,
            }
            extracted.append(HarnessEvent(**merged))
        return extracted
