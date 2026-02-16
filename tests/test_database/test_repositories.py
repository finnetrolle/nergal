"""Tests for database repositories."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import UUID, uuid4

from nergal.database.repositories import (
    UserRepository,
    ProfileRepository,
    ConversationRepository,
    record_to_user,
    record_to_user_profile,
    record_to_profile_fact,
    record_to_conversation_message,
    record_to_conversation_session,
)
from nergal.database.models import (
    User,
    UserProfile,
    ProfileFact,
    ConversationMessage,
    ConversationSession,
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
def sample_uuid():
    """Create a sample UUID."""
    return uuid4()


@pytest.fixture
def sample_user_record():
    """Create a sample user database record."""
    return {
        "id": 12345,
        "telegram_username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "language_code": "en",
        "is_allowed": True,
        "created_at": datetime(2024, 1, 1, 12, 0, 0),
        "updated_at": datetime(2024, 1, 2, 12, 0, 0),
    }


@pytest.fixture
def sample_profile_record(sample_uuid):
    """Create a sample user profile database record."""
    return {
        "id": sample_uuid,
        "user_id": 12345,
        "preferred_name": "Tester",
        "age": 30,
        "location": "Moscow",
        "timezone": "Europe/Moscow",
        "occupation": "Developer",
        "languages": ["ru", "en"],
        "interests": ["coding", "AI"],
        "expertise_areas": ["Python"],
        "communication_style": "casual",
        "custom_attributes": {"key": "value"},
        "created_at": datetime(2024, 1, 1, 12, 0, 0),
        "updated_at": datetime(2024, 1, 2, 12, 0, 0),
    }


@pytest.fixture
def sample_fact_record(sample_uuid):
    """Create a sample profile fact database record."""
    return {
        "id": sample_uuid,
        "user_id": 12345,
        "fact_type": "personal",
        "fact_key": "favorite_color",
        "fact_value": "blue",
        "confidence": 0.9,
        "source": "conversation",
        "created_at": datetime(2024, 1, 1, 12, 0, 0),
        "updated_at": datetime(2024, 1, 2, 12, 0, 0),
        "expires_at": None,
    }


@pytest.fixture
def sample_message_record(sample_uuid):
    """Create a sample conversation message database record."""
    return {
        "id": sample_uuid,
        "user_id": 12345,
        "session_id": "session-123",
        "role": "user",
        "content": "Hello, bot!",
        "agent_type": "default",
        "tokens_used": 10,
        "processing_time_ms": 100,
        "created_at": datetime(2024, 1, 1, 12, 0, 0),
    }


@pytest.fixture
def sample_session_record():
    """Create a sample conversation session database record."""
    return {
        "id": "session-123",
        "user_id": 12345,
        "started_at": datetime(2024, 1, 1, 12, 0, 0),
        "ended_at": None,
        "message_count": 5,
        "metadata": {"key": "value"},
    }


# =============================================================================
# Record Conversion Tests
# =============================================================================

class TestRecordConversions:
    """Tests for record-to-model conversion functions."""

    def test_record_to_user(self, sample_user_record):
        """Test converting a record to User model."""
        user = record_to_user(sample_user_record)
        
        assert isinstance(user, User)
        assert user.id == 12345
        assert user.telegram_username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.language_code == "en"
        assert user.is_allowed is True

    def test_record_to_user_missing_is_allowed(self, sample_user_record):
        """Test converting a record without is_allowed field."""
        del sample_user_record["is_allowed"]
        user = record_to_user(sample_user_record)
        
        assert user.is_allowed is False  # Default value

    def test_record_to_user_profile(self, sample_profile_record):
        """Test converting a record to UserProfile model."""
        profile = record_to_user_profile(sample_profile_record)
        
        assert isinstance(profile, UserProfile)
        assert profile.user_id == 12345
        assert profile.preferred_name == "Tester"
        assert profile.age == 30
        assert profile.location == "Moscow"
        assert profile.languages == ["ru", "en"]
        assert profile.interests == ["coding", "AI"]

    def test_record_to_profile_fact(self, sample_fact_record):
        """Test converting a record to ProfileFact model."""
        fact = record_to_profile_fact(sample_fact_record)
        
        assert isinstance(fact, ProfileFact)
        assert fact.user_id == 12345
        assert fact.fact_type == "personal"
        assert fact.fact_key == "favorite_color"
        assert fact.fact_value == "blue"
        assert fact.confidence == 0.9

    def test_record_to_conversation_message(self, sample_message_record):
        """Test converting a record to ConversationMessage model."""
        message = record_to_conversation_message(sample_message_record)
        
        assert isinstance(message, ConversationMessage)
        assert message.user_id == 12345
        assert message.session_id == "session-123"
        assert message.role == "user"
        assert message.content == "Hello, bot!"
        assert message.agent_type == "default"

    def test_record_to_conversation_session(self, sample_session_record):
        """Test converting a record to ConversationSession model."""
        session = record_to_conversation_session(sample_session_record)
        
        assert isinstance(session, ConversationSession)
        assert session.id == "session-123"
        assert session.user_id == 12345
        assert session.message_count == 5
        assert session.metadata == {"key": "value"}


# =============================================================================
# UserRepository Tests
# =============================================================================

class TestUserRepository:
    """Tests for UserRepository."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_db, sample_user_record):
        """Test getting a user by ID when user exists."""
        mock_db.fetchrow.return_value = sample_user_record
        repo = UserRepository(mock_db)
        
        user = await repo.get_by_id(12345)
        
        assert user is not None
        assert user.id == 12345
        mock_db.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_db):
        """Test getting a user by ID when user doesn't exist."""
        mock_db.fetchrow.return_value = None
        repo = UserRepository(mock_db)
        
        user = await repo.get_by_id(99999)
        
        assert user is None

    @pytest.mark.asyncio
    async def test_get_by_username_found(self, mock_db, sample_user_record):
        """Test getting a user by username when user exists."""
        mock_db.fetchrow.return_value = sample_user_record
        repo = UserRepository(mock_db)
        
        user = await repo.get_by_username("testuser")
        
        assert user is not None
        assert user.telegram_username == "testuser"

    @pytest.mark.asyncio
    async def test_create_or_update_new_user(self, mock_db, sample_user_record):
        """Test creating a new user."""
        mock_db.fetchrow.return_value = sample_user_record
        repo = UserRepository(mock_db)
        
        user = await repo.create_or_update(
            user_id=12345,
            telegram_username="testuser",
            first_name="Test",
            last_name="User",
        )
        
        assert user.id == 12345
        mock_db.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_allowed_success(self, mock_db):
        """Test setting user allowed status successfully."""
        mock_db.execute.return_value = "UPDATE 1"
        repo = UserRepository(mock_db)
        
        result = await repo.set_allowed(12345, True)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_set_allowed_user_not_found(self, mock_db):
        """Test setting allowed status for non-existent user."""
        mock_db.execute.return_value = "UPDATE 0"
        repo = UserRepository(mock_db)
        
        result = await repo.set_allowed(99999, True)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_is_user_allowed_true(self, mock_db):
        """Test checking if user is allowed (True case)."""
        mock_db.fetchrow.return_value = {"is_allowed": True}
        repo = UserRepository(mock_db)
        
        result = await repo.is_user_allowed(12345)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_is_user_allowed_false(self, mock_db):
        """Test checking if user is allowed (False case)."""
        mock_db.fetchrow.return_value = {"is_allowed": False}
        repo = UserRepository(mock_db)
        
        result = await repo.is_user_allowed(12345)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_is_user_allowed_not_found(self, mock_db):
        """Test checking if user is allowed when user doesn't exist."""
        mock_db.fetchrow.return_value = None
        repo = UserRepository(mock_db)
        
        result = await repo.is_user_allowed(99999)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_all_allowed(self, mock_db, sample_user_record):
        """Test getting all allowed users."""
        mock_db.fetch.return_value = [sample_user_record]
        repo = UserRepository(mock_db)
        
        users = await repo.get_all_allowed()
        
        assert len(users) == 1
        assert users[0].is_allowed is True

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, mock_db, sample_user_record):
        """Test getting all users with pagination."""
        mock_db.fetch.return_value = [sample_user_record]
        repo = UserRepository(mock_db)
        
        users = await repo.get_all(limit=10, offset=0)
        
        assert len(users) == 1
        mock_db.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_success(self, mock_db):
        """Test deleting a user successfully."""
        mock_db.execute.return_value = "DELETE 1"
        repo = UserRepository(mock_db)
        
        result = await repo.delete(12345)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_db):
        """Test deleting a non-existent user."""
        mock_db.execute.return_value = "DELETE 0"
        repo = UserRepository(mock_db)
        
        result = await repo.delete(99999)
        
        assert result is False


