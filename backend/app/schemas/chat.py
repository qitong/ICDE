"""Pydantic schemas for chat functionality."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


# ============== Mention/Reference Types ==============

class MentionRef(BaseModel):
    """Reference to a file or dataset mentioned with @ in the chat."""
    type: Literal["dataset", "file", "script"]  # Type of reference
    id: str  # ID of the referenced item
    path: str  # Display path like "@ADSL/ADSL.xlsx"
    name: Optional[str] = None  # Human-readable name

    # Optional metadata that gets populated when building context
    metadata: Optional[Dict[str, Any]] = None


# ============== Chat Message Types ==============

class ChatMessageCreate(BaseModel):
    """Schema for creating a new chat message."""
    content: str = Field(..., min_length=1)
    mentions: List[MentionRef] = Field(default_factory=list)
    conversation_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """Schema for chat message response."""
    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    mentions: Optional[List[MentionRef]] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    status: str = "success"
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Convert ORM object to response, parsing JSON fields."""
        import json
        mentions = None
        if obj.mentions:
            try:
                mentions = json.loads(obj.mentions)
            except json.JSONDecodeError:
                mentions = None

        return cls(
            id=obj.id,
            conversation_id=obj.conversation_id,
            role=obj.role,
            content=obj.content,
            mentions=mentions,
            provider=obj.provider,
            model=obj.model,
            tokens_used=obj.tokens_used,
            status=obj.status,
            error_message=obj.error_message,
            created_at=obj.created_at,
        )


# ============== Chat Request/Response Types ==============

class ChatRequest(BaseModel):
    """Schema for chat request to get AI response."""
    message: str = Field(..., min_length=1)
    mentions: List[MentionRef] = Field(default_factory=list)
    conversation_id: Optional[str] = None
    provider: str = "openai"  # kimi | gemini | claude | openai
    project_id: Optional[str] = None
    stream: bool = True  # Whether to use streaming response


class ChatResponse(BaseModel):
    """Schema for non-streaming chat response."""
    message: str
    conversation_id: str
    message_id: str
    provider: str
    model: Optional[str] = None
    usage: Optional[Dict[str, int]] = None  # token usage stats


class StreamChunk(BaseModel):
    """Schema for streaming response chunks."""
    type: Literal["content", "done", "error"]
    content: Optional[str] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    error: Optional[str] = None


# ============== Conversation Types ==============

class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""
    title: Optional[str] = None
    project_id: Optional[str] = None


class ConversationResponse(BaseModel):
    """Schema for conversation response."""
    id: str
    title: Optional[str] = None
    project_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    """Conversation response including all messages."""
    messages: List[ChatMessageResponse] = Field(default_factory=list)


# ============== LLM Settings Types ==============

class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""
    provider: str  # "openai" | "claude" | "gemini" | "kimi"
    display_name: str
    api_key: Optional[str] = None  # Will be masked in responses
    api_key_set: bool = False  # Indicates if API key is configured
    api_base_url: Optional[str] = None
    model: str
    enabled: bool = True
    is_default: bool = False
    available_models: List[str] = Field(default_factory=list)  # Available models for this provider


class LLMSettingsResponse(BaseModel):
    """Response schema for LLM settings."""
    default_provider: Optional[str] = None
    providers: List[ProviderConfig]


class LLMSettingUpdate(BaseModel):
    """Schema for updating a single LLM provider setting."""
    api_key: Optional[str] = None  # New API key (or None to keep existing)
    api_base_url: Optional[str] = None
    model: Optional[str] = None
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None


class LLMSettingsUpdate(BaseModel):
    """Schema for updating multiple LLM settings at once."""
    default_provider: Optional[str] = None
    providers: Dict[str, LLMSettingUpdate] = Field(default_factory=dict)


# ============== Context Building Types ==============

class FileContext(BaseModel):
    """Context information for a file reference."""
    type: str  # "dataset" | "file" | "script"
    id: str
    name: str
    path: str

    # Dataset-specific
    study_name: Optional[str] = None
    version_name: Optional[str] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    columns: Optional[List[Dict[str, Any]]] = None

    # Script-specific
    language: Optional[str] = None
    description: Optional[str] = None
    parameters_schema: Optional[Dict[str, Any]] = None

    # File-specific
    file_type: Optional[str] = None
    file_size: Optional[int] = None


class ChatContext(BaseModel):
    """Full context passed to LLM including project structure."""
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    available_datasets: List[Dict[str, Any]] = Field(default_factory=list)
    available_scripts: List[Dict[str, Any]] = Field(default_factory=list)
    mentioned_files: List[FileContext] = Field(default_factory=list)
