"""Ephemeral OpenCode runtime configuration (`opencode.json` + `AGENTS.md`) builder."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import DATABASE_URL, UPLOAD_DIR
from app.models.chat import LLMSetting
from app.schemas.chat import MentionRef
from app.services.llm_service import LLMService
from .workspace_guard import WorkspaceGuard


DEFAULT_KIMI_BASE_URL = "https://api.moonshot.cn/v1"


@dataclass(frozen=True)
class ProviderSpec:
    """Mapping from ICDE provider identifier to OpenCode provider and env variable."""

    icde_provider: str
    opencode_provider: str
    env_var: str
    default_model: str
    default_base_url: Optional[str] = None
    npm_package: Optional[str] = None
    extra_env_vars: tuple[str, ...] = ()


PROVIDER_SPECS: Dict[str, ProviderSpec] = {
    "openai": ProviderSpec(
        icde_provider="openai",
        opencode_provider="openai",
        env_var="OPENAI_API_KEY",
        default_model="gpt-4o",
    ),
    "claude": ProviderSpec(
        icde_provider="claude",
        opencode_provider="anthropic",
        env_var="ANTHROPIC_API_KEY",
        default_model="claude-sonnet-4-20250514",
    ),
    "anthropic": ProviderSpec(
        icde_provider="claude",
        opencode_provider="anthropic",
        env_var="ANTHROPIC_API_KEY",
        default_model="claude-sonnet-4-20250514",
    ),
    "gemini": ProviderSpec(
        icde_provider="gemini",
        opencode_provider="google",
        env_var="GOOGLE_GENERATIVE_AI_API_KEY",
        default_model="gemini-2.0-flash",
        extra_env_vars=("GEMINI_API_KEY",),
    ),
    "google": ProviderSpec(
        icde_provider="gemini",
        opencode_provider="google",
        env_var="GOOGLE_GENERATIVE_AI_API_KEY",
        default_model="gemini-2.0-flash",
        extra_env_vars=("GEMINI_API_KEY",),
    ),
    "kimi": ProviderSpec(
        icde_provider="kimi",
        opencode_provider="kimi",
        env_var="MOONSHOT_API_KEY",
        default_model="moonshot-v1-32k",
        default_base_url=DEFAULT_KIMI_BASE_URL,
        npm_package="@ai-sdk/openai-compatible",
    ),
    "moonshot": ProviderSpec(
        icde_provider="kimi",
        opencode_provider="kimi",
        env_var="MOONSHOT_API_KEY",
        default_model="moonshot-v1-32k",
        default_base_url=DEFAULT_KIMI_BASE_URL,
        npm_package="@ai-sdk/openai-compatible",
    ),
}


@dataclass
class OpenCodeRuntimeBundle:
    """Ephemeral session configuration bundle for `opencode serve`."""

    workspace_dir: Path
    config_path: Path
    agents_md_path: Path
    config: Dict[str, Any]
    env: Dict[str, str] = field(repr=False)
    icde_provider: str = "openai"
    opencode_provider: str = "openai"
    model_name: str = "gpt-4o"
    opencode_model_id: str = "openai/gpt-4o"
    raw_protected_paths: List[str] = field(default_factory=list)
    _owns_workspace_dir: bool = True

    def cleanup(self) -> None:
        """Remove ephemeral workspace directory if created by builder."""
        if self._owns_workspace_dir and self.workspace_dir.exists():
            shutil.rmtree(self.workspace_dir, ignore_errors=True)


class OpenCodeConfigBuilder:
    """
    Generates ephemeral `opencode.json` and `AGENTS.md` files for an ICDE session.

    Guarantees:
    - Decrypted API keys exist ONLY in `bundle.env` (memory) and are NEVER written
      to `opencode.json` or `AGENTS.md`.
    - `RAW` dataset directories and files are explicitly marked read-only (`deny` on
      `edit`/`write` and destructive shell rules) and registered with `icde-mcp`.
    """

    def __init__(
        self,
        db: Session,
        *,
        database_url: Optional[str] = None,
        upload_dir: Optional[Path] = None,
        mcp_http_url: Optional[str] = None,
        allow_env_fallback: bool = False,
    ) -> None:
        self.db = db
        self.llm_service = LLMService(db)
        self.guard = WorkspaceGuard(db)
        self.database_url = database_url or DATABASE_URL
        self.upload_dir = Path(upload_dir or UPLOAD_DIR).resolve()
        self.mcp_http_url = mcp_http_url
        self.allow_env_fallback = allow_env_fallback

    def _resolve_setting(self, provider_name: Optional[str]) -> tuple[ProviderSpec, Optional[LLMSetting], Optional[str]]:
        requested = (provider_name or self.llm_service.get_default_provider() or "openai").lower()
        spec = PROVIDER_SPECS.get(requested)
        if not spec:
            raise ValueError(f"Unsupported LLM provider for OpenCode harness: {requested}")

        setting = (
            self.db.query(LLMSetting)
            .filter(LLMSetting.provider == spec.icde_provider)
            .first()
        )
        if setting and not setting.enabled:
            raise ValueError(f"Provider is disabled: {spec.icde_provider}")

        decrypted_key: Optional[str] = None
        if setting and setting.api_key_encrypted:
            decrypted_key = self.llm_service._decrypt_api_key(setting.api_key_encrypted)
        elif self.allow_env_fallback:
            decrypted_key = os.environ.get(spec.env_var)

        return spec, setting, decrypted_key

    def build(
        self,
        *,
        provider_name: Optional[str] = None,
        project_id: Optional[str] = None,
        mentions: Optional[List[MentionRef]] = None,
        target_dir: Optional[Path] = None,
        require_api_key: bool = True,
    ) -> OpenCodeRuntimeBundle:
        """
        Build runtime `opencode.json`, `AGENTS.md`, and environment map.
        """
        spec, setting, decrypted_key = self._resolve_setting(provider_name)
        if require_api_key and not decrypted_key:
            raise ValueError(f"API key not configured for provider: {spec.icde_provider}")

        model_name = (setting.model if setting and setting.model else spec.default_model).strip()
        if "/" in model_name:
            opencode_model_id = model_name
            bare_model_name = model_name.split("/", 1)[1]
        else:
            bare_model_name = model_name
            opencode_model_id = f"{spec.opencode_provider}/{bare_model_name}"

        base_url = (
            setting.api_base_url.strip()
            if setting and setting.api_base_url
            else spec.default_base_url
        )

        owns_dir = target_dir is None
        workspace_dir = (
            Path(target_dir).resolve()
            if target_dir is not None
            else Path(tempfile.mkdtemp(prefix="icde_opencode_"))
        )
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Collect RAW dataset paths for OpenCode permission rules
        raw_paths = sorted({str(path) for _, path in self.guard.get_protected_raw_roots()})

        edit_permissions: Dict[str, str] = {"*": "allow"}
        bash_permissions: Dict[str, str] = {
            "*": "ask",
            "rm *": "deny",
            "mv *": "deny",
            "chmod *": "deny",
        }
        for raw_path in raw_paths:
            edit_permissions[raw_path] = "deny"
            edit_permissions[f"{raw_path}/*"] = "deny"
            edit_permissions[f"{raw_path}/**"] = "deny"
            bash_permissions[f"*{raw_path}*"] = "deny"

        provider_options: Dict[str, Any] = {
            "apiKey": f"{{env:{spec.env_var}}}",
        }
        if base_url:
            provider_options["baseURL"] = base_url

        provider_entry: Dict[str, Any] = {
            "options": provider_options,
        }
        if spec.npm_package:
            provider_entry["npm"] = spec.npm_package
            provider_entry["name"] = setting.display_name if setting else spec.icde_provider.title()
            provider_entry["models"] = {
                bare_model_name: {"name": bare_model_name},
            }

        backend_root = Path(__file__).resolve().parents[2]
        if self.mcp_http_url:
            mcp_entry: Dict[str, Any] = {
                "type": "remote",
                "url": self.mcp_http_url,
                "enabled": True,
            }
        else:
            mcp_entry = {
                "type": "local",
                "command": [sys.executable, "-m", "app.mcp.icde_mcp_server"],
                "enabled": True,
                "environment": {
                    "PYTHONPATH": str(backend_root),
                    "DATABASE_URL": "{env:ICDE_DATABASE_URL}",
                    "ICDE_UPLOAD_DIR": "{env:ICDE_UPLOAD_DIR}",
                },
            }

        config_dict: Dict[str, Any] = {
            "$schema": "https://opencode.ai/config.json",
            "model": opencode_model_id,
            "provider": {
                spec.opencode_provider: provider_entry,
            },
            "mcp": {
                "icde-mcp": mcp_entry,
            },
            "permission": {
                "edit": edit_permissions,
                "bash": bash_permissions,
                "icde-mcp_*": "allow",
            },
        }

        agents_md = self._build_agents_markdown(
            project_id=project_id,
            mentions=mentions or [],
            raw_paths=raw_paths,
        )

        config_json = json.dumps(config_dict, indent=2, ensure_ascii=False)

        # Strict hygiene assertion: plaintext API keys must never be serialized to disk
        if decrypted_key:
            if decrypted_key in config_json or decrypted_key in agents_md:
                raise RuntimeError("Security violation: plaintext API key leaked into generated config!")

        config_path = workspace_dir / "opencode.json"
        agents_md_path = workspace_dir / "AGENTS.md"
        config_path.write_text(config_json, encoding="utf-8")
        agents_md_path.write_text(agents_md, encoding="utf-8")

        runtime_env: Dict[str, str] = {
            "ICDE_DATABASE_URL": self.database_url,
            "ICDE_UPLOAD_DIR": str(self.upload_dir),
            "OPENCODE_CONFIG": str(config_path),
        }
        if project_id:
            runtime_env["ICDE_PROJECT_ID"] = project_id
        if decrypted_key:
            runtime_env[spec.env_var] = decrypted_key
            for alias_var in spec.extra_env_vars:
                runtime_env[alias_var] = decrypted_key

        return OpenCodeRuntimeBundle(
            workspace_dir=workspace_dir,
            config_path=config_path,
            agents_md_path=agents_md_path,
            config=config_dict,
            env=runtime_env,
            icde_provider=spec.icde_provider,
            opencode_provider=spec.opencode_provider,
            model_name=bare_model_name,
            opencode_model_id=opencode_model_id,
            raw_protected_paths=raw_paths,
            _owns_workspace_dir=owns_dir,
        )

    def _build_agents_markdown(
        self,
        *,
        project_id: Optional[str],
        mentions: List[MentionRef],
        raw_paths: List[str],
    ) -> str:
        """Render clinical workspace instructions and `@` mention metadata into `AGENTS.md`."""
        context = self.llm_service.build_context(project_id=project_id, mentions=mentions)
        lines: List[str] = [
            "# ICDE Clinical Data Agent Workspace Instructions",
            "",
            "You are operating inside the **ICDE (Integrated Clinical-Data Environment)** Agent Harness.",
            "",
            "## Mandatory Safety & Clinical Governance Rules",
            "1. **RAW Datasets Are Strictly Read-Only**: NEVER write to, overwrite, rename, or delete any `RAW` dataset file or folder.",
            "2. **Use `icde-mcp` Tools for All Lineage Operations**:",
            "   - `icde_list_datasets` / `icde_inspect_dataset` to inspect columns, types, missingness, and lineage.",
            "   - `icde_list_scripts` / `icde_save_script` to search or persist reusable Python `transform(df)` scripts.",
            "   - `icde_derive_dataset` to generate `DERIVED` datasets with atomic SQLite lineage registration.",
            "   - `icde_request_approval` to obtain Principal Investigator (PI) sign-off before locking cohort inclusion/exclusion criteria or statistical models.",
        ]

        if context.project_name:
            lines.extend(["", f"## Active Project: {context.project_name} (`{project_id}`)"])

        if context.available_datasets:
            lines.extend(["", "## Workspace Datasets"])
            for ds in context.available_datasets:
                ds_type = ds.get("type") or "RAW"
                guard_tag = "READ-ONLY" if ds_type == "RAW" else "DERIVED"
                lines.append(
                    f"- `{ds['name']}` (id=`{ds['id']}`, type=`{ds_type}` [{guard_tag}], "
                    f"rows={ds.get('row_count', '?')}, cols={ds.get('column_count', '?')})"
                )

        if context.available_scripts:
            lines.extend(["", "## Registered Reusable Scripts"])
            for sc in context.available_scripts:
                lines.append(
                    f"- `{sc['name']}` (id=`{sc['id']}`, {sc.get('language', 'python')}): "
                    f"{sc.get('description', '')[:120]}"
                )

        if context.mentioned_files:
            lines.extend(["", "## Explicit `@` Mentions in Current Turn"])
            for mf in context.mentioned_files:
                lines.append(f"- **[{mf.type.upper()}] {mf.name}** (`{mf.path}`, id=`{mf.id}`)")
                if mf.columns:
                    col_preview = ", ".join(c.get("name", "?") for c in mf.columns[:15])
                    lines.append(f"  - Columns: {col_preview}")
                if mf.description:
                    lines.append(f"  - Description: {mf.description}")

        if raw_paths:
            lines.extend(["", "## Protected Read-Only Paths (`DatasetType.RAW`)"])
            for rp in raw_paths:
                lines.append(f"- `{rp}`")

        lines.append("")
        return "\n".join(lines)
