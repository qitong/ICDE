import os
import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from ..database import get_db
from ..models.dataset import Dataset, DatasetFile
from ..schemas.dataset import (
    DatasetCreate,
    DatasetResponse,
    DatasetListResponse,
    DatasetFileResponse,
    FilePreview,
)
from ..services.file_parser import FileParser

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

    dataset = Dataset(
        id=dataset_id,
        name=dataset_in.name,
        description=dataset_in.description,
        folder_path=str(folder_path),
        file_count=0,
        total_size=0,
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
