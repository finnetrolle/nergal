"""Tests for memory service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from nergal.memory.service import MemoryService
from nergal.database.models import (
    User,
    UserProfile,
    ProfileFact,
    ConversationMessage,
    ConversationSession,
    UserMemoryContext,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database connection."""
    db = MagicMock()
    db.fetchrow = AsyncMock()
    db.fetch = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.memory.short_term_max_messages = 50
    return settings


@pytest.fixture
def sample_user():
    """Create a sample user."""
    return User(
        id=12345,
        telegram_username="testuser",
        first_name="Test",
        last_name="User",
        language_code="en",
        is_allowed=True,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 2, 12, 0, 0),
    )


@pytest.fixture
def sample_profile():
    """Create a sample user profile."""
    return UserProfile(
        id=uuid4(),
        user_id=12345,
        preferred_name="Tester",
        age=30,
        location="Moscow",
        timezone="Europe/Moscow",
        occupation="Developer",
        languages=["ru", "en"],
        interests=["coding", "AI"],
        expertise_areas=["Python"],
        communication_style="casual",
        custom_attributes={"key": "value"},
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 2, 12, 0, 0),
    )


@pytest.fixture
def sample_fact():
    """Create a sample profile fact."""
    return ProfileFact(
        id=uuid4(),
        user_id=12345,
        fact_type="personal",
        fact_key="favorite_color",
        fact_value="blue",
        confidence=0.9,
        source="conversation",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 2, 12, 0, 0),
        expires_at=None,
    )


@pytest.fixture
def sample_message():
    """Create a sample conversation message."""
    return ConversationMessage(
        id=uuid4(),
        user_id=12345,
        session_id="session-123",
        role="user",
        content="Hello, bot!",
        agent_type="default",
        tokens_used=10,
        processing_time_ms=100,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_session():
    """Create a sample conversation session."""
    return ConversationSession(
        id="session-123",
        user_id=12345,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        ended_at=None,
        message_count=5,
        metadata={"key": "value"},
    )


# =============================================================================
# Test MemoryService - User Management
# =============================================================================

class TestMemoryServiceUserManagement:
    """Tests for MemoryService user management methods."""

    @pytest.mark.asyncio
    async def test_get_or_create_user(self, mock_db, sample_user):
        """Test getting or creating a user."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            # Mock the repository method
            service._user_repo.create_or_update = AsyncMock(return_value=sample_user)
            
            user = await service.get_or_create_user(
                user_id=12345,
                telegram_username="testuser",
                first_name="Test",
                last_name="User",
                language_code="en",
            )
            
            assert user.id == 12345
            assert user.telegram_username == "testuser"
            service._user_repo.create_or_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_found(self, mock_db, sample_user):
        """Test getting a user that exists."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._user_repo.get_by_id = AsyncMock(return_value=sample_user)
            
            user = await service.get_user(12345)
            
            assert user is not None
            assert user.id == 12345

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, mock_db):
        """Test getting a user that doesn't exist."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._user_repo.get_by_id = AsyncMock(return_value=None)
            
            user = await service.get_user(99999)
            
            assert user is None


# =============================================================================
# Test MemoryService - Short-term Memory
# =============================================================================

class TestMemoryServiceShortTermMemory:
    """Tests for MemoryService short-term memory methods."""

    @pytest.mark.asyncio
    async def test_add_message(self, mock_db, sample_message):
        """Test adding a message to conversation history."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._conversation_repo.add_message = AsyncMock(return_value=sample_message)
            
            message = await service.add_message(
                user_id=12345,
                session_id="session-123",
                role="user",
                content="Hello, bot!",
            )
            
            assert message is not None
            assert message.content == "Hello, bot!"

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, mock_db, sample_message):
        """Test getting conversation history."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._conversation_repo.get_messages = AsyncMock(return_value=[sample_message])
            
            messages = await service.get_conversation_history(user_id=12345)
            
            assert len(messages) == 1
            assert messages[0].content == "Hello, bot!"

    @pytest.mark.asyncio
    async def test_get_conversation_history_with_limit(self, mock_db, sample_message):
        """Test getting conversation history with custom limit."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._conversation_repo.get_messages = AsyncMock(return_value=[sample_message])
            
            messages = await service.get_conversation_history(user_id=12345, limit=10)
            
            service._conversation_repo.get_messages.assert_called_once_with(
                user_id=12345,
                session_id=None,
                limit=10,
            )

    @pytest.mark.asyncio
    async def test_get_recent_messages(self, mock_db, sample_message):
        """Test getting recent messages."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._conversation_repo.get_recent_messages = AsyncMock(return_value=[sample_message])
            
            messages = await service.get_recent_messages(user_id=12345)
            
            assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_get_or_create_session(self, mock_db, sample_session):
        """Test getting or creating a session."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._conversation_repo.create_session = AsyncMock(return_value=sample_session)
            
            session = await service.get_or_create_session(
                user_id=12345,
                session_id="session-123",
            )
            
            assert session is not None
            assert session.user_id == 12345

    @pytest.mark.asyncio
    async def test_get_active_session(self, mock_db, sample_session):
        """Test getting active session."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._conversation_repo.get_active_session = AsyncMock(return_value=sample_session)
            
            session = await service.get_active_session(12345)
            
            assert session is not None

    @pytest.mark.asyncio
    async def test_end_session(self, mock_db, sample_session):
        """Test ending a session."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            ended_session = sample_session.model_copy(update={"ended_at": datetime(2024, 1, 1, 13, 0, 0)})
            service._conversation_repo.end_session = AsyncMock(return_value=ended_session)
            
            session = await service.end_session("session-123")
            
            assert session is not None
            assert session.ended_at is not None


# =============================================================================
# Test MemoryService - Long-term Memory
# =============================================================================

