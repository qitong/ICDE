"""Chat models for conversation persistence and LLM settings."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship
from .base import Base
import uuid


class Conversation(Base):
    """Model for storing chat conversations."""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=True)  # Auto-generated from first message
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    project = relationship("Project")


class ChatMessage(Base):
    """Model for storing individual chat messages."""
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    mentions = Column(Text, nullable=True)  # JSON: [{type, id, path}]
    provider = Column(String(50), nullable=True)  # LLM provider used (openai, claude, etc.)
    model = Column(String(100), nullable=True)  # Specific model used
    tokens_used = Column(Integer, nullable=True)  # Token usage for billing tracking
    status = Column(String(20), default="success")  # "success" | "error"
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class LLMSetting(Base):
    """Model for storing LLM provider settings with encrypted API keys."""
    __tablename__ = "llm_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(50), nullable=False, unique=True)  # "openai" | "claude" | "gemini" | "kimi"
    display_name = Column(String(100), nullable=False)  # Human-readable name
    api_key_encrypted = Column(Text, nullable=True)  # Fernet encrypted API key
    api_base_url = Column(String(500), nullable=True)  # Custom API base URL (for Kimi, etc.)
    model = Column(String(100), nullable=False)  # Default model to use
    is_default = Column(Boolean, default=False)  # Is this the default provider?
    enabled = Column(Boolean, default=True)  # Is this provider enabled?
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
