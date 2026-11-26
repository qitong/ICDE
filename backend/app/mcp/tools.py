"""Domain tools exposed by the local ICDE MCP Bridge (`icde-mcp`)."""

from __future__ import annotations

import json
import os
import stat
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.harness.approval_store import ApprovalStore
from app.harness.events import HarnessEvent
from app.harness.workspace_guard import ReadOnlyDatasetViolationError, WorkspaceGuard
from app.models.dataset import Dataset, DatasetFile, DatasetLineage, DatasetType
from app.models.script import Script
from app.services.file_parser import FileParser
from app.services.script_executor import ScriptExecutor


EventSink = Callable[[HarnessEvent], None]


TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "icde_list_datasets",
        "description": (
            "List datasets in ICDE along with versions, RAW/DERIVED type, read-only status, "
            "and row/column counts."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Optional project UUID to scope datasets.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "icde_inspect_dataset",
        "description": (
            "Inspect column metadata (name, data_type, non_null_count, unique_count, sample_values) "
            "and upstream/downstream lineage summary of a dataset without mutating data."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset_id": {
                    "type": "string",
                    "description": "UUID of the dataset to inspect.",
                },
            },
            "required": ["dataset_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "icde_list_scripts",
        "description": "List or search reusable Python/R transformation and analysis scripts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Optional search keyword matching name, display_name, description, or keywords.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "icde_save_script",
        "description": (
            "Create or update a reusable transformation/analysis script in SQLite `scripts` "
            "and emit a `script_saved` workspace event."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Unique machine identifier (snake_case)."},
                "display_name": {"type": "string", "description": "Human-readable title."},
                "description": {"type": "string", "description": "Detailed clinical/statistical logic description."},
                "code": {"type": "string", "description": "Script source code (e.g. defining `transform(df)`)."},
                "language": {"type": "string", "default": "python"},
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Searchable clinical tags.",
                },
                "input_requirements": {"type": "string"},
                "output_description": {"type": "string"},
                "script_id": {"type": "string", "description": "Optional existing script ID to update."},
                "created_from_prompt": {"type": "string"},
            },
            "required": ["name", "display_name", "description", "code"],
            "additionalProperties": False,
        },
    },
    {
        "name": "icde_derive_dataset",
        "description": (
            "Derive a new `DERIVED` dataset from a source dataset and registered script while "
            "enforcing `WorkspaceGuard` RAW immutability, atomically recording `Dataset`, "
            "`DatasetFile`, and `DatasetLineage`, and emitting workspace events."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_dataset_id": {"type": "string", "description": "Source dataset UUID."},
                "script_id": {"type": "string", "description": "Transformation script UUID."},
                "output_name": {"type": "string", "description": "Name of the new derived dataset."},
            },
            "required": ["source_dataset_id", "script_id", "output_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "icde_request_approval",
        "description": (
            "Create a Human-in-the-loop clinical approval checkpoint (e.g. cohort inclusion/exclusion "
            "criteria or statistical model confirmation) for Principal Investigator review."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Machine action identifier (e.g. confirm_cohort_criteria)."},
                "title": {"type": "string", "description": "Short clinical checkpoint title."},
                "summary": {"type": "string", "description": "Detailed explanation of proposed criteria/model."},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Selectable decision options for the PI.",
                },
            },
            "required": ["action", "title", "summary"],
            "additionalProperties": False,
        },
    },
]


