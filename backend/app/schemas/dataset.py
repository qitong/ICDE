from pydantic import BaseModel, Field
from typing import Optional, List, Any, Literal
from datetime import datetime


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_dataset_id: Optional[str] = None
    crf_version: Optional[str] = None
    patient_id_column: Optional[str] = None
    project_id: Optional[str] = None
    study_name: Optional[str] = None
    version_name: Optional[str] = None


class ColumnInfo(BaseModel):
    name: str
    data_type: str  # numeric, categorical, date, text
    non_null_count: int
    unique_count: int
    sample_values: List[str]


class DatasetFileResponse(BaseModel):
    id: str
    file_name: str
    original_name: str
    file_type: str
    file_size: int
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    parse_status: str
    parse_error: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DatasetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    type: Optional[str] = "RAW"
    file_count: int
    total_size: int
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    files: List[DatasetFileResponse] = []
    parent_dataset_id: Optional[str] = None
    source_dataset_id: Optional[str] = None
    script_id: Optional[str] = None
    crf_version: Optional[str] = None
    patient_id_column: Optional[str] = None
    is_stale: bool = False
    stale_reason: Optional[str] = None
    is_manual: bool = False
    project_id: Optional[str] = None
    study_name: Optional[str] = None
    version_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_type(cls, obj):
        """Convert ORM model to response, handling enum type."""
        data = {
            "id": obj.id,
            "name": obj.name,
            "description": obj.description,
            "type": obj.type.value if obj.type else "RAW",
            "file_count": obj.file_count,
            "total_size": obj.total_size,
            "row_count": obj.row_count,
            "column_count": obj.column_count,
            "files": obj.files,
            "parent_dataset_id": obj.parent_dataset_id,
            "source_dataset_id": obj.source_dataset_id,
            "script_id": obj.script_id,
            "crf_version": obj.crf_version,
            "patient_id_column": obj.patient_id_column,
            "is_stale": obj.is_stale,
            "stale_reason": obj.stale_reason,
            "is_manual": obj.is_manual,
            "project_id": obj.project_id,
            "study_name": obj.study_name,
            "version_name": obj.version_name,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }
        return cls(**data)


class DatasetListResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    file_count: int
    total_size: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FilePreview(BaseModel):
    file_id: str
    file_name: str
    row_count: int
    column_count: int
    columns: List[ColumnInfo]
    sample_rows: List[dict[str, Any]]


class SetRelationshipRequest(BaseModel):
    """Request schema for setting dataset relationships after upload."""
    relationship_type: Literal["none", "version", "derived"]
    parent_dataset_id: Optional[str] = None      # For version relationship
    source_dataset_id: Optional[str] = None      # For derived relationship
    version_name: Optional[str] = None           # Version label (e.g., v2.1)
    is_manual: bool = False                      # Whether manually created (自建)
    description: Optional[str] = None            # Additional description