# =============================================================================
# ProfileRepository Tests
# =============================================================================

class TestProfileRepository:
    """Tests for ProfileRepository."""

    @pytest.mark.asyncio
    async def test_get_profile_found(self, mock_db, sample_profile_record):
        """Test getting a user profile when it exists."""
        mock_db.fetchrow.return_value = sample_profile_record
        repo = ProfileRepository(mock_db)
        
        profile = await repo.get_profile(12345)
        
        assert profile is not None
        assert profile.user_id == 12345

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, mock_db):
        """Test getting a user profile when it doesn't exist."""
        mock_db.fetchrow.return_value = None
        repo = ProfileRepository(mock_db)
        
        profile = await repo.get_profile(99999)
        
        assert profile is None

    @pytest.mark.asyncio
    async def test_get_facts(self, mock_db, sample_fact_record):
        """Test getting facts for a user."""
        mock_db.fetch.return_value = [sample_fact_record]
        repo = ProfileRepository(mock_db)
        
        facts = await repo.get_facts(12345)
        
        assert len(facts) == 1
        assert facts[0].fact_key == "favorite_color"


# =============================================================================
# ConversationRepository Tests
# =============================================================================

class TestConversationRepository:
    """Tests for ConversationRepository."""

    @pytest.mark.asyncio
    async def test_add_message(self, mock_db, sample_message_record):
        """Test adding a message to conversation history."""
        mock_db.fetchrow.return_value = sample_message_record
        repo = ConversationRepository(mock_db)
        
        message = await repo.add_message(
            user_id=12345,
            session_id="session-123",
            role="user",
            content="Hello, bot!",
        )
        
        assert message is not None
        assert message.content == "Hello, bot!"

    @pytest.mark.asyncio
    async def test_get_messages(self, mock_db, sample_message_record):
        """Test getting messages for a user."""
        mock_db.fetch.return_value = [sample_message_record]
        repo = ConversationRepository(mock_db)
        
        messages = await repo.get_messages(user_id=12345, limit=10)
        
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_create_session(self, mock_db, sample_session_record):
        """Test creating a conversation session."""
        mock_db.fetchrow.return_value = sample_session_record
        repo = ConversationRepository(mock_db)
        
        session = await repo.create_session(
            user_id=12345,
            session_id="session-123",
        )
        
        assert session is not None
        assert session.user_id == 12345

    @pytest.mark.asyncio
    async def test_get_active_session(self, mock_db, sample_session_record):
        """Test getting active session for a user."""
        sample_session_record["ended_at"] = None
        mock_db.fetchrow.return_value = sample_session_record
        repo = ConversationRepository(mock_db)
        
        session = await repo.get_active_session(12345)
        
        assert session is not None

    @pytest.mark.asyncio
    async def test_end_session(self, mock_db, sample_session_record):
        """Test ending a conversation session."""
        sample_session_record["ended_at"] = datetime(2024, 1, 1, 13, 0, 0)
        mock_db.fetchrow.return_value = sample_session_record
        repo = ConversationRepository(mock_db)
        
        session = await repo.end_session("session-123")
        
        assert session is not None

    @pytest.mark.asyncio
    async def test_cleanup_old_messages(self, mock_db):
        """Test cleaning up old messages."""
        mock_db.execute.return_value = "DELETE 5"
        repo = ConversationRepository(mock_db)
        
        deleted = await repo.cleanup_old_messages(days_to_keep=30)
        
        assert deleted == 5
