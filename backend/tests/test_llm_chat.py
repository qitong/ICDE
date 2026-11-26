"""
Tests for LLM chat functionality.

This module tests:
1. LLM connection for each provider (OpenAI, Claude, Gemini, Kimi)
2. Multi-turn conversation context
3. Provider switching within conversations
4. Conversation persistence (save/load/delete)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.chat import Conversation, ChatMessage
from app.services.llm_service import LLMService
from app.services.llm_providers import (
    OpenAIProvider,
    ClaudeProvider,
    GeminiProvider,
    KimiProvider,
    LLMResponse,
)
from app.services.llm_providers.base import LLMMessage


# ============== Fixtures ==============

@pytest.fixture
def llm_service(test_db_with_llm):
    """Create an LLMService instance with a test database."""
    return LLMService(test_db_with_llm)


@pytest.fixture
def mock_openai_completion():
    """Mock OpenAI chat completion response."""
    completion = MagicMock()
    completion.choices = [MagicMock()]
    completion.choices[0].message = MagicMock(content="Hello! I'm an AI assistant.")
    completion.choices[0].finish_reason = "stop"
    completion.model = "gpt-4o"
    completion.usage = MagicMock(
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
    )
    return completion


@pytest.fixture
def mock_claude_completion():
    """Mock Claude message response."""
    response = MagicMock()
    response.content = [MagicMock(type="text", text="Hello from Claude!")]
    response.model = "claude-sonnet-4-20250514"
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=15, output_tokens=25)
    return response


@pytest.fixture
def mock_gemini_completion():
    """Mock Gemini generate content response."""
    response = MagicMock()
    response.text = "Hello from Gemini!"
    response.usage_metadata = MagicMock(
        prompt_token_count=12,
        candidates_token_count=18,
        total_token_count=30,
    )
    return response


@pytest.fixture
def mock_kimi_completion():
    """Mock Kimi (OpenAI-compatible) chat completion response."""
    completion = MagicMock()
    completion.choices = [MagicMock()]
    completion.choices[0].message = MagicMock(content="Hello from Kimi!")
    completion.choices[0].finish_reason = "stop"
    completion.model = "moonshot-v1-32k"
    completion.usage = MagicMock(
        prompt_tokens=8,
        completion_tokens=16,
        total_tokens=24,
    )
    return completion


# ============== Test Classes ==============

class TestLLMConnection:
    """Tests for LLM provider connections."""

    @pytest.mark.asyncio
    async def test_openai_connection(self, mock_openai_completion):
        """Test OpenAI provider connection with mocked client."""
        with patch('openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_completion)

            provider = OpenAIProvider(api_key="sk-test-key", model="gpt-4o")
            messages = [LLMMessage(role="user", content="Hello")]
            response = await provider.chat(messages)

            assert response.content == "Hello! I'm an AI assistant."
            assert response.provider == "openai"
            assert response.model == "gpt-4o"
            assert response.usage["total_tokens"] == 30
            assert response.error is None

    @pytest.mark.asyncio
    async def test_claude_connection(self, mock_claude_completion):
        """Test Claude provider connection with mocked client."""
        with patch('anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.messages.create = AsyncMock(return_value=mock_claude_completion)

            provider = ClaudeProvider(api_key="sk-ant-test-key", model="claude-sonnet-4-20250514")
            messages = [LLMMessage(role="user", content="Hello")]
            response = await provider.chat(messages)

            assert response.content == "Hello from Claude!"
            assert response.provider == "claude"
            assert response.error is None

    @pytest.mark.asyncio
    async def test_gemini_connection(self, mock_gemini_completion):
        """Test Gemini provider connection with mocked client."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                with patch('google.generativeai.GenerationConfig'):
                    mock_model = MagicMock()
                    mock_model_class.return_value = mock_model
                    mock_chat = MagicMock()
                    mock_model.start_chat.return_value = mock_chat
                    mock_chat.send_message_async = AsyncMock(return_value=mock_gemini_completion)

                    provider = GeminiProvider(api_key="test-gemini-key", model="gemini-2.0-flash")
                    messages = [LLMMessage(role="user", content="Hello")]
                    response = await provider.chat(messages)

                    assert response.content == "Hello from Gemini!"
                    assert response.provider == "gemini"
                    assert response.error is None

    @pytest.mark.asyncio
    async def test_kimi_connection(self, mock_kimi_completion):
        """Test Kimi provider connection with mocked client."""
        with patch('openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_kimi_completion)

            provider = KimiProvider(api_key="sk-kimi-test-key", model="moonshot-v1-32k")
            messages = [LLMMessage(role="user", content="Hello")]
            response = await provider.chat(messages)

            assert response.content == "Hello from Kimi!"
            assert response.provider == "kimi"
            assert response.model == "moonshot-v1-32k"
            assert response.error is None

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test error handling for invalid API key."""
        with patch('openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("Invalid API key provided")
            )

            provider = OpenAIProvider(api_key="invalid-key", model="gpt-4o")
            messages = [LLMMessage(role="user", content="Hello")]
            response = await provider.chat(messages)

            assert response.content == ""
            assert response.error is not None
            assert "Invalid API key" in response.error

    @pytest.mark.asyncio
    async def test_openai_validate_api_key(self):
        """Test OpenAI API key validation."""
        with patch('openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.models.list = AsyncMock(return_value=MagicMock())

            provider = OpenAIProvider(api_key="sk-valid-key", model="gpt-4o")
            is_valid = await provider.validate_api_key()

            assert is_valid is True

    @pytest.mark.asyncio
    async def test_openai_validate_api_key_invalid(self):
        """Test OpenAI API key validation with invalid key."""
        with patch('openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.models.list = AsyncMock(side_effect=Exception("Invalid key"))

            provider = OpenAIProvider(api_key="sk-invalid-key", model="gpt-4o")
            is_valid = await provider.validate_api_key()

            assert is_valid is False


class TestMultiTurnConversation:
    """Tests for multi-turn conversation functionality."""

    @pytest.mark.asyncio
    async def test_single_turn(self, llm_service):
        """Test single turn conversation."""
        with patch.object(llm_service, 'get_provider') as mock_get_provider:
            mock_provider = MagicMock(spec=OpenAIProvider)
            mock_provider.chat = AsyncMock(return_value=LLMResponse(
                content="Hello! How can I help you?",
                model="gpt-4o",
                provider="openai",
            ))
            mock_get_provider.return_value = mock_provider

            response, conv_id, msg_id = await llm_service.chat(
                message="Hello!",
                provider_name="openai",
            )

            assert response.content == "Hello! How can I help you?"
            assert conv_id is not None
            assert msg_id is not None

    @pytest.mark.asyncio
    async def test_multi_turn_context(self, llm_service):
        """Test multi-turn conversation maintains context."""
        with patch.object(llm_service, 'get_provider') as mock_get_provider:
            mock_provider = MagicMock(spec=OpenAIProvider)
            call_count = 0

            async def chat_side_effect(messages, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    assert len(messages) == 2  # system + user
                elif call_count == 2:
                    assert len(messages) == 4  # system + user + assistant + user
                    assert messages[1].content == "What is Python?"
                    assert messages[2].content == "Python is a programming language."
                    assert messages[3].content == "Tell me more about it."

                return LLMResponse(
                    content="Python is a programming language." if call_count == 1 else "More details...",
                    model="gpt-4o",
                    provider="openai",
                )

            mock_provider.chat = AsyncMock(side_effect=chat_side_effect)
            mock_get_provider.return_value = mock_provider

            _, conv_id, _ = await llm_service.chat(
                message="What is Python?",
                provider_name="openai",
            )

            _, conv_id2, _ = await llm_service.chat(
                message="Tell me more about it.",
                conversation_id=conv_id,
                provider_name="openai",
            )

            assert conv_id == conv_id2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_conversation_title_generation(self, llm_service):
        """Test that conversation title is auto-generated from first message."""
        with patch.object(llm_service, 'get_provider') as mock_get_provider:
            mock_provider = MagicMock(spec=OpenAIProvider)
            mock_provider.chat = AsyncMock(return_value=LLMResponse(
                content="Response",
                model="gpt-4o",
                provider="openai",
            ))
            mock_get_provider.return_value = mock_provider

            _, conv_id, _ = await llm_service.chat(
                message="This is a test message for title generation",
                provider_name="openai",
            )

            conversation = llm_service.get_conversation(conv_id)
            assert conversation is not None
            assert conversation.title is not None
            assert "This is a test message" in conversation.title


class TestProviderSwitching:
    """Tests for switching LLM providers within conversations."""

    @pytest.mark.asyncio
    async def test_switch_provider_same_conversation(self, llm_service):
        """Test switching provider within the same conversation."""
        call_history = []

        with patch.object(llm_service, 'get_provider') as mock_get_provider:
            def create_mock_provider(provider_name):
                mock_provider = MagicMock()

                async def chat_func(messages, *args, **kwargs):
                    call_history.append({
                        "provider": provider_name,
                        "message_count": len(messages),
                    })
                    return LLMResponse(
                        content=f"Response from {provider_name}",
                        model=f"{provider_name}-model",
                        provider=provider_name,
                    )

                mock_provider.chat = AsyncMock(side_effect=chat_func)
                return mock_provider

            def get_provider_side_effect(provider_name=None):
                return create_mock_provider(provider_name or "openai")

            mock_get_provider.side_effect = get_provider_side_effect

            _, conv_id, _ = await llm_service.chat(
                message="Hello from OpenAI",
                provider_name="openai",
            )

            _, conv_id2, _ = await llm_service.chat(
                message="Now using Claude",
                conversation_id=conv_id,
                provider_name="claude",
            )

            assert conv_id == conv_id2
            assert len(call_history) == 2
            assert call_history[0]["provider"] == "openai"
            assert call_history[1]["provider"] == "claude"
            assert call_history[1]["message_count"] > call_history[0]["message_count"]

    def test_default_provider(self, llm_service):
        """Test getting/setting default provider."""
        default = llm_service.get_default_provider()
        assert default in [None, "openai"]

        llm_service.update_setting(
            provider="claude",
            api_key="test-key",
            is_default=True,
        )

        new_default = llm_service.get_default_provider()
        assert new_default == "claude"


class TestConversationPersistence:
    """Tests for conversation save/load/delete functionality."""

    def test_save_conversation(self, llm_service):
        """Test saving a conversation to the database."""
        conv = Conversation(
            title="Test Conversation",
            project_id=None,
        )
        llm_service.db.add(conv)
        llm_service.db.commit()

        msg1 = ChatMessage(
            conversation_id=conv.id,
            role="user",
            content="Hello",
        )
        msg2 = ChatMessage(
            conversation_id=conv.id,
            role="assistant",
            content="Hi there!",
            provider="openai",
            model="gpt-4o",
        )
        llm_service.db.add(msg1)
        llm_service.db.add(msg2)
        llm_service.db.commit()

        loaded_conv = llm_service.get_conversation(conv.id)
        assert loaded_conv is not None
        assert loaded_conv.title == "Test Conversation"

    def test_load_conversation(self, llm_service):
        """Test loading a conversation from the database."""
        conv = Conversation(title="Load Test")
        llm_service.db.add(conv)
        llm_service.db.commit()

        msg = ChatMessage(
            conversation_id=conv.id,
            role="user",
            content="Test message",
        )
        llm_service.db.add(msg)
        llm_service.db.commit()

        loaded = llm_service.get_conversation(conv.id)
        messages = llm_service.get_conversation_messages(conv.id)

        assert loaded is not None
        assert loaded.id == conv.id
        assert len(messages) == 1
        assert messages[0].content == "Test message"

    def test_list_conversations(self, llm_service):
        """Test listing all conversations."""
        for i in range(3):
            conv = Conversation(title=f"Conv {i}")
            llm_service.db.add(conv)
        llm_service.db.commit()

        conversations = llm_service.list_conversations(limit=10)
        assert len(conversations) == 3

    def test_delete_conversation(self, llm_service):
        """Test deleting a conversation."""
        conv = Conversation(title="To Delete")
        llm_service.db.add(conv)
        llm_service.db.commit()
        conv_id = conv.id

        msg = ChatMessage(
            conversation_id=conv.id,
            role="user",
            content="Will be deleted",
        )
        llm_service.db.add(msg)
        llm_service.db.commit()

        assert llm_service.get_conversation(conv_id) is not None

        result = llm_service.delete_conversation(conv_id)
        assert result is True
        assert llm_service.get_conversation(conv_id) is None

        messages = llm_service.get_conversation_messages(conv_id)
        assert len(messages) == 0

    def test_conversation_messages_order(self, llm_service):
        """Test that messages are returned in correct order."""
        conv = Conversation(title="Order Test")
        llm_service.db.add(conv)
        llm_service.db.commit()

        for i in range(5):
            msg = ChatMessage(
                conversation_id=conv.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )
            llm_service.db.add(msg)
            llm_service.db.commit()

        messages = llm_service.get_conversation_messages(conv.id)

        assert len(messages) == 5
        for i, msg in enumerate(messages):
            assert msg.content == f"Message {i}"


class TestStreamingChat:
    """Tests for streaming chat functionality."""

    @pytest.mark.asyncio
    async def test_stream_chat_openai(self, llm_service):
        """Test streaming chat with OpenAI provider."""
        with patch.object(llm_service, 'get_provider') as mock_get_provider:
            mock_provider = MagicMock(spec=OpenAIProvider)
            mock_provider.model = "gpt-4o"

            async def stream_generator(*args, **kwargs):
                chunks = ["Hello", " ", "World", "!"]
                for chunk in chunks:
                    yield chunk

            mock_provider.stream_chat = MagicMock(return_value=stream_generator())
            mock_get_provider.return_value = mock_provider

            collected_chunks = []
            async for chunk, conv_id, msg_id in llm_service.stream_chat(
                message="Say hello",
                provider_name="openai",
            ):
                collected_chunks.append(chunk)

            assert "".join(collected_chunks) == "Hello World!"


class TestContextBuilding:
    """Tests for context building with mentions."""

    def test_build_system_prompt(self, llm_service):
        """Test building system prompt with context."""
        from app.schemas.chat import ChatContext

        context = ChatContext(
            project_name="Test Project",
            available_datasets=[
                {
                    "id": "ds-1",
                    "name": "ADSL",
                    "study_name": "STUDY001",
                    "version_name": "v1.0",
                    "row_count": 100,
                    "column_count": 20,
                }
            ],
            available_scripts=[
                {
                    "id": "sc-1",
                    "name": "demographics.py",
                    "display_name": "Demographics Script",
                    "description": "Generate demographics table",
                }
            ],
        )

        prompt = llm_service._build_system_prompt(context)

        assert "Test Project" in prompt
        assert "ADSL" in prompt
        assert "STUDY001" in prompt
        assert "Demographics Script" in prompt


class TestLLMSettings:
    """Tests for LLM settings management."""

    def test_initialize_default_settings(self, llm_service):
        """Test initializing default LLM settings."""
        llm_service.initialize_default_settings()

        settings = llm_service.get_all_settings()
        provider_names = [s.provider for s in settings]

        assert "openai" in provider_names
        assert "claude" in provider_names
        assert "gemini" in provider_names
        assert "kimi" in provider_names

    def test_update_setting(self, llm_service):
        """Test updating provider settings."""
        llm_service.initialize_default_settings()

        updated = llm_service.update_setting(
            provider="openai",
            api_key="sk-test-new-key",
            model="gpt-4o-mini",
            enabled=True,
        )

        assert updated.provider == "openai"
        assert updated.api_key_set is True
        assert updated.model == "gpt-4o-mini"

    def test_encryption_decryption(self, llm_service):
        """Test API key encryption and decryption."""
        original_key = "sk-test-secret-key-12345"

        encrypted = llm_service._encrypt_api_key(original_key)
        decrypted = llm_service._decrypt_api_key(encrypted)

        assert encrypted != original_key
        assert decrypted == original_key

    def test_get_provider_not_configured(self, llm_service):
        """Test error when getting unconfigured provider."""
        with pytest.raises(ValueError, match="API key not configured"):
            llm_service.get_provider("openai")

    def test_get_provider_disabled(self, llm_service):
        """Test error when provider is disabled."""
        llm_service.update_setting(
            provider="openai",
            api_key="test-key",
            enabled=False,
        )

        with pytest.raises(ValueError, match="disabled"):
            llm_service.get_provider("openai")
