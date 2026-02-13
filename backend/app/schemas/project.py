from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DatasetSummary(BaseModel):
    """Summary of a dataset for the tree view."""
    id: str
    name: str
    type: str
    file_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class StudyVersion(BaseModel):
    """A version within a study."""
    name: str
    datasets: List[DatasetSummary]


class Study(BaseModel):
    """A study containing multiple versions."""
    name: str
    versions: List[StudyVersion]


class ProjectTree(BaseModel):
    """Hierarchical tree structure of a project."""
    project_id: str
    project_name: str
    studies: List[Study]
