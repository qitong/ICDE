import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from ..database import get_db
from ..models.dataset import Dataset, DatasetFile, DatasetType
from ..models.script import Script
from ..schemas.dataset import (
    DatasetCreate,
    DatasetResponse,
    DatasetListResponse,
    DatasetFileResponse,
    FilePreview,
    SetRelationshipRequest,
)
from ..schemas.script import DeriveDatasetRequest
from ..services.file_parser import FileParser
from ..services.script_executor import ScriptExecutor

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    dataset_in: DatasetCreate,
    db: Session = Depends(get_db),
):
    """Create a new dataset."""
    dataset_id = str(uuid.uuid4())
    folder_path = UPLOAD_DIR / dataset_id
    folder_path.mkdir(parents=True, exist_ok=True)

    # Determine type based on parent_dataset_id
    dataset_type = DatasetType.RAW
    if dataset_in.parent_dataset_id:
        # Validate parent exists
        parent = db.query(Dataset).filter(Dataset.id == dataset_in.parent_dataset_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent dataset not found")

    dataset = Dataset(
        id=dataset_id,
        name=dataset_in.name,
        description=dataset_in.description,
        folder_path=str(folder_path),
        file_count=0,
        total_size=0,
        type=dataset_type,
        parent_dataset_id=dataset_in.parent_dataset_id,
        crf_version=dataset_in.crf_version,
        patient_id_column=dataset_in.patient_id_column or "SUBJID",
        project_id=dataset_in.project_id,
        study_name=dataset_in.study_name,
        version_name=dataset_in.version_name,
    )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset


@router.post("/{dataset_id}/files", response_model=List[DatasetFileResponse])
async def upload_files(
    dataset_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload files to a dataset."""
    # Get dataset
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    uploaded_files: List[DatasetFile] = []

    for file in files:
        # Validate extension
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_name = f"{file_id}{ext}"
        file_path = Path(dataset.folder_path) / file_name

        # Save file
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)}MB"
            )

        with open(file_path, "wb") as f:
            f.write(content)

        # Create database record
        dataset_file = DatasetFile(
            id=file_id,
            dataset_id=dataset_id,
            file_name=file_name,
            original_name=file.filename,
            file_path=str(file_path),
            file_type=ext.lstrip("."),
            file_size=len(content),
            parse_status="pending",
        )

        # Parse file
        try:
            row_count, column_count, columns, column_info_json = FileParser.parse_file(file_path)
            dataset_file.row_count = row_count
            dataset_file.column_count = column_count
            dataset_file.column_info = column_info_json
            dataset_file.parse_status = "parsed"
        except Exception as e:
            dataset_file.parse_status = "error"
            dataset_file.parse_error = str(e)

        db.add(dataset_file)
        uploaded_files.append(dataset_file)

    # Update dataset stats
    dataset.file_count = db.query(DatasetFile).filter(DatasetFile.dataset_id == dataset_id).count() + len(uploaded_files)
    dataset.total_size = sum(f.file_size for f in uploaded_files) + dataset.total_size

    db.commit()

    for f in uploaded_files:
        db.refresh(f)

    return uploaded_files


@router.get("", response_model=List[DatasetResponse])
async def list_datasets(db: Session = Depends(get_db)):
    """List all datasets with their files."""
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    return datasets


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Get dataset details including file list."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/files/{file_id}/preview", response_model=FilePreview)
async def get_file_preview(
    dataset_id: str,
    file_id: str,
    db: Session = Depends(get_db),
):
    """Get file structure preview with sample rows."""
    dataset_file = (
        db.query(DatasetFile)
        .filter(DatasetFile.id == file_id, DatasetFile.dataset_id == dataset_id)
        .first()
    )

    if not dataset_file:
        raise HTTPException(status_code=404, detail="File not found")

    if dataset_file.parse_status == "error":
        raise HTTPException(
            status_code=400,
            detail=f"File parsing failed: {dataset_file.parse_error}"
        )

    file_path = Path(dataset_file.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    try:
        preview = FileParser.get_preview(file_path, file_id, dataset_file.original_name)
        return preview
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.post("/{dataset_id}/files/{file_id}/reparse", response_model=DatasetFileResponse)
async def reparse_file(
    dataset_id: str,
    file_id: str,
    db: Session = Depends(get_db),
):
    """Re-parse a file that previously failed or needs updating."""
    dataset_file = (
        db.query(DatasetFile)
        .filter(DatasetFile.id == file_id, DatasetFile.dataset_id == dataset_id)
        .first()
    )

    if not dataset_file:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(dataset_file.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Re-parse the file
    try:
        row_count, column_count, columns, column_info_json = FileParser.parse_file(file_path)
        dataset_file.row_count = row_count
        dataset_file.column_count = column_count
        dataset_file.column_info = column_info_json
        dataset_file.parse_status = "parsed"
        dataset_file.parse_error = None
    except Exception as e:
        dataset_file.parse_status = "error"
        dataset_file.parse_error = str(e)
        db.commit()
        raise HTTPException(status_code=400, detail=f"File parsing failed: {str(e)}")

    db.commit()
    db.refresh(dataset_file)

    return dataset_file


@router.post("/{dataset_id}/reparse-all", response_model=List[DatasetFileResponse])
async def reparse_all_files(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    """Re-parse all files in a dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    files = db.query(DatasetFile).filter(DatasetFile.dataset_id == dataset_id).all()

    results = []
    for dataset_file in files:
        file_path = Path(dataset_file.file_path)
        if not file_path.exists():
            dataset_file.parse_status = "error"
            dataset_file.parse_error = "File not found on disk"
            results.append(dataset_file)
            continue

        try:
            row_count, column_count, columns, column_info_json = FileParser.parse_file(file_path)
            dataset_file.row_count = row_count
            dataset_file.column_count = column_count
            dataset_file.column_info = column_info_json
            dataset_file.parse_status = "parsed"
            dataset_file.parse_error = None
        except Exception as e:
            dataset_file.parse_status = "error"
            dataset_file.parse_error = str(e)

        results.append(dataset_file)

    db.commit()
    for f in results:
        db.refresh(f)

    return results


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Delete a dataset and all its files."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Delete folder from disk
    folder_path = Path(dataset.folder_path)
    if folder_path.exists():
        shutil.rmtree(folder_path)

    # Delete from database (cascade will delete files)
    db.delete(dataset)
    db.commit()

    return None


@router.put("/{dataset_id}/relationship", response_model=DatasetResponse)
async def set_dataset_relationship(
    dataset_id: str,
    request: SetRelationshipRequest,
    db: Session = Depends(get_db),
):
    """Set relationship for a dataset (version or derived)."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if request.relationship_type == "none":
        # Clear any existing relationships
        dataset.parent_dataset_id = None
        dataset.source_dataset_id = None
        dataset.is_manual = False
        dataset.type = DatasetType.RAW

    elif request.relationship_type == "version":
        # Set as new version of parent dataset
        if not request.parent_dataset_id:
            raise HTTPException(
                status_code=400,
                detail="parent_dataset_id is required for version relationship"
            )
        parent = db.query(Dataset).filter(Dataset.id == request.parent_dataset_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent dataset not found")

        dataset.parent_dataset_id = request.parent_dataset_id
        dataset.source_dataset_id = None
        dataset.is_manual = False
        dataset.type = DatasetType.RAW
        if request.version_name:
            dataset.version_name = request.version_name

    elif request.relationship_type == "derived":
        # Set as derived from source dataset
        if not request.source_dataset_id:
            raise HTTPException(
                status_code=400,
                detail="source_dataset_id is required for derived relationship"
            )
        source = db.query(Dataset).filter(Dataset.id == request.source_dataset_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source dataset not found")

        dataset.source_dataset_id = request.source_dataset_id
        dataset.parent_dataset_id = None
        dataset.is_manual = request.is_manual
        dataset.type = DatasetType.DERIVED
        dataset.script_id = None  # Manual upload, no script

    # Update description if provided
    if request.description:
        dataset.description = request.description

    db.commit()
    db.refresh(dataset)

    return dataset


@router.get("/{dataset_id}/versions", response_model=List[DatasetResponse])
async def get_dataset_versions(dataset_id: str, db: Session = Depends(get_db)):
    """Get version history of a dataset (all versions in the same lineage)."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Find all versions in the chain
    versions = []

    # Go up to find the root
    root = dataset
    while root.parent_dataset_id:
        parent = db.query(Dataset).filter(Dataset.id == root.parent_dataset_id).first()
        if not parent:
            break
        root = parent

    # Collect all descendants from root
    def collect_descendants(node):
        versions.append(node)
        children = db.query(Dataset).filter(Dataset.parent_dataset_id == node.id).all()
        for child in children:
            collect_descendants(child)

    collect_descendants(root)

    return versions


@router.post("/{dataset_id}/derive", response_model=DatasetResponse, status_code=201)
async def derive_dataset(
    dataset_id: str,
    derive_request: DeriveDatasetRequest,
    db: Session = Depends(get_db),
):
    """Create a derived dataset by applying a script."""
    # Get source dataset
    source = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source dataset not found")

    # Get script
    script = db.query(Script).filter(Script.id == derive_request.script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Execute script and save result
    executor = ScriptExecutor()
    result = executor.execute_and_save(
        script=script,
        source_dataset=source,
        output_name=derive_request.output_name,
        output_dir=UPLOAD_DIR,
        db=db,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return result.dataset


@router.get("/{dataset_id}/derived", response_model=List[DatasetResponse])
async def get_derived_datasets(dataset_id: str, db: Session = Depends(get_db)):
    """Get all datasets derived from this source."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    derived = db.query(Dataset).filter(Dataset.source_dataset_id == dataset_id).all()
    return derived


@router.get("/{dataset_id}/lineage")
async def get_dataset_lineage(dataset_id: str, db: Session = Depends(get_db)):
    """Get full lineage of a dataset (ancestors and descendants)."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Find ancestors (both version parents and derivation sources)
    ancestors = []
    visited = set()

    def find_ancestors(node):
        if node.id in visited:
            return
        visited.add(node.id)

        # Version parent
        if node.parent_dataset_id:
            parent = db.query(Dataset).filter(Dataset.id == node.parent_dataset_id).first()
            if parent:
                ancestors.append({
                    "id": parent.id,
                    "name": parent.name,
                    "type": parent.type.value if parent.type else "RAW",
                    "relationship": "version_parent"
                })
                find_ancestors(parent)

        # Derivation source
        if node.source_dataset_id:
            source = db.query(Dataset).filter(Dataset.id == node.source_dataset_id).first()
            if source:
                ancestors.append({
                    "id": source.id,
                    "name": source.name,
                    "type": source.type.value if source.type else "RAW",
                    "relationship": "derivation_source"
                })
                find_ancestors(source)

    find_ancestors(dataset)

    # Find descendants (both version children and derived datasets)
    descendants = []
    visited.clear()

    def find_descendants(node):
        if node.id in visited:
            return
        visited.add(node.id)

        # Version children
        version_children = db.query(Dataset).filter(Dataset.parent_dataset_id == node.id).all()
        for child in version_children:
            descendants.append({
                "id": child.id,
                "name": child.name,
                "type": child.type.value if child.type else "RAW",
                "relationship": "version_child"
            })
            find_descendants(child)

        # Derived datasets
        derived = db.query(Dataset).filter(Dataset.source_dataset_id == node.id).all()
        for d in derived:
            descendants.append({
                "id": d.id,
                "name": d.name,
                "type": d.type.value if d.type else "DERIVED",
                "relationship": "derived"
            })
            find_descendants(d)

    find_descendants(dataset)

    return {
        "dataset": {
            "id": dataset.id,
            "name": dataset.name,
            "type": dataset.type.value if dataset.type else "RAW"
        },
        "ancestors": ancestors,
        "descendants": descendants
    }