class TestMemoryServiceLongTermMemory:
    """Tests for MemoryService long-term memory methods."""

    @pytest.mark.asyncio
    async def test_get_user_profile(self, mock_db, sample_profile):
        """Test getting user profile."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._profile_repo.get_profile = AsyncMock(return_value=sample_profile)
            
            profile = await service.get_user_profile(12345)
            
            assert profile is not None
            assert profile.user_id == 12345

    @pytest.mark.asyncio
    async def test_update_user_profile(self, mock_db, sample_profile):
        """Test updating user profile."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._profile_repo.create_or_update_profile = AsyncMock(return_value=sample_profile)
            
            profile = await service.update_user_profile(
                user_id=12345,
                preferred_name="NewName",
                location="New York",
            )
            
            assert profile is not None
            service._profile_repo.create_or_update_profile.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_facts(self, mock_db, sample_fact):
        """Test getting user facts."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._profile_repo.get_facts = AsyncMock(return_value=[sample_fact])
            
            facts = await service.get_user_facts(12345)
            
            assert len(facts) == 1
            assert facts[0].fact_key == "favorite_color"

    @pytest.mark.asyncio
    async def test_get_user_facts_with_type_filter(self, mock_db, sample_fact):
        """Test getting user facts with type filter."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._profile_repo.get_facts = AsyncMock(return_value=[sample_fact])
            
            facts = await service.get_user_facts(12345, fact_type="personal")
            
            service._profile_repo.get_facts.assert_called_once_with(12345, "personal")

    @pytest.mark.asyncio
    async def test_add_user_fact(self, mock_db, sample_fact):
        """Test adding a user fact."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._profile_repo.upsert_fact = AsyncMock(return_value=sample_fact)
            
            fact = await service.add_user_fact(
                user_id=12345,
                fact_type="personal",
                fact_key="favorite_color",
                fact_value="blue",
                confidence=0.9,
            )
            
            assert fact is not None
            assert fact.fact_value == "blue"

    @pytest.mark.asyncio
    async def test_remove_user_fact(self, mock_db):
        """Test removing a user fact."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._profile_repo.delete_fact = AsyncMock(return_value=True)
            
            result = await service.remove_user_fact(
                user_id=12345,
                fact_type="personal",
                fact_key="favorite_color",
            )
            
            assert result is True


# =============================================================================
# Test MemoryService - Memory Context
# =============================================================================

class TestMemoryServiceMemoryContext:
    """Tests for MemoryService memory context methods."""

    @pytest.mark.asyncio
    async def test_get_memory_context(self, mock_db, sample_user, sample_profile, sample_fact, sample_message, sample_session):
        """Test getting complete memory context."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            # Mock all repository methods
            service._user_repo.get_by_id = AsyncMock(return_value=sample_user)
            service._profile_repo.get_profile = AsyncMock(return_value=sample_profile)
            service._profile_repo.get_facts = AsyncMock(return_value=[sample_fact])
            service._conversation_repo.get_recent_messages = AsyncMock(return_value=[sample_message])
            service._conversation_repo.get_active_session = AsyncMock(return_value=sample_session)
            
            context = await service.get_memory_context(12345)
            
            assert context.user.id == 12345
            assert context.profile is not None
            assert len(context.facts) == 1
            assert len(context.recent_messages) == 1
            assert context.current_session is not None

    @pytest.mark.asyncio
    async def test_get_memory_context_without_history(self, mock_db, sample_user, sample_profile, sample_fact, sample_session):
        """Test getting memory context without history."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._user_repo.get_by_id = AsyncMock(return_value=sample_user)
            service._profile_repo.get_profile = AsyncMock(return_value=sample_profile)
            service._profile_repo.get_facts = AsyncMock(return_value=[sample_fact])
            service._conversation_repo.get_active_session = AsyncMock(return_value=sample_session)
            
            context = await service.get_memory_context(12345, include_history=False)
            
            assert len(context.recent_messages) == 0

    @pytest.mark.asyncio
    async def test_get_memory_context_user_not_exists(self, mock_db, sample_profile, sample_fact, sample_message, sample_session):
        """Test getting memory context when user doesn't exist."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._user_repo.get_by_id = AsyncMock(return_value=None)
            service._profile_repo.get_profile = AsyncMock(return_value=sample_profile)
            service._profile_repo.get_facts = AsyncMock(return_value=[sample_fact])
            service._conversation_repo.get_recent_messages = AsyncMock(return_value=[sample_message])
            service._conversation_repo.get_active_session = AsyncMock(return_value=sample_session)
            
            context = await service.get_memory_context(12345)
            
            # Should create a minimal user
            assert context.user.id == 12345

    @pytest.mark.asyncio
    async def test_get_context_for_agent(self, mock_db, sample_user, sample_profile, sample_fact, sample_message, sample_session):
        """Test getting context formatted for agent use."""
        with patch("nergal.memory.service.get_database", return_value=mock_db), \
             patch("nergal.memory.service.get_settings") as mock_get_settings:
            mock_get_settings.return_value.memory.short_term_max_messages = 50
            service = MemoryService(db=mock_db)
            
            service._user_repo.get_by_id = AsyncMock(return_value=sample_user)
            service._profile_repo.get_profile = AsyncMock(return_value=sample_profile)
            service._profile_repo.get_facts = AsyncMock(return_value=[sample_fact])
            service._conversation_repo.get_recent_messages = AsyncMock(return_value=[sample_message])
            service._conversation_repo.get_active_session = AsyncMock(return_value=sample_session)
            
            context = await service.get_context_for_agent(12345)
            
            assert "user_id" in context
            assert "user_name" in context
            assert "profile_summary" in context
            assert context["user_id"] == 12345
