from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


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
    file_count: int
    total_size: int
    files: List[DatasetFileResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