class ICDEMCPTools:
    """
    Callable implementation of ICDE's domain tools.

    Can be invoked directly from Python or mounted through `ICDEMCPServer` over
    JSON-RPC 2.0 (stdio / HTTP).
    """

    def __init__(
        self,
        db: Session,
        *,
        upload_dir: Optional[Path] = None,
        event_sink: Optional[EventSink] = None,
        conversation_id: Optional[str] = None,
    ) -> None:
        self.db = db
        env_upload = os.environ.get("ICDE_UPLOAD_DIR")
        resolved_upload = Path(upload_dir) if upload_dir else (
            Path(env_upload) if env_upload else UPLOAD_DIR
        )
        self.upload_dir = resolved_upload.resolve()
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.guard = WorkspaceGuard(db, workspace_root=self.upload_dir)
        self.approval_store = ApprovalStore(db)
        self._event_sink = event_sink
        self.conversation_id = conversation_id
        self.emitted_events: List[HarnessEvent] = []

    def _emit(self, event: HarnessEvent) -> Dict[str, Any]:
        self.emitted_events.append(event)
        if self._event_sink is not None:
            self._event_sink(event)
        return event.to_dict()

    # ============== Tool 1: icde_list_datasets ==============

    def icde_list_datasets(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """List datasets, versions, types (`RAW`/`DERIVED`), and row/column counts."""
        query = self.db.query(Dataset)
        if project_id:
            query = query.filter(Dataset.project_id == project_id)

        datasets = query.order_by(Dataset.created_at.desc()).all()
        items: List[Dict[str, Any]] = []
        for ds in datasets:
            ds_type = ds.type.value if ds.type else "RAW"
            row_count = ds.row_count
            col_count = ds.column_count
            if (row_count is None or col_count is None) and ds.files:
                first_file = ds.files[0]
                row_count = row_count if row_count is not None else first_file.row_count
                col_count = col_count if col_count is not None else first_file.column_count

            items.append(
                {
                    "id": ds.id,
                    "name": ds.name,
                    "description": ds.description,
                    "type": ds_type,
                    "read_only": ds_type == "RAW",
                    "project_id": ds.project_id,
                    "study_name": ds.study_name,
                    "version_name": ds.version_name,
                    "crf_version": ds.crf_version,
                    "row_count": row_count,
                    "column_count": col_count,
                    "file_count": len(ds.files) if ds.files is not None else ds.file_count,
                    "parent_dataset_id": ds.parent_dataset_id,
                    "source_dataset_id": ds.source_dataset_id,
                    "script_id": ds.script_id,
                    "is_stale": bool(ds.is_stale),
                }
            )

        return {
            "count": len(items),
            "datasets": items,
        }

    # ============== Tool 2: icde_inspect_dataset ==============

    def icde_inspect_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Return column metadata and lineage summary without mutating dataset files."""
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        raw_snapshot = (
            self.guard.snapshot_raw_files([dataset.id])
            if dataset.type == DatasetType.RAW
            else None
        )

        files_meta: List[Dict[str, Any]] = []
        aggregated_columns: List[Dict[str, Any]] = []

        for ds_file in dataset.files:
            columns: List[Dict[str, Any]] = []
            row_count = ds_file.row_count
            col_count = ds_file.column_count

            if ds_file.column_info:
                try:
                    columns = json.loads(ds_file.column_info)
                except json.JSONDecodeError:
                    columns = []

            if not columns and ds_file.file_path:
                fpath = Path(ds_file.file_path)
                if fpath.exists() and fpath.suffix.lower() in {".csv", ".xlsx", ".xls"}:
                    parsed_rows, parsed_cols, col_objs, _ = FileParser.parse_file(fpath)
                    row_count = row_count if row_count is not None else parsed_rows
                    col_count = col_count if col_count is not None else parsed_cols
                    columns = [c.model_dump() for c in col_objs]

            if not aggregated_columns and columns:
                aggregated_columns = columns

            files_meta.append(
                {
                    "id": ds_file.id,
                    "file_name": ds_file.original_name or ds_file.file_name,
                    "file_type": ds_file.file_type,
                    "row_count": row_count,
                    "column_count": col_count,
                    "columns": columns,
                }
            )

        lineage = self._build_lineage_summary(dataset)

        if raw_snapshot is not None:
            self.guard.verify_raw_files_unchanged(raw_snapshot)

        ds_type = dataset.type.value if dataset.type else "RAW"
        effective_rows = dataset.row_count
        effective_cols = dataset.column_count
        if files_meta:
            if effective_rows is None:
                effective_rows = files_meta[0]["row_count"]
            if effective_cols is None:
                effective_cols = files_meta[0]["column_count"]

        return {
            "dataset": {
                "id": dataset.id,
                "name": dataset.name,
                "description": dataset.description,
                "type": ds_type,
                "read_only": ds_type == "RAW",
                "study_name": dataset.study_name,
                "version_name": dataset.version_name,
                "crf_version": dataset.crf_version,
                "patient_id_column": dataset.patient_id_column,
                "row_count": effective_rows,
                "column_count": effective_cols,
            },
            "columns": aggregated_columns,
            "files": files_meta,
            "lineage": lineage,
        }

    def _build_lineage_summary(self, dataset: Dataset) -> Dict[str, Any]:
        ancestors: List[Dict[str, Any]] = []
        visited = set()

        def walk_up(node: Dataset) -> None:
            if node.id in visited:
                return
            visited.add(node.id)
            if node.parent_dataset_id:
                parent = self.db.query(Dataset).filter(Dataset.id == node.parent_dataset_id).first()
                if parent:
                    ancestors.append(
                        {
                            "id": parent.id,
                            "name": parent.name,
                            "type": parent.type.value if parent.type else "RAW",
                            "relationship": "version_parent",
                        }
                    )
                    walk_up(parent)
            if node.source_dataset_id:
                source = self.db.query(Dataset).filter(Dataset.id == node.source_dataset_id).first()
                if source:
                    ancestors.append(
                        {
                            "id": source.id,
                            "name": source.name,
                            "type": source.type.value if source.type else "RAW",
                            "relationship": "derivation_source",
                            "script_id": node.script_id,
                        }
                    )
                    walk_up(source)

        walk_up(dataset)

        descendants: List[Dict[str, Any]] = []
        visited.clear()

        def walk_down(node: Dataset) -> None:
            if node.id in visited:
                return
            visited.add(node.id)
            for vchild in self.db.query(Dataset).filter(Dataset.parent_dataset_id == node.id).all():
                descendants.append(
                    {
                        "id": vchild.id,
                        "name": vchild.name,
                        "type": vchild.type.value if vchild.type else "RAW",
                        "relationship": "version_child",
                    }
                )
                walk_down(vchild)
            for derived in self.db.query(Dataset).filter(Dataset.source_dataset_id == node.id).all():
                descendants.append(
                    {
                        "id": derived.id,
                        "name": derived.name,
                        "type": derived.type.value if derived.type else "DERIVED",
                        "relationship": "derived",
                        "script_id": derived.script_id,
                    }
                )
                walk_down(derived)

        walk_down(dataset)
        return {
            "ancestors": ancestors,
            "descendants": descendants,
        }

    # ============== Tool 3: icde_list_scripts ==============

    def icde_list_scripts(self, query: Optional[str] = None) -> Dict[str, Any]:
        """List or search transformation/analysis scripts."""
        q = self.db.query(Script)
        if query and query.strip():
            term = f"%{query.strip()}%"
            q = q.filter(
                or_(
                    Script.name.ilike(term),
                    Script.display_name.ilike(term),
                    Script.description.ilike(term),
                    Script.keywords.ilike(term),
                )
            )

        scripts = q.order_by(Script.usage_count.desc(), Script.updated_at.desc()).all()
        items: List[Dict[str, Any]] = []
        for sc in scripts:
            keywords = None
            if sc.keywords:
                try:
                    keywords = json.loads(sc.keywords)
                except json.JSONDecodeError:
                    keywords = []
            items.append(
                {
                    "id": sc.id,
                    "name": sc.name,
                    "display_name": sc.display_name,
                    "description": sc.description,
                    "language": sc.language,
                    "keywords": keywords,
                    "usage_count": sc.usage_count,
                    "version": sc.version,
                }
            )

        return {
            "count": len(items),
            "scripts": items,
        }

    # ============== Tool 4: icde_save_script ==============

    def icde_save_script(
        self,
        *,
        name: str,
        display_name: str,
        description: str,
        code: str,
        language: str = "python",
        keywords: Optional[List[str]] = None,
        input_requirements: Optional[str] = None,
        output_description: Optional[str] = None,
        script_id: Optional[str] = None,
        created_from_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update a script in SQLite and emit `script_saved`."""
        if language.lower() == "python":
            executor = ScriptExecutor()
            is_valid, syntax_err = executor.validate_syntax(code)
            if not is_valid:
                raise ValueError(f"Invalid Python script syntax: {syntax_err}")

        keywords_json = json.dumps(keywords, ensure_ascii=False) if keywords is not None else None

        existing: Optional[Script] = None
        if script_id:
            existing = self.db.query(Script).filter(Script.id == script_id).first()
            if not existing:
                raise ValueError(f"Script not found for update: {script_id}")
        else:
            existing = self.db.query(Script).filter(Script.name == name).first()

        action_kind = "updated" if existing else "created"
        if existing:
            existing.display_name = display_name
            existing.description = description
            existing.code = code
            existing.language = language
            if keywords_json is not None:
                existing.keywords = keywords_json
            if input_requirements is not None:
                existing.input_requirements = input_requirements
            if output_description is not None:
                existing.output_description = output_description
            existing.version = (existing.version or 1) + 1
            existing.updated_at = datetime.utcnow()
            script = existing
        else:
            script = Script(
                name=name,
                display_name=display_name,
                description=description,
                code=code,
                language=language,
                keywords=keywords_json,
                input_requirements=input_requirements,
                output_description=output_description,
                created_by="llm",
                created_from_prompt=created_from_prompt,
                version=1,
            )
            self.db.add(script)

        self.db.commit()
        self.db.refresh(script)

        ws_event = self._emit(
            HarnessEvent.workspace_event_chunk(
                event_name="script_saved",
                script_id=script.id,
                payload={
                    "action": action_kind,
                    "script_id": script.id,
                    "name": script.name,
                    "display_name": script.display_name,
                    "language": script.language,
                    "version": script.version,
                },
                conversation_id=self.conversation_id,
            )
        )

        return {
            "action": action_kind,
            "script": {
                "id": script.id,
                "name": script.name,
                "display_name": script.display_name,
                "description": script.description,
                "language": script.language,
                "version": script.version,
            },
            "_icde_events": [ws_event],
        }

    # ============== Tool 5: icde_derive_dataset ==============

    def icde_derive_dataset(
        self,
        *,
        source_dataset_id: str,
        script_id: str,
        output_name: str,
    ) -> Dict[str, Any]:
        """
        Derive a `DERIVED` dataset from `source_dataset_id` + `script_id`, enforcing
        `WorkspaceGuard` RAW immutability and atomic `Dataset` + `DatasetFile` +
        `DatasetLineage` persistence.
        """
        if not output_name or not output_name.strip():
            raise ValueError("output_name must not be empty")
        if "/" in output_name or "\\" in output_name or ".." in output_name:
            raise ReadOnlyDatasetViolationError(
                f"Invalid output_name '{output_name}': path separators and traversal segments are forbidden."
            )

        source = self.db.query(Dataset).filter(Dataset.id == source_dataset_id).first()
        if not source:
            raise ValueError(f"Source dataset not found: {source_dataset_id}")
        if not source.files:
            raise ValueError(f"Source dataset '{source.name}' ({source.id}) has no files")

        script = self.db.query(Script).filter(Script.id == script_id).first()
        if not script:
            raise ValueError(f"Script not found: {script_id}")

        source_file = source.files[0]
        input_path = Path(source_file.file_path).resolve()
        if not input_path.exists():
            raise ValueError(f"Source file not found on disk: {input_path}")

        # 1. Snapshot all RAW files before running user/agent transformation code
        raw_snapshot = self.guard.snapshot_raw_files()

        # Temporarily enforce 0o444 on RAW files during script execution to block in-code writes
        saved_modes: Dict[Path, int] = {}
        try:
            for file_key in raw_snapshot.files:
                rpath = Path(file_key)
                if rpath.exists():
                    saved_modes[rpath] = stat.S_IMODE(rpath.stat().st_mode)
                    os.chmod(rpath, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

            executor = ScriptExecutor()
            exec_result = executor.execute(script.code, input_path)
        finally:
            for rpath, orig_mode in saved_modes.items():
                if rpath.exists():
                    os.chmod(rpath, orig_mode)

        # 2. Verify zero RAW bytes or folder inventories changed during execution
        self.guard.verify_raw_files_unchanged(raw_snapshot)

        if not exec_result.success or exec_result.output_df is None:
            raise ValueError(f"Script execution failed: {exec_result.error}")

        # 3. Validate derived output folder path against WorkspaceGuard
        derived_id = str(uuid.uuid4())
        derived_dir = self.guard.assert_writable(self.upload_dir / derived_id)
        derived_dir.mkdir(parents=True, exist_ok=True)

        csv_filename = f"{derived_id}.csv"
        parquet_filename = f"{derived_id}.parquet"
        csv_path = self.guard.assert_writable(derived_dir / csv_filename)
        parquet_path = self.guard.assert_writable(derived_dir / parquet_filename)

        output_df = exec_result.output_df
        output_df.to_csv(csv_path, index=False)
        output_df.to_parquet(parquet_path, index=False)

        row_count, column_count, _, column_info_json = FileParser.parse_file(csv_path)
        csv_size = csv_path.stat().st_size

        # 4. Atomic SQLite persistence: Dataset (DERIVED) + DatasetFile + DatasetLineage + Script stats
        try:
            derived_dataset = Dataset(
                id=derived_id,
                name=output_name.strip(),
                description=f"Derived from {source.name} via script {script.display_name or script.name}",
                type=DatasetType.DERIVED,
                project_id=source.project_id,
                study_name=source.study_name,
                version_name=source.version_name,
                source_dataset_id=source.id,
                script_id=script.id,
                patient_id_column=source.patient_id_column or "SUBJID",
                row_count=row_count,
                column_count=column_count,
                folder_path=str(derived_dir),
                file_count=1,
                total_size=csv_size,
            )
            self.db.add(derived_dataset)

            derived_file = DatasetFile(
                id=str(uuid.uuid4()),
                dataset_id=derived_id,
                file_name=csv_filename,
                original_name=f"{output_name.strip()}.csv",
                file_path=str(csv_path),
                file_type="csv",
                file_size=csv_size,
                row_count=row_count,
                column_count=column_count,
                column_info=column_info_json,
                parse_status="parsed",
            )
            self.db.add(derived_file)

            lineage_record = DatasetLineage(
                id=str(uuid.uuid4()),
                parent_id=source.id,
                child_id=derived_id,
                relationship="DERIVED_FROM",
                script_id=script.id,
            )
            self.db.add(lineage_record)

            script.usage_count = (script.usage_count or 0) + 1
            script.last_used_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(derived_dataset)
            self.db.refresh(derived_file)
        except Exception:
            self.db.rollback()
            raise

        # 5. Final cryptographic verification of RAW source datasets
        self.guard.verify_raw_files_unchanged(raw_snapshot)

        ev_derived = self._emit(
            HarnessEvent.workspace_event_chunk(
                event_name="dataset_derived",
                dataset_id=derived_dataset.id,
                script_id=script.id,
                payload={
                    "dataset_id": derived_dataset.id,
                    "name": derived_dataset.name,
                    "source_dataset_id": source.id,
                    "script_id": script.id,
                    "row_count": row_count,
                    "column_count": column_count,
                    "stats": exec_result.stats,
                },
                conversation_id=self.conversation_id,
            )
        )
        ev_lineage = self._emit(
            HarnessEvent.workspace_event_chunk(
                event_name="lineage_updated",
                dataset_id=derived_dataset.id,
                script_id=script.id,
                payload={
                    "parent_id": source.id,
                    "child_id": derived_dataset.id,
                    "relationship": "DERIVED_FROM",
                    "script_id": script.id,
                },
                conversation_id=self.conversation_id,
            )
        )

        return {
            "dataset": {
                "id": derived_dataset.id,
                "name": derived_dataset.name,
                "type": derived_dataset.type.value,
                "source_dataset_id": derived_dataset.source_dataset_id,
                "script_id": derived_dataset.script_id,
                "row_count": derived_dataset.row_count,
                "column_count": derived_dataset.column_count,
                "file_count": derived_dataset.file_count,
            },
            "file": {
                "id": derived_file.id,
                "file_name": derived_file.original_name,
                "file_type": derived_file.file_type,
                "row_count": derived_file.row_count,
                "column_count": derived_file.column_count,
            },
            "stats": exec_result.stats,
            "_icde_events": [ev_derived, ev_lineage],
        }

    # ============== Tool 6: icde_request_approval ==============

    def icde_request_approval(
        self,
        *,
        action: str,
        title: str,
        summary: str,
        options: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a tracked PI approval checkpoint and emit `approval_required`."""
        checkpoint = self.approval_store.create(
            action=action,
            title=title,
            summary=summary,
            options=options,
            conversation_id=self.conversation_id,
        )
        ev_approval = self._emit(
            HarnessEvent.approval_required_event(
                checkpoint,
                conversation_id=self.conversation_id,
            )
        )
        return {
            "approval": checkpoint.model_dump(),
            "_icde_events": [ev_approval],
        }

    # ============== Dynamic Dispatcher ==============

    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatch a tool call by MCP tool name."""
        args = arguments or {}
        dispatch_map: Dict[str, Callable[..., Dict[str, Any]]] = {
            "icde_list_datasets": self.icde_list_datasets,
            "icde_inspect_dataset": self.icde_inspect_dataset,
            "icde_list_scripts": self.icde_list_scripts,
            "icde_save_script": self.icde_save_script,
            "icde_derive_dataset": self.icde_derive_dataset,
            "icde_request_approval": self.icde_request_approval,
        }
        handler = dispatch_map.get(tool_name)
        if handler is None:
            raise KeyError(f"Unknown ICDE MCP tool: {tool_name}")
        return handler(**args)
