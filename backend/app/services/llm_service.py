"""LLM Service for managing multiple LLM providers."""

import json
import logging
import os
from typing import AsyncIterator, Dict, List, Optional, Type
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.models.chat import LLMSetting, Conversation, ChatMessage
from app.models.dataset import Dataset, DatasetFile
from app.models.script import Script
from app.schemas.chat import (
    ChatContext,
    FileContext,
    MentionRef,
    ProviderConfig,
)
from app.services.llm_providers import (
    BaseLLMProvider,
    OpenAIProvider,
    ClaudeProvider,
    GeminiProvider,
    KimiProvider,
    LLMResponse,
)
from app.services.llm_providers.base import LLMMessage

logger = logging.getLogger(__name__)

# Encryption key for API keys - in production, use environment variable
ENCRYPTION_KEY = os.environ.get("LLM_ENCRYPTION_KEY", Fernet.generate_key().decode())


class LLMService:
    """Service for managing LLM providers and chat completions."""

    # Registry of available providers
    PROVIDERS: Dict[str, Type[BaseLLMProvider]] = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "gemini": GeminiProvider,
        "kimi": KimiProvider,
    }

    # Default provider configurations
    DEFAULT_CONFIGS = {
        "openai": {
            "display_name": "OpenAI",
            "model": "gpt-4o",
        },
        "claude": {
            "display_name": "Claude",
            "model": "claude-sonnet-4-20250514",
        },
        "gemini": {
            "display_name": "Gemini",
            "model": "gemini-2.0-flash",
        },
        "kimi": {
            "display_name": "Kimi",
            "model": "moonshot-v1-32k",
        },
    }

    def __init__(self, db: Session):
        self.db = db
        self._fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

    # ============== Encryption ==============

    def _encrypt_api_key(self, api_key: str) -> str:
        """Encrypt an API key for storage."""
        return self._fernet.encrypt(api_key.encode()).decode()

    def _decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt an API key from storage."""
        return self._fernet.decrypt(encrypted_key.encode()).decode()

    # ============== Settings Management ==============

    def initialize_default_settings(self) -> None:
        """Initialize default LLM settings if they don't exist."""
        for provider_name, config in self.DEFAULT_CONFIGS.items():
            existing = self.db.query(LLMSetting).filter(LLMSetting.provider == provider_name).first()
            if not existing:
                setting = LLMSetting(
                    provider=provider_name,
                    display_name=config["display_name"],
                    model=config["model"],
                    enabled=True,
                    is_default=(provider_name == "openai"),
                )
                self.db.add(setting)
        self.db.commit()

    def get_all_settings(self) -> List[ProviderConfig]:
        """Get all LLM provider settings."""
        settings = self.db.query(LLMSetting).all()

        # Initialize if empty
        if not settings:
            self.initialize_default_settings()
            settings = self.db.query(LLMSetting).all()

        result = []
        for setting in settings:
            provider_class = self.PROVIDERS.get(setting.provider)
            available_models = provider_class.available_models if provider_class else []

            result.append(ProviderConfig(
                provider=setting.provider,
                display_name=setting.display_name,
                api_key=None,  # Never return actual API key
                api_key_set=bool(setting.api_key_encrypted),
                api_base_url=setting.api_base_url,
                model=setting.model,
                enabled=setting.enabled,
                is_default=setting.is_default,
                available_models=available_models,
            ))

        return result

    def get_default_provider(self) -> Optional[str]:
        """Get the default provider name."""
        setting = self.db.query(LLMSetting).filter(LLMSetting.is_default == True).first()
        return setting.provider if setting else None

    def update_setting(
        self,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enabled: Optional[bool] = None,
        is_default: Optional[bool] = None,
        api_base_url: Optional[str] = None,
    ) -> ProviderConfig:
        """Update settings for a specific provider."""
        setting = self.db.query(LLMSetting).filter(LLMSetting.provider == provider).first()

        if not setting:
            # Create new setting
            config = self.DEFAULT_CONFIGS.get(provider, {})
            setting = LLMSetting(
                provider=provider,
                display_name=config.get("display_name", provider.title()),
                model=model or config.get("model", ""),
                enabled=enabled if enabled is not None else True,
            )
            self.db.add(setting)

        # Update fields
        if api_key is not None:
            setting.api_key_encrypted = self._encrypt_api_key(api_key) if api_key else None

        if model is not None:
            setting.model = model

        if enabled is not None:
            setting.enabled = enabled

        if api_base_url is not None:
            setting.api_base_url = api_base_url

        if is_default:
            # Clear other defaults first
            self.db.query(LLMSetting).filter(LLMSetting.provider != provider).update({"is_default": False})
            setting.is_default = True

        self.db.commit()
        self.db.refresh(setting)

        provider_class = self.PROVIDERS.get(setting.provider)
        available_models = provider_class.available_models if provider_class else []

        return ProviderConfig(
            provider=setting.provider,
            display_name=setting.display_name,
            api_key=None,
            api_key_set=bool(setting.api_key_encrypted),
            api_base_url=setting.api_base_url,
            model=setting.model,
            enabled=setting.enabled,
            is_default=setting.is_default,
            available_models=available_models,
        )

    # ============== Provider Instantiation ==============

    def get_provider(self, provider_name: Optional[str] = None) -> BaseLLMProvider:
        """Get an instantiated provider with API key."""
        # Use default if not specified
        if not provider_name:
            provider_name = self.get_default_provider() or "openai"

        setting = self.db.query(LLMSetting).filter(LLMSetting.provider == provider_name).first()

        if not setting or not setting.api_key_encrypted:
            raise ValueError(f"API key not configured for provider: {provider_name}")

        if not setting.enabled:
            raise ValueError(f"Provider is disabled: {provider_name}")

        provider_class = self.PROVIDERS.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")

        api_key = self._decrypt_api_key(setting.api_key_encrypted)

        return provider_class(
            api_key=api_key,
            model=setting.model,
            api_base_url=setting.api_base_url,
        )

    # ============== Context Building ==============

    def build_context(
        self,
        project_id: Optional[str] = None,
        mentions: List[MentionRef] = None,
    ) -> ChatContext:
        """Build context information for the LLM including project structure."""
        mentions = mentions or []
        context = ChatContext(project_id=project_id)

        # Get project info
        if project_id:
            from app.models.project import Project
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project:
                context.project_name = project.name

        # Get available datasets
        dataset_query = self.db.query(Dataset)
        if project_id:
            dataset_query = dataset_query.filter(Dataset.project_id == project_id)
        datasets = dataset_query.all()

        for ds in datasets:
            context.available_datasets.append({
                "id": ds.id,
                "name": ds.name,
                "study_name": ds.study_name,
                "version_name": ds.version_name,
                "row_count": ds.row_count,
                "column_count": ds.column_count,
                "type": ds.type.value if ds.type else None,
            })

        # Get available scripts
        scripts = self.db.query(Script).all()
        for script in scripts:
            context.available_scripts.append({
                "id": script.id,
                "name": script.name,
                "display_name": script.display_name,
                "description": script.description,
                "language": script.language,
            })

        # Process mentions to get detailed file context
        for mention in mentions:
            file_context = self._get_file_context(mention)
            if file_context:
                context.mentioned_files.append(file_context)

        return context

    def _get_file_context(self, mention: MentionRef) -> Optional[FileContext]:
        """Get detailed context for a mentioned file."""
        if mention.type == "dataset":
            dataset = self.db.query(Dataset).filter(Dataset.id == mention.id).first()
            if dataset:
                # Get column info from first file
                columns = None
                if dataset.files:
                    first_file = dataset.files[0]
                    if first_file.column_info:
                        try:
                            columns = json.loads(first_file.column_info)
                        except json.JSONDecodeError:
                            pass

                return FileContext(
                    type="dataset",
                    id=dataset.id,
                    name=dataset.name,
                    path=mention.path,
                    study_name=dataset.study_name,
                    version_name=dataset.version_name,
                    row_count=dataset.row_count,
                    column_count=dataset.column_count,
                    columns=columns,
                )

        elif mention.type == "file":
            # Parse file ID (could be "dataset_id:file_id")
            parts = mention.id.split(":")
            if len(parts) == 2:
                file_id = parts[1]
            else:
                file_id = mention.id

            file = self.db.query(DatasetFile).filter(DatasetFile.id == file_id).first()
            if file:
                columns = None
                if file.column_info:
                    try:
                        columns = json.loads(file.column_info)
                    except json.JSONDecodeError:
                        pass

                return FileContext(
                    type="file",
                    id=file.id,
                    name=file.file_name,
                    path=mention.path,
                    row_count=file.row_count,
                    column_count=file.column_count,
                    columns=columns,
                    file_type=file.file_type,
                    file_size=file.file_size,
                )

        elif mention.type == "script":
            script = self.db.query(Script).filter(Script.id == mention.id).first()
            if script:
                params_schema = None
                if script.parameters_schema:
                    try:
                        params_schema = json.loads(script.parameters_schema)
                    except json.JSONDecodeError:
                        pass

                return FileContext(
                    type="script",
                    id=script.id,
                    name=script.name,
                    path=mention.path,
                    language=script.language,
                    description=script.description,
                    parameters_schema=params_schema,
                )

        return None

    def _build_system_prompt(self, context: ChatContext) -> str:
        """Build the system prompt with context information."""
        parts = [
            "You are an AI assistant helping with clinical data analysis and management.",
            "You have access to the following information about the current project:",
        ]

        if context.project_name:
            parts.append(f"\nProject: {context.project_name}")

        if context.available_datasets:
            parts.append("\n\nAvailable Datasets:")
            for ds in context.available_datasets:
                parts.append(f"  - {ds['name']} ({ds.get('study_name', 'N/A')}/{ds.get('version_name', 'N/A')}): "
                           f"{ds.get('row_count', '?')} rows, {ds.get('column_count', '?')} columns")

        if context.available_scripts:
            parts.append("\n\nAvailable Scripts:")
            for script in context.available_scripts:
                parts.append(f"  - {script['display_name'] or script['name']}: {script.get('description', 'No description')[:100]}")

        if context.mentioned_files:
            parts.append("\n\nUser is referencing these specific files:")
            for file in context.mentioned_files:
                parts.append(f"\n  [{file.type.upper()}] {file.name}")
                if file.columns:
                    col_names = [c.get("name", "?") for c in file.columns[:10]]
                    parts.append(f"    Columns: {', '.join(col_names)}")
                    if len(file.columns) > 10:
                        parts.append(f"    ... and {len(file.columns) - 10} more columns")
                if file.description:
                    parts.append(f"    Description: {file.description}")

        parts.append("\n\nProvide helpful, accurate responses based on this context.")

        return "\n".join(parts)

    # ============== Chat Completion ==============

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        mentions: List[MentionRef] = None,
        provider_name: Optional[str] = None,
    ) -> tuple[LLMResponse, str, str]:
        """
        Send a chat message and get a response.

        Returns:
            Tuple of (LLMResponse, conversation_id, message_id)
        """
        mentions = mentions or []

        # Get or create conversation
        conversation = None
        if conversation_id:
            conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()

        if not conversation:
            conversation = Conversation(project_id=project_id)
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

        # Build context
        context = self.build_context(project_id, mentions)

        # Get conversation history
        history_messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at)
            .all()
        )

        # Build messages for LLM
        messages = [LLMMessage(role="system", content=self._build_system_prompt(context))]

        for hist_msg in history_messages:
            messages.append(LLMMessage(role=hist_msg.role, content=hist_msg.content))

        messages.append(LLMMessage(role="user", content=message))

        # Save user message
        user_msg = ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content=message,
            mentions=json.dumps([m.dict() for m in mentions]) if mentions else None,
        )
        self.db.add(user_msg)

        # Get provider and make request
        provider = self.get_provider(provider_name)
        response = await provider.chat(messages)

        # Save assistant message
        assistant_msg = ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=response.content,
            provider=response.provider,
            model=response.model,
            tokens_used=response.usage.get("total_tokens") if response.usage else None,
            status="error" if response.error else "success",
            error_message=response.error,
        )
        self.db.add(assistant_msg)

        # Update conversation title from first message
        if not conversation.title and len(history_messages) == 0:
            # Generate title from first message (truncate to 50 chars)
            conversation.title = message[:50] + ("..." if len(message) > 50 else "")

        self.db.commit()

        return response, conversation.id, assistant_msg.id

    async def stream_chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        mentions: List[MentionRef] = None,
        provider_name: Optional[str] = None,
    ) -> AsyncIterator[tuple[str, str, str]]:
        """
        Stream a chat response.

        Yields:
            Tuples of (content_chunk, conversation_id, message_id)
        """
        mentions = mentions or []

        # Get or create conversation
        conversation = None
        if conversation_id:
            conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()

        if not conversation:
            conversation = Conversation(project_id=project_id)
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

        # Build context
        context = self.build_context(project_id, mentions)

        # Get conversation history
        history_messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at)
            .all()
        )

        # Build messages for LLM
        messages = [LLMMessage(role="system", content=self._build_system_prompt(context))]

        for hist_msg in history_messages:
            messages.append(LLMMessage(role=hist_msg.role, content=hist_msg.content))

        messages.append(LLMMessage(role="user", content=message))

        # Save user message
        user_msg = ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content=message,
            mentions=json.dumps([m.dict() for m in mentions]) if mentions else None,
        )
        self.db.add(user_msg)
        self.db.commit()

        # Create placeholder for assistant message
        assistant_msg = ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content="",
            provider=provider_name,
        )
        self.db.add(assistant_msg)
        self.db.commit()
        self.db.refresh(assistant_msg)

        # Get provider and stream
        provider = self.get_provider(provider_name)
        full_content = ""

        try:
            async for chunk in provider.stream_chat(messages):
                full_content += chunk
                yield chunk, conversation.id, assistant_msg.id

            # Update assistant message with full content
            assistant_msg.content = full_content
            assistant_msg.status = "success"
            assistant_msg.model = provider.model

            # Update conversation title from first message
            if not conversation.title and len(history_messages) == 0:
                conversation.title = message[:50] + ("..." if len(message) > 50 else "")

            self.db.commit()

        except Exception as e:
            assistant_msg.status = "error"
            assistant_msg.error_message = str(e)
            self.db.commit()
            raise

    # ============== Conversation Management ==============

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return self.db.query(Conversation).filter(Conversation.id == conversation_id).first()

    def get_conversation_messages(self, conversation_id: str) -> List[ChatMessage]:
        """Get all messages in a conversation."""
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at)
            .all()
        )

    def list_conversations(self, project_id: Optional[str] = None, limit: int = 50) -> List[Conversation]:
        """List recent conversations."""
        query = self.db.query(Conversation)
        if project_id:
            query = query.filter(Conversation.project_id == project_id)
        return query.order_by(Conversation.updated_at.desc()).limit(limit).all()

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            self.db.delete(conversation)
            self.db.commit()
            return True
        return False
