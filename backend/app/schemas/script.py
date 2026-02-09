"""
Pydantic schemas for Script API.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ScriptCreate(BaseModel):
    """Schema for creating a new script."""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)
    keywords: Optional[List[str]] = None
    language: str = Field(default="python", max_length=20)
    input_requirements: Optional[str] = None
    output_description: Optional[str] = None
    created_by: str = Field(default="user", max_length=50)
    created_from_prompt: Optional[str] = None


class ScriptUpdate(BaseModel):
    """Schema for updating a script."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    code: Optional[str] = Field(None, min_length=1)
    keywords: Optional[List[str]] = None
    input_requirements: Optional[str] = None
    output_description: Optional[str] = None


class ScriptResponse(BaseModel):
    """Schema for script response."""
    id: str
    name: str
    display_name: str
    description: str
    code: str
    keywords: Optional[List[str]] = None
    language: str
    input_requirements: Optional[str] = None
    output_description: Optional[str] = None
    created_by: str
    created_from_prompt: Optional[str] = None
    usage_count: int
    last_used_at: Optional[datetime] = None
    version: int
    parent_script_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm(cls, script):
        """Convert ORM model to response schema."""
        keywords = None
        if script.keywords:
            import json
            try:
                keywords = json.loads(script.keywords)
            except (json.JSONDecodeError, TypeError):
                keywords = None

        return cls(
            id=script.id,
            name=script.name,
            display_name=script.display_name,
            description=script.description,
            code=script.code,
            keywords=keywords,
            language=script.language,
            input_requirements=script.input_requirements,
            output_description=script.output_description,
            created_by=script.created_by,
            created_from_prompt=script.created_from_prompt,
            usage_count=script.usage_count,
            last_used_at=script.last_used_at,
            version=script.version,
            parent_script_id=script.parent_script_id,
            created_at=script.created_at,
            updated_at=script.updated_at,
        )


class DeriveDatasetRequest(BaseModel):
    """Schema for deriving a dataset with a script."""
    script_id: str
    output_name: str = Field(..., min_length=1, max_length=255)
