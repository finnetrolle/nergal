"""Database repositories for user memory management.

This module provides repository classes for CRUD operations
on users, profiles, and conversation history.
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from asyncpg import Record

from nergal.database.connection import DatabaseConnection, get_database
from nergal.database.models import (
    ConversationMessage,
    ConversationSession,
    MemoryExtractionEvent,
    ProfileFact,
    User,
    UserProfile,
)

logger = logging.getLogger(__name__)


def record_to_user(record: Record) -> User:
    """Convert a database record to User model."""
    return User(
        id=record["id"],
        telegram_username=record["telegram_username"],
        first_name=record["first_name"],
        last_name=record["last_name"],
        language_code=record["language_code"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )


def record_to_user_profile(record: Record) -> UserProfile:
    """Convert a database record to UserProfile model."""
    return UserProfile(
        id=record["id"],
        user_id=record["user_id"],
        preferred_name=record["preferred_name"],
        age=record["age"],
        location=record["location"],
        timezone=record["timezone"],
        occupation=record["occupation"],
        languages=record["languages"] or [],
        interests=record["interests"] or [],
        expertise_areas=record["expertise_areas"] or [],
        communication_style=record["communication_style"],
        custom_attributes=record["custom_attributes"] or {},
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )


def record_to_profile_fact(record: Record) -> ProfileFact:
    """Convert a database record to ProfileFact model."""
    return ProfileFact(
        id=record["id"],
        user_id=record["user_id"],
        fact_type=record["fact_type"],
        fact_key=record["fact_key"],
        fact_value=record["fact_value"],
        confidence=record["confidence"],
        source=record["source"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
        expires_at=record["expires_at"],
    )


def record_to_conversation_message(record: Record) -> ConversationMessage:
    """Convert a database record to ConversationMessage model."""
    return ConversationMessage(
        id=record["id"],
        user_id=record["user_id"],
        session_id=record["session_id"],
        role=record["role"],
        content=record["content"],
        agent_type=record["agent_type"],
        tokens_used=record["tokens_used"],
        processing_time_ms=record["processing_time_ms"],
        created_at=record["created_at"],
    )


def record_to_conversation_session(record: Record) -> ConversationSession:
    """Convert a database record to ConversationSession model."""
    return ConversationSession(
        id=record["id"],
        user_id=record["user_id"],
        started_at=record["started_at"],
        ended_at=record["ended_at"],
        message_count=record["message_count"],
        metadata=record["metadata"] or {},
    )


class UserRepository:
    """Repository for User CRUD operations."""

    def __init__(self, db: DatabaseConnection | None = None) -> None:
        """Initialize the repository.

        Args:
            db: Database connection. If not provided, uses the singleton.
        """
        self._db = db or get_database()

    async def get_by_id(self, user_id: int) -> User | None:
        """Get a user by Telegram ID.

        Args:
            user_id: Telegram user ID.

        Returns:
            User instance or None if not found.
        """
        query = """
            SELECT id, telegram_username, first_name, last_name, language_code,
                   created_at, updated_at
            FROM users
            WHERE id = $1
        """
        record = await self._db.fetchrow(query, user_id)
        return record_to_user(record) if record else None

    async def get_by_username(self, username: str) -> User | None:
        """Get a user by Telegram username.

        Args:
            username: Telegram username (without @).

        Returns:
            User instance or None if not found.
        """
        query = """
            SELECT id, telegram_username, first_name, last_name, language_code,
                   created_at, updated_at
            FROM users
            WHERE telegram_username = $1
        """
        record = await self._db.fetchrow(query, username)
        return record_to_user(record) if record else None

    async def create_or_update(
        self,
        user_id: int,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> User:
        """Create a new user or update an existing one.

        Args:
            user_id: Telegram user ID.
            telegram_username: Telegram username.
            first_name: User's first name.
            last_name: User's last name.
            language_code: User's language code.

        Returns:
            Created or updated User instance.
        """
        query = """
            INSERT INTO users (id, telegram_username, first_name, last_name, language_code)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE SET
                telegram_username = EXCLUDED.telegram_username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                language_code = EXCLUDED.language_code,
                updated_at = NOW()
            RETURNING id, telegram_username, first_name, last_name, language_code,
                      created_at, updated_at
        """
        record = await self._db.fetchrow(
            query, user_id, telegram_username, first_name, last_name, language_code
        )
        return record_to_user(record)

    async def delete(self, user_id: int) -> bool:
        """Delete a user by ID.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if user was deleted, False if not found.
        """
        query = "DELETE FROM users WHERE id = $1"
        result = await self._db.execute(query, user_id)
        return result == "DELETE 1"


class ProfileRepository:
    """Repository for UserProfile and ProfileFact operations."""

    def __init__(self, db: DatabaseConnection | None = None) -> None:
        """Initialize the repository.

        Args:
            db: Database connection. If not provided, uses the singleton.
        """
        self._db = db or get_database()

    async def get_profile(self, user_id: int) -> UserProfile | None:
        """Get a user's profile.

        Args:
            user_id: Telegram user ID.

        Returns:
            UserProfile instance or None if not found.
        """
        query = """
            SELECT id, user_id, preferred_name, age, location, timezone,
                   occupation, languages, interests, expertise_areas,
                   communication_style, custom_attributes, created_at, updated_at
            FROM user_profiles
            WHERE user_id = $1
        """
        record = await self._db.fetchrow(query, user_id)
        return record_to_user_profile(record) if record else None

    async def create_or_update_profile(
        self,
        user_id: int,
        preferred_name: str | None = None,
        age: int | None = None,
        location: str | None = None,
        timezone: str | None = None,
        occupation: str | None = None,
        languages: list[str] | None = None,
        interests: list[str] | None = None,
        expertise_areas: list[str] | None = None,
        communication_style: str | None = None,
        custom_attributes: dict[str, Any] | None = None,
    ) -> UserProfile:
        """Create or update a user's profile.

        Args:
            user_id: Telegram user ID.
            preferred_name: How the user prefers to be called.
            age: User's age.
            location: User's location.
            timezone: User's timezone.
            occupation: User's occupation.
            languages: Languages the user speaks.
            interests: User's interests.
            expertise_areas: Areas of expertise.
            communication_style: Preferred communication style.
            custom_attributes: Additional custom attributes.

        Returns:
            Created or updated UserProfile instance.
        """
        query = """
            INSERT INTO user_profiles (
                user_id, preferred_name, age, location, timezone, occupation,
                languages, interests, expertise_areas, communication_style, custom_attributes
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (user_id) DO UPDATE SET
                preferred_name = COALESCE(EXCLUDED.preferred_name, user_profiles.preferred_name),
                age = COALESCE(EXCLUDED.age, user_profiles.age),
                location = COALESCE(EXCLUDED.location, user_profiles.location),
                timezone = COALESCE(EXCLUDED.timezone, user_profiles.timezone),
                occupation = COALESCE(EXCLUDED.occupation, user_profiles.occupation),
                languages = COALESCE(EXCLUDED.languages, user_profiles.languages),
                interests = COALESCE(EXCLUDED.interests, user_profiles.interests),
                expertise_areas = COALESCE(EXCLUDED.expertise_areas, user_profiles.expertise_areas),
                communication_style = COALESCE(EXCLUDED.communication_style, user_profiles.communication_style),
                custom_attributes = COALESCE(EXCLUDED.custom_attributes, user_profiles.custom_attributes),
                updated_at = NOW()
            RETURNING id, user_id, preferred_name, age, location, timezone,
                      occupation, languages, interests, expertise_areas,
                      communication_style, custom_attributes, created_at, updated_at
        """
        record = await self._db.fetchrow(
            query,
            user_id,
            preferred_name,
            age,
            location,
            timezone,
            occupation,
            languages or [],
            interests or [],
            expertise_areas or [],
            communication_style,
            json.dumps(custom_attributes) if custom_attributes else None,
        )
        return record_to_user_profile(record)

    async def get_facts(
        self, user_id: int, fact_type: str | None = None
    ) -> list[ProfileFact]:
        """Get facts for a user.

        Args:
            user_id: Telegram user ID.
            fact_type: Optional filter by fact type.

        Returns:
            List of ProfileFact instances.
        """
        if fact_type:
            query = """
                SELECT id, user_id, fact_type, fact_key, fact_value, confidence,
                       source, created_at, updated_at, expires_at
                FROM profile_facts
                WHERE user_id = $1 AND fact_type = $2
                ORDER BY created_at DESC
            """
            records = await self._db.fetch(query, user_id, fact_type)
        else:
            query = """
                SELECT id, user_id, fact_type, fact_key, fact_value, confidence,
                       source, created_at, updated_at, expires_at
                FROM profile_facts
                WHERE user_id = $1
                ORDER BY created_at DESC
            """
            records = await self._db.fetch(query, user_id)

        return [record_to_profile_fact(r) for r in records]

    async def upsert_fact(
        self,
        user_id: int,
        fact_type: str,
        fact_key: str,
        fact_value: str,
        confidence: float = 1.0,
        source: str | None = None,
        expires_at: datetime | None = None,
    ) -> ProfileFact:
        """Create or update a fact for a user.

        Args:
            user_id: Telegram user ID.
            fact_type: Type of fact.
            fact_key: Key for the fact.
            fact_value: Value of the fact.
            confidence: Confidence level (0-1).
            source: Source of the fact.
            expires_at: Optional expiration timestamp.

        Returns:
            Created or updated ProfileFact instance.
        """
        query = """
            INSERT INTO profile_facts (user_id, fact_type, fact_key, fact_value, confidence, source, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (user_id, fact_type, fact_key) DO UPDATE SET
                fact_value = EXCLUDED.fact_value,
                confidence = EXCLUDED.confidence,
                source = EXCLUDED.source,
                expires_at = EXCLUDED.expires_at,
                updated_at = NOW()
            RETURNING id, user_id, fact_type, fact_key, fact_value, confidence,
                      source, created_at, updated_at, expires_at
        """
        record = await self._db.fetchrow(
            query, user_id, fact_type, fact_key, fact_value, confidence, source, expires_at
        )
        return record_to_profile_fact(record)

    async def delete_fact(self, user_id: int, fact_type: str, fact_key: str) -> bool:
        """Delete a specific fact.

        Args:
            user_id: Telegram user ID.
            fact_type: Type of fact.
            fact_key: Key for the fact.

        Returns:
            True if fact was deleted, False if not found.
        """
        query = """
            DELETE FROM profile_facts
            WHERE user_id = $1 AND fact_type = $2 AND fact_key = $3
        """
        result = await self._db.execute(query, user_id, fact_type, fact_key)
        return result == "DELETE 1"

    async def delete_expired_facts(self) -> int:
        """Delete all expired facts.

        Returns:
            Number of deleted facts.
        """
        query = "DELETE FROM profile_facts WHERE expires_at IS NOT NULL AND expires_at < NOW()"
        result = await self._db.execute(query)
        # Parse "DELETE N" result
        count = int(result.split()[-1]) if result.startswith("DELETE") else 0
        return count


class ConversationRepository:
    """Repository for conversation history operations."""

    def __init__(self, db: DatabaseConnection | None = None) -> None:
        """Initialize the repository.

        Args:
            db: Database connection. If not provided, uses the singleton.
        """
        self._db = db or get_database()

    async def add_message(
        self,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        agent_type: str | None = None,
        tokens_used: int | None = None,
        processing_time_ms: int | None = None,
    ) -> ConversationMessage:
        """Add a message to the conversation history.

        Args:
            user_id: Telegram user ID.
            session_id: Session identifier.
            role: Message role (user, assistant, system).
            content: Message content.
            agent_type: Agent that handled the message.
            tokens_used: Number of tokens used.
            processing_time_ms: Processing time in milliseconds.

        Returns:
            Created ConversationMessage instance.
        """
        query = """
            INSERT INTO conversation_messages (
                user_id, session_id, role, content, agent_type, tokens_used, processing_time_ms
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, user_id, session_id, role, content, agent_type,
                      tokens_used, processing_time_ms, created_at
        """
        record = await self._db.fetchrow(
            query, user_id, session_id, role, content, agent_type, tokens_used, processing_time_ms
        )

        # Update session message count
        await self._update_session_count(session_id)

        return record_to_conversation_message(record)

    async def get_messages(
        self,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationMessage]:
        """Get messages from conversation history.

        Args:
            user_id: Telegram user ID.
            session_id: Optional session ID filter.
            limit: Maximum number of messages to return.
            offset: Number of messages to skip.

        Returns:
            List of ConversationMessage instances.
        """
        if session_id:
            query = """
                SELECT id, user_id, session_id, role, content, agent_type,
                       tokens_used, processing_time_ms, created_at
                FROM conversation_messages
                WHERE user_id = $1 AND session_id = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
            """
            records = await self._db.fetch(query, user_id, session_id, limit, offset)
        else:
            query = """
                SELECT id, user_id, session_id, role, content, agent_type,
                       tokens_used, processing_time_ms, created_at
                FROM conversation_messages
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            records = await self._db.fetch(query, user_id, limit, offset)

        # Return in chronological order (oldest first)
        return [record_to_conversation_message(r) for r in reversed(records)]

    async def get_recent_messages(
        self, user_id: int, limit: int = 20
    ) -> list[ConversationMessage]:
        """Get recent messages for a user across all sessions.

        Args:
            user_id: Telegram user ID.
            limit: Maximum number of messages to return.

        Returns:
            List of ConversationMessage instances in chronological order.
        """
        query = """
            SELECT id, user_id, session_id, role, content, agent_type,
                   tokens_used, processing_time_ms, created_at
            FROM conversation_messages
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        records = await self._db.fetch(query, user_id, limit)
        return [record_to_conversation_message(r) for r in reversed(records)]

    async def create_session(
        self, user_id: int, session_id: str, metadata: dict[str, Any] | None = None
    ) -> ConversationSession:
        """Create a new conversation session.

        Args:
            user_id: Telegram user ID.
            session_id: Session identifier.
            metadata: Optional session metadata.

        Returns:
            Created ConversationSession instance.
        """
        query = """
            INSERT INTO conversation_sessions (id, user_id, metadata)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO UPDATE SET
                ended_at = NULL,
                metadata = COALESCE(EXCLUDED.metadata, conversation_sessions.metadata)
            RETURNING id, user_id, started_at, ended_at, message_count, metadata
        """
        record = await self._db.fetchrow(
            query, session_id, user_id, json.dumps(metadata) if metadata else None
        )
        return record_to_conversation_session(record)

    async def end_session(self, session_id: str) -> ConversationSession | None:
        """End a conversation session.

        Args:
            session_id: Session identifier.

        Returns:
            Updated ConversationSession instance or None if not found.
        """
        query = """
            UPDATE conversation_sessions
            SET ended_at = NOW()
            WHERE id = $1 AND ended_at IS NULL
            RETURNING id, user_id, started_at, ended_at, message_count, metadata
        """
        record = await self._db.fetchrow(query, session_id)
        return record_to_conversation_session(record) if record else None

    async def get_active_session(self, user_id: int) -> ConversationSession | None:
        """Get the active session for a user.

        Args:
            user_id: Telegram user ID.

        Returns:
            Active ConversationSession instance or None.
        """
        query = """
            SELECT id, user_id, started_at, ended_at, message_count, metadata
            FROM conversation_sessions
            WHERE user_id = $1 AND ended_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
        """
        record = await self._db.fetchrow(query, user_id)
        return record_to_conversation_session(record) if record else None

    async def get_session(self, session_id: str) -> ConversationSession | None:
        """Get a session by ID.

        Args:
            session_id: Session identifier.

        Returns:
            ConversationSession instance or None if not found.
        """
        query = """
            SELECT id, user_id, started_at, ended_at, message_count, metadata
            FROM conversation_sessions
            WHERE id = $1
        """
        record = await self._db.fetchrow(query, session_id)
        return record_to_conversation_session(record) if record else None

    async def _update_session_count(self, session_id: str) -> None:
        """Update the message count for a session.

        Args:
            session_id: Session identifier.
        """
        query = """
            UPDATE conversation_sessions
            SET message_count = message_count + 1
            WHERE id = $1
        """
        await self._db.execute(query, session_id)

    async def cleanup_old_messages(self, days_to_keep: int = 30) -> int:
        """Delete old messages from the database.

        Args:
            days_to_keep: Number of days to keep messages.

        Returns:
            Number of deleted messages.
        """
        query = """
            DELETE FROM conversation_messages
            WHERE created_at < NOW() - ($1 || ' days')::INTERVAL
        """
        result = await self._db.execute(query, str(days_to_keep))
        count = int(result.split()[-1]) if result.startswith("DELETE") else 0
        return count

    async def record_extraction_event(
        self,
        user_id: int,
        extracted_facts: dict[str, Any],
        message_id: UUID | None = None,
        extraction_confidence: float | None = None,
        was_applied: bool = False,
    ) -> MemoryExtractionEvent:
        """Record a memory extraction event.

        Args:
            user_id: Telegram user ID.
            extracted_facts: Facts extracted from the message.
            message_id: ID of the source message.
            extraction_confidence: Confidence of extraction.
            was_applied: Whether facts were applied to profile.

        Returns:
            Created MemoryExtractionEvent instance.
        """
        query = """
            INSERT INTO memory_extraction_events (
                user_id, message_id, extracted_facts, extraction_confidence, was_applied
            )
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, user_id, message_id, extracted_facts, extraction_confidence,
                      was_applied, created_at
        """
        record = await self._db.fetchrow(
            query,
            user_id,
            message_id,
            json.dumps(extracted_facts),
            extraction_confidence,
            was_applied,
        )
        return MemoryExtractionEvent(
            id=record["id"],
            user_id=record["user_id"],
            message_id=record["message_id"],
            extracted_facts=record["extracted_facts"],
            extraction_confidence=record["extraction_confidence"],
            was_applied=record["was_applied"],
            created_at=record["created_at"],
        )
