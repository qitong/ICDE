"""
Pydantic schemas for Script API.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ============ Parameter Schema Types ============

class ParameterProperty(BaseModel):
    """Schema for a single parameter property."""
    type: str  # DataFrame, string, int, float, list, dict, etc.
    description: str
    enum: Optional[List[str]] = None  # For categorical parameters
    default: Optional[Any] = None
    items: Optional[Dict[str, Any]] = None  # For array types


class ParametersSchema(BaseModel):
    """JSON Schema format for function parameters (OpenAI-compatible)."""
    type: str = "object"
    properties: Dict[str, ParameterProperty]
    required: List[str] = []


class ReturnsSchema(BaseModel):
    """Schema for function return value."""
    type: str  # DataFrame, dict, list, int, float, string, etc.
    description: str
    properties: Optional[Dict[str, Any]] = None  # For dict/object return types


class FunctionDefinition(BaseModel):
    """Definition of a function provided by the script."""
    name: str
    description: str
    is_main: bool = False  # Whether this is the main entry point


class ExampleCall(BaseModel):
    """Example of how to call the script."""
    input: str  # e.g., "count_patients(adsl_df, population='safety')"
    output: str  # e.g., "{'total': 95, 'by_arm': {'Treatment A': 38, ...}}"
    description: Optional[str] = None


# ============ Script CRUD Schemas ============

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
    # New structured metadata
    parameters_schema: Optional[ParametersSchema] = None
    returns_schema: Optional[ReturnsSchema] = None
    functions: Optional[List[FunctionDefinition]] = None
    use_cases: Optional[List[str]] = None
    example_calls: Optional[List[ExampleCall]] = None


class ScriptUpdate(BaseModel):
    """Schema for updating a script."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    code: Optional[str] = Field(None, min_length=1)
    keywords: Optional[List[str]] = None
    input_requirements: Optional[str] = None
    output_description: Optional[str] = None
    # New structured metadata
    parameters_schema: Optional[ParametersSchema] = None
    returns_schema: Optional[ReturnsSchema] = None
    functions: Optional[List[FunctionDefinition]] = None
    use_cases: Optional[List[str]] = None
    example_calls: Optional[List[ExampleCall]] = None


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
    # New structured metadata
    parameters_schema: Optional[ParametersSchema] = None
    returns_schema: Optional[ReturnsSchema] = None
    functions: Optional[List[FunctionDefinition]] = None
    use_cases: Optional[List[str]] = None
    example_calls: Optional[List[ExampleCall]] = None
    # Origin and stats
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
        import json

        def parse_json_field(field_value):
            if field_value:
                try:
                    return json.loads(field_value)
                except (json.JSONDecodeError, TypeError):
                    return None
            return None

        keywords = parse_json_field(script.keywords)
        parameters_schema = parse_json_field(script.parameters_schema)
        returns_schema = parse_json_field(script.returns_schema)
        functions = parse_json_field(script.functions)
        use_cases = parse_json_field(script.use_cases)
        example_calls = parse_json_field(script.example_calls)

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
            parameters_schema=parameters_schema,
            returns_schema=returns_schema,
            functions=functions,
            use_cases=use_cases,
            example_calls=example_calls,
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
