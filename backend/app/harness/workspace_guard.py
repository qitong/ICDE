"""Read-only enforcement and integrity verification for `DatasetType.RAW` files."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

from sqlalchemy.orm import Session

from app.models.dataset import Dataset, DatasetFile, DatasetType


class ReadOnlyDatasetViolationError(PermissionError):
    """Raised when any operation attempts to mutate or tamper with a `RAW` dataset."""

    def __init__(
        self,
        message: str,
        *,
        target_path: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.target_path = target_path
        self.dataset_id = dataset_id


@dataclass(frozen=True)
class RawFileDigest:
    """Cryptographic fingerprint of a protected `RAW` file."""

    dataset_id: str
    file_path: str
    sha256: str
    size: int


@dataclass(frozen=True)
class RawSnapshot:
    """Snapshot of all `RAW` files and folder inventories prior to an agent action."""

    files: Dict[str, RawFileDigest]
    folder_inventories: Dict[str, Tuple[str, Set[str]]]


class WorkspaceGuard:
    """
    Enforces strict read-only immutability on all `DatasetType.RAW` folders and files.

    Defense-in-depth mechanisms:
    1. Canonical `Path.resolve()` + symlink & `../` traversal checks rejecting writes/deletes.
    2. Pre/post-turn cryptographic SHA-256 verification (`snapshot_raw_files` /
       `verify_raw_files_unchanged`).
    3. POSIX file mode helper (`0o444` lock on `RAW` files, safely restored only for
       explicit user-initiated dataset deletion).
    """

    def __init__(self, db: Session, workspace_root: Optional[Union[str, Path]] = None) -> None:
        self.db = db
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None

    def list_raw_datasets(self, project_id: Optional[str] = None) -> List[Dataset]:
        """Return `DatasetType.RAW` datasets (all projects by default for write safety)."""
        query = self.db.query(Dataset).filter(Dataset.type == DatasetType.RAW)
        if project_id is not None:
            query = query.filter(Dataset.project_id == project_id)
        return query.all()

    def get_protected_raw_roots(self) -> List[Tuple[str, Path]]:
        """
        Return `(dataset_id, canonical_path)` pairs for every `RAW` dataset folder and file.
        """
        protected: List[Tuple[str, Path]] = []
        seen: Set[Tuple[str, str]] = set()

        for ds in self.list_raw_datasets():
            if ds.folder_path:
                resolved_folder = Path(ds.folder_path).expanduser().resolve(strict=False)
                key = (ds.id, str(resolved_folder))
                if key not in seen:
                    seen.add(key)
                    protected.append((ds.id, resolved_folder))

            for ds_file in ds.files:
                if ds_file.file_path:
                    resolved_file = Path(ds_file.file_path).expanduser().resolve(strict=False)
                    key = (ds.id, str(resolved_file))
                    if key not in seen:
                        seen.add(key)
                        protected.append((ds.id, resolved_file))

        return protected

    def assert_writable(
        self,
        target_path: Union[str, Path],
        *,
        base_dir: Optional[Union[str, Path]] = None,
        is_directory_delete: bool = False,
    ) -> Path:
        """
        Validate that `target_path` does not target, traverse into, or symlink to any `RAW`
        dataset folder or file. Raises `ReadOnlyDatasetViolationError` on violation.
        """
        raw_candidate = Path(target_path).expanduser()
        if not raw_candidate.is_absolute():
            anchor = Path(base_dir).resolve(strict=False) if base_dir else (
                self.workspace_root or Path.cwd().resolve(strict=False)
            )
            candidate = anchor / raw_candidate
        else:
            candidate = raw_candidate

        resolved_target = candidate.resolve(strict=False)
        protected_roots = self.get_protected_raw_roots()

        # Check every symlink component along candidate path as well
        symlink_targets: List[Path] = []
        probe = candidate
        for part_parent in [probe, *probe.parents]:
            try:
                if part_parent.is_symlink():
                    symlink_targets.append(part_parent.resolve(strict=False))
            except OSError:
                continue

        paths_to_check = [resolved_target, *symlink_targets]

        for dataset_id, protected_path in protected_roots:
            for checked_path in paths_to_check:
                if checked_path == protected_path or protected_path in checked_path.parents:
                    raise ReadOnlyDatasetViolationError(
                        f"Write/modify/delete denied: '{target_path}' resolves inside read-only "
                        f"RAW dataset '{dataset_id}' ({protected_path}).",
                        target_path=str(resolved_target),
                        dataset_id=dataset_id,
                    )
                if is_directory_delete and checked_path in protected_path.parents:
                    raise ReadOnlyDatasetViolationError(
                        f"Directory delete denied: '{target_path}' contains read-only "
                        f"RAW dataset '{dataset_id}' ({protected_path}).",
                        target_path=str(resolved_target),
                        dataset_id=dataset_id,
                    )

        return resolved_target

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Compute hex SHA-256 digest of a file without modifying timestamps or data."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for block in iter(lambda: handle.read(65536), b""):
                hasher.update(block)
        return hasher.hexdigest()

    def snapshot_raw_files(
        self,
        dataset_ids: Optional[Iterable[str]] = None,
    ) -> RawSnapshot:
        """
        Capture SHA-256 digests and folder file inventories for `RAW` datasets.
        """
        allowed_ids = set(dataset_ids) if dataset_ids is not None else None
        digests: Dict[str, RawFileDigest] = {}
        folder_inventories: Dict[str, Tuple[str, Set[str]]] = {}

        for ds in self.list_raw_datasets():
            if allowed_ids is not None and ds.id not in allowed_ids:
                continue

            candidate_files: Set[Path] = set()
            if ds.folder_path:
                folder = Path(ds.folder_path).expanduser().resolve(strict=False)
                if folder.exists() and folder.is_dir():
                    inventory: Set[str] = set()
                    for child in folder.rglob("*"):
                        if child.is_file():
                            resolved_child = child.resolve(strict=False)
                            candidate_files.add(resolved_child)
                            inventory.add(str(resolved_child))
                    folder_inventories[str(folder)] = (ds.id, inventory)

            for ds_file in ds.files:
                if ds_file.file_path:
                    resolved_file = Path(ds_file.file_path).expanduser().resolve(strict=False)
                    if resolved_file.exists() and resolved_file.is_file():
                        candidate_files.add(resolved_file)

            for file_path in sorted(candidate_files):
                key = str(file_path)
                digests[key] = RawFileDigest(
                    dataset_id=ds.id,
                    file_path=key,
                    sha256=self.compute_sha256(file_path),
                    size=file_path.stat().st_size,
                )

        return RawSnapshot(files=digests, folder_inventories=folder_inventories)

    def verify_raw_files_unchanged(self, snapshot: RawSnapshot) -> bool:
        """
        Verify that zero `RAW` files were modified, deleted, or injected since `snapshot`.
        Raises `ReadOnlyDatasetViolationError` on any discrepancy.
        """
        for file_key, expected in snapshot.files.items():
            path = Path(file_key)
            if not path.exists() or not path.is_file():
                raise ReadOnlyDatasetViolationError(
                    f"RAW dataset file '{file_key}' (dataset '{expected.dataset_id}') was deleted!",
                    target_path=file_key,
                    dataset_id=expected.dataset_id,
                )

            actual_size = path.stat().st_size
            actual_sha256 = self.compute_sha256(path)
            if actual_size != expected.size or actual_sha256 != expected.sha256:
                raise ReadOnlyDatasetViolationError(
                    f"RAW dataset file '{file_key}' (dataset '{expected.dataset_id}') was altered "
                    f"(expected sha256={expected.sha256[:12]}..., got {actual_sha256[:12]}...).",
                    target_path=file_key,
                    dataset_id=expected.dataset_id,
                )

        for folder_str, (dataset_id, expected_inventory) in snapshot.folder_inventories.items():
            folder = Path(folder_str)
            if not folder.exists():
                raise ReadOnlyDatasetViolationError(
                    f"RAW dataset folder '{folder_str}' (dataset '{dataset_id}') was removed!",
                    target_path=folder_str,
                    dataset_id=dataset_id,
                )
            current_inventory = {
                str(child.resolve(strict=False))
                for child in folder.rglob("*")
                if child.is_file()
            }
            if current_inventory != expected_inventory:
                added = current_inventory - expected_inventory
                removed = expected_inventory - current_inventory
                raise ReadOnlyDatasetViolationError(
                    f"RAW dataset folder '{folder_str}' (dataset '{dataset_id}') inventory changed "
                    f"(added={sorted(added)}, removed={sorted(removed)}).",
                    target_path=folder_str,
                    dataset_id=dataset_id,
                )

        return True

    def lock_raw_dataset_files(self, dataset_id: Optional[str] = None) -> List[Path]:
        """
        Apply OS-level read-only permissions (`0o444` on files and `0o555` on directories)
        to `DatasetType.RAW` datasets so files can neither be modified nor unlinked/renamed.
        """
        file_mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH  # 0o444
        dir_mode = (
            stat.S_IRUSR
            | stat.S_IXUSR
            | stat.S_IRGRP
            | stat.S_IXGRP
            | stat.S_IROTH
            | stat.S_IXOTH
        )  # 0o555

        locked: List[Path] = []
        datasets = self.list_raw_datasets()
        for ds in datasets:
            if dataset_id is not None and ds.id != dataset_id:
                continue

            file_paths: Set[Path] = set()
            dir_paths: List[Path] = []

            if ds.folder_path:
                folder = Path(ds.folder_path).expanduser()
                if folder.exists() and folder.is_dir():
                    for root_str, subdirs, files in os.walk(folder, topdown=False):
                        root_path = Path(root_str)
                        for fname in files:
                            fpath = root_path / fname
                            if fpath.is_file() and not fpath.is_symlink():
                                file_paths.add(fpath)
                        for dname in subdirs:
                            dpath = root_path / dname
                            if dpath.is_dir() and not dpath.is_symlink():
                                dir_paths.append(dpath)
                    # Never lock the shared workspace_root itself if misconfigured as folder_path
                    if self.workspace_root is None or folder.resolve() != self.workspace_root:
                        dir_paths.append(folder)

            for ds_file in ds.files:
                if ds_file.file_path:
                    fpath = Path(ds_file.file_path).expanduser()
                    if fpath.exists() and fpath.is_file() and not fpath.is_symlink():
                        file_paths.add(fpath)

            for fpath in sorted(file_paths):
                os.chmod(fpath, file_mode)
                locked.append(fpath)

            seen_dirs: Set[str] = set()
            for dpath in dir_paths:
                dkey = str(dpath.resolve(strict=False))
                if dkey not in seen_dirs:
                    seen_dirs.add(dkey)
                    os.chmod(dpath, dir_mode)
                    locked.append(dpath)

        return locked

    @staticmethod
    def unlock_for_deletion(dataset: Dataset) -> List[Path]:
        """
        Restore owner write permissions (`0o755` on directories, `0o644` on files)
        top-down strictly prior to explicit dataset deletion or test teardown.
        """
        dir_rw_mode = (
            stat.S_IRWXU
            | stat.S_IRGRP
            | stat.S_IXGRP
            | stat.S_IROTH
            | stat.S_IXOTH
        )  # 0o755
        file_rw_mode = (
            stat.S_IRUSR
            | stat.S_IWUSR
            | stat.S_IRGRP
            | stat.S_IROTH
        )  # 0o644

        unlocked: List[Path] = []
        if dataset.folder_path:
            folder = Path(dataset.folder_path).expanduser()
            if folder.exists() and folder.is_dir():
                os.chmod(folder, dir_rw_mode)
                unlocked.append(folder)
                for root_str, subdirs, files in os.walk(folder, topdown=True):
                    root_path = Path(root_str)
                    for dname in subdirs:
                        dpath = root_path / dname
                        if dpath.is_dir() and not dpath.is_symlink():
                            os.chmod(dpath, dir_rw_mode)
                            unlocked.append(dpath)
                    for fname in files:
                        fpath = root_path / fname
                        if fpath.is_file() and not fpath.is_symlink():
                            os.chmod(fpath, file_rw_mode)
                            unlocked.append(fpath)

        for ds_file in dataset.files:
            if ds_file.file_path:
                fpath = Path(ds_file.file_path).expanduser()
                if fpath.exists() and fpath.is_file() and not fpath.is_symlink():
                    os.chmod(fpath, file_rw_mode)
                    if fpath not in unlocked:
                        unlocked.append(fpath)

        return unlocked
