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
    UserIntegration,
    UserProfile,
    WebSearchTelemetry,
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
        is_allowed=record.get("is_allowed", False),
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
                   is_allowed, created_at, updated_at
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
                   is_allowed, created_at, updated_at
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
        is_allowed: bool | None = None,
    ) -> User:
        """Create a new user or update an existing one.

        Args:
            user_id: Telegram user ID.
            telegram_username: Telegram username.
            first_name: User's first name.
            last_name: User's last name.
            language_code: User's language code.
            is_allowed: Whether user is allowed to use the bot.

        Returns:
            Created or updated User instance.
        """
        # For new users, use provided is_allowed or default to False
        # For existing users, only update is_allowed if explicitly provided (not None)
        query = """
            INSERT INTO users (id, telegram_username, first_name, last_name, language_code, is_allowed)
            VALUES ($1, $2, $3, $4, $5, COALESCE($6, FALSE))
            ON CONFLICT (id) DO UPDATE SET
                telegram_username = EXCLUDED.telegram_username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                language_code = EXCLUDED.language_code,
                is_allowed = CASE WHEN $6 IS NOT NULL THEN $6 ELSE users.is_allowed END,
                updated_at = NOW()
            RETURNING id, telegram_username, first_name, last_name, language_code,
                      is_allowed, created_at, updated_at
        """
        record = await self._db.fetchrow(
            query, user_id, telegram_username, first_name, last_name, language_code, is_allowed
        )
        return record_to_user(record)

    async def set_allowed(self, user_id: int, is_allowed: bool) -> bool:
        """Set the allowed status for a user.

        Args:
            user_id: Telegram user ID.
            is_allowed: Whether user is allowed to use the bot.

        Returns:
            True if user was updated, False if not found.
        """
        query = """
            UPDATE users SET is_allowed = $2, updated_at = NOW()
            WHERE id = $1
        """
        result = await self._db.execute(query, user_id, is_allowed)
        return result == "UPDATE 1"

    async def is_user_allowed(self, user_id: int) -> bool:
        """Check if a user is allowed to use the bot.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if user is allowed, False otherwise.
        """
        query = "SELECT is_allowed FROM users WHERE id = $1"
        record = await self._db.fetchrow(query, user_id)
        return record["is_allowed"] if record else False

    async def get_all_allowed(self) -> list[User]:
        """Get all users who are allowed to use the bot.

        Returns:
            List of User instances with is_allowed=True.
        """
        query = """
            SELECT id, telegram_username, first_name, last_name, language_code,
                   is_allowed, created_at, updated_at
            FROM users
            WHERE is_allowed = TRUE
            ORDER BY created_at DESC
        """
        records = await self._db.fetch(query)
        return [record_to_user(r) for r in records]

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        """Get all users with pagination.

        Args:
            limit: Maximum number of users to return.
            offset: Number of users to skip.

        Returns:
            List of User instances.
        """
        query = """
            SELECT id, telegram_username, first_name, last_name, language_code,
                   is_allowed, created_at, updated_at
            FROM users
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
        """
        records = await self._db.fetch(query, limit, offset)
        return [record_to_user(r) for r in records]

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
        # Ensure fact_value is a string (LLM may return bool or other types)
        fact_value_str = str(fact_value) if not isinstance(fact_value, str) else fact_value
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
            query, user_id, fact_type, fact_key, fact_value_str, confidence, source, expires_at
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

    async def get_user_stats(self, user_id: int) -> dict[str, int]:
        """Get statistics for a specific user.

        Args:
            user_id: Telegram user ID.

        Returns:
            Dictionary with tokens_used, web_searches, and message_count.
        """
        # Get total tokens used
        tokens_query = """
            SELECT COALESCE(SUM(tokens_used), 0) as total_tokens
            FROM conversation_messages
            WHERE user_id = $1 AND tokens_used IS NOT NULL
        """
        tokens_record = await self._db.fetchrow(tokens_query, user_id)
        total_tokens = tokens_record["total_tokens"] if tokens_record else 0

        # Get web search count (messages from web search agents)
        web_search_query = """
            SELECT COUNT(*) as web_search_count
            FROM conversation_messages
            WHERE user_id = $1 AND agent_type IS NOT NULL AND agent_type LIKE '%web_search%'
        """
        web_search_record = await self._db.fetchrow(web_search_query, user_id)
        web_search_count = web_search_record["web_search_count"] if web_search_record else 0

        # Get total message count (user messages = requests to bot)
        messages_query = """
            SELECT COUNT(*) as message_count
            FROM conversation_messages
            WHERE user_id = $1 AND role = 'user'
        """
        messages_record = await self._db.fetchrow(messages_query, user_id)
        message_count = messages_record["message_count"] if messages_record else 0

        return {
            "tokens_used": total_tokens,
            "web_searches": web_search_count,
            "requests": message_count,
        }

    async def get_all_users_stats(self) -> dict[int, dict[str, int]]:
        """Get statistics for all users.

        Returns:
            Dictionary mapping user_id to stats dictionary.
        """
        query = """
            SELECT 
                user_id,
                COALESCE(SUM(tokens_used), 0) as total_tokens,
                COUNT(*) FILTER (WHERE agent_type IS NOT NULL AND agent_type LIKE '%web_search%') as web_search_count,
                COUNT(*) FILTER (WHERE role = 'user') as message_count
            FROM conversation_messages
            GROUP BY user_id
        """
        records = await self._db.fetch(query)

        return {
            record["user_id"]: {
                "tokens_used": record["total_tokens"],
                "web_searches": record["web_search_count"],
                "requests": record["message_count"],
            }
            for record in records
        }

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


def record_to_web_search_telemetry(record: Record) -> WebSearchTelemetry:
    """Convert a database record to WebSearchTelemetry model."""
    return WebSearchTelemetry(
        id=record["id"],
        query=record["query"],
        user_id=record["user_id"],
        session_id=record["session_id"],
        result_count_requested=record["result_count_requested"],
        recency_filter=record["recency_filter"],
        domain_filter=record["domain_filter"],
        status=record["status"],
        results_count=record["results_count"],
        results=record["results"] or [],
        error_type=record["error_type"],
        error_message=record["error_message"],
        error_stack_trace=record["error_stack_trace"],
        http_status_code=record["http_status_code"],
        api_response_time_ms=record["api_response_time_ms"],
        api_session_id=record["api_session_id"],
        raw_response=record["raw_response"],
        raw_response_truncated=record["raw_response_truncated"],
        total_duration_ms=record["total_duration_ms"],
        init_duration_ms=record["init_duration_ms"],
        tools_list_duration_ms=record["tools_list_duration_ms"],
        search_call_duration_ms=record["search_call_duration_ms"],
        provider_name=record["provider_name"],
        tool_used=record["tool_used"],
        # New retry and classification fields
        retry_count=record.get("retry_count", 0) or 0,
        retry_reasons=record.get("retry_reasons", []) or [],
        total_retry_delay_ms=record.get("total_retry_delay_ms"),
        error_category=record.get("error_category"),
        created_at=record["created_at"],
    )


class WebSearchTelemetryRepository:
    """Repository for web search telemetry operations."""

    # Maximum size for raw_response before truncation (in bytes)
    MAX_RAW_RESPONSE_SIZE = 50000

    def __init__(self, db: DatabaseConnection | None = None) -> None:
        """Initialize the repository.

        Args:
            db: Database connection. If not provided, uses the singleton.
        """
        self._db = db or get_database()

    async def record_search(
        self,
        query: str,
        status: str,
        user_id: int | None = None,
        session_id: str | None = None,
        result_count_requested: int = 10,
        recency_filter: str | None = None,
        domain_filter: str | None = None,
        results_count: int = 0,
        results: list[dict[str, Any]] | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        error_stack_trace: str | None = None,
        http_status_code: int | None = None,
        api_response_time_ms: int | None = None,
        api_session_id: str | None = None,
        raw_response: dict[str, Any] | None = None,
        total_duration_ms: int | None = None,
        init_duration_ms: int | None = None,
        tools_list_duration_ms: int | None = None,
        search_call_duration_ms: int | None = None,
        provider_name: str | None = None,
        tool_used: str | None = None,
        retry_count: int = 0,
        retry_reasons: list[str] | None = None,
        total_retry_delay_ms: int | None = None,
        error_category: str | None = None,
    ) -> WebSearchTelemetry:
        """Record a web search telemetry event.

        Args:
            query: Search query.
            status: Search status (success, error, timeout, empty).
            user_id: User who initiated search.
            session_id: Session identifier.
            result_count_requested: Requested number of results.
            recency_filter: Time filter applied.
            domain_filter: Domain filter applied.
            results_count: Actual number of results.
            results: List of search results (limited data).
            error_type: Exception class name if error.
            error_message: Error message if error.
            error_stack_trace: Full stack trace if error.
            http_status_code: HTTP status code from API.
            api_response_time_ms: API response time.
            api_session_id: MCP session ID.
            raw_response: Raw API response.
            total_duration_ms: Total search duration.
            init_duration_ms: MCP init duration.
            tools_list_duration_ms: Tools list duration.
            search_call_duration_ms: Search call duration.
            provider_name: Search provider name.
            tool_used: MCP tool name used.
            retry_count: Number of retry attempts.
            retry_reasons: List of error categories that triggered retries.
            total_retry_delay_ms: Total time spent in retry delays.
            error_category: Classified error category.

        Returns:
            Created WebSearchTelemetry instance.
        """
        # Truncate raw_response if too large
        raw_response_truncated = False
        if raw_response is not None:
            raw_response_str = json.dumps(raw_response)
            if len(raw_response_str) > self.MAX_RAW_RESPONSE_SIZE:
                raw_response = {"_truncated": True, "_original_size": len(raw_response_str)}
                raw_response_truncated = True

        query_sql = """
            INSERT INTO web_search_telemetry (
                query, user_id, session_id, result_count_requested, recency_filter,
                domain_filter, status, results_count, results, error_type, error_message,
                error_stack_trace, http_status_code, api_response_time_ms, api_session_id,
                raw_response, raw_response_truncated, total_duration_ms, init_duration_ms,
                tools_list_duration_ms, search_call_duration_ms, provider_name, tool_used,
                retry_count, retry_reasons, total_retry_delay_ms, error_category
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27)
            RETURNING *
        """
        record = await self._db.fetchrow(
            query_sql,
            query,
            user_id,
            session_id,
            result_count_requested,
            recency_filter,
            domain_filter,
            status,
            results_count,
            json.dumps(results) if results else None,
            error_type,
            error_message,
            error_stack_trace,
            http_status_code,
            api_response_time_ms,
            api_session_id,
            json.dumps(raw_response) if raw_response else None,
            raw_response_truncated,
            total_duration_ms,
            init_duration_ms,
            tools_list_duration_ms,
            search_call_duration_ms,
            provider_name,
            tool_used,
            retry_count,
            json.dumps(retry_reasons) if retry_reasons else None,
            total_retry_delay_ms,
            error_category,
        )
        return record_to_web_search_telemetry(record)

    async def get_by_id(self, telemetry_id: UUID) -> WebSearchTelemetry | None:
        """Get a telemetry record by ID.

        Args:
            telemetry_id: Telemetry record ID.

        Returns:
            WebSearchTelemetry instance or None if not found.
        """
        query = "SELECT * FROM web_search_telemetry WHERE id = $1"
        record = await self._db.fetchrow(query, telemetry_id)
        return record_to_web_search_telemetry(record) if record else None

    async def get_recent(
        self,
        limit: int = 100,
        status: str | None = None,
        user_id: int | None = None,
    ) -> list[WebSearchTelemetry]:
        """Get recent telemetry records.

        Args:
            limit: Maximum number of records to return.
            status: Optional filter by status.
            user_id: Optional filter by user ID.

        Returns:
            List of WebSearchTelemetry instances.
        """
        conditions = []
        params: list[Any] = []
        param_idx = 1

        if status:
            conditions.append(f"status = ${param_idx}")
            params.append(status)
            param_idx += 1

        if user_id:
            conditions.append(f"user_id = ${param_idx}")
            params.append(user_id)
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        query = f"""
            SELECT * FROM web_search_telemetry
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx}
        """
        records = await self._db.fetch(query, *params)
        return [record_to_web_search_telemetry(r) for r in records]

    async def get_failures(self, limit: int = 50) -> list[WebSearchTelemetry]:
        """Get failed search records.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of failed WebSearchTelemetry instances.
        """
        query = """
            SELECT * FROM web_search_telemetry
            WHERE status IN ('error', 'timeout')
            ORDER BY created_at DESC
            LIMIT $1
        """
        records = await self._db.fetch(query, limit)
        return [record_to_web_search_telemetry(r) for r in records]

    async def get_empty_results(self, limit: int = 50) -> list[WebSearchTelemetry]:
        """Get searches with empty results.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of WebSearchTelemetry instances with no results.
        """
        query = """
            SELECT * FROM web_search_telemetry
            WHERE status = 'success' AND results_count = 0
            ORDER BY created_at DESC
            LIMIT $1
        """
        records = await self._db.fetch(query, limit)
        return [record_to_web_search_telemetry(r) for r in records]

    async def get_stats(
        self,
        days: int = 7,
    ) -> dict[str, Any]:
        """Get search statistics for a time period.

        Args:
            days: Number of days to include.

        Returns:
            Dictionary with statistics.
        """
        query = """
            SELECT
                COUNT(*) as total_searches,
                COUNT(*) FILTER (WHERE status = 'success') as successful_searches,
                COUNT(*) FILTER (WHERE status = 'error') as failed_searches,
                COUNT(*) FILTER (WHERE status = 'timeout') as timed_out_searches,
                COUNT(*) FILTER (WHERE status = 'success' AND results_count = 0) as empty_result_searches,
                AVG(api_response_time_ms) FILTER (WHERE status = 'success') as avg_response_time_ms,
                AVG(total_duration_ms) as avg_total_duration_ms,
                AVG(results_count) FILTER (WHERE status = 'success') as avg_results_count,
                MAX(results_count) as max_results_count
            FROM web_search_telemetry
            WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
        """
        record = await self._db.fetchrow(query, days)

        return {
            "total_searches": record["total_searches"] or 0,
            "successful_searches": record["successful_searches"] or 0,
            "failed_searches": record["failed_searches"] or 0,
            "timed_out_searches": record["timed_out_searches"] or 0,
            "empty_result_searches": record["empty_result_searches"] or 0,
            "avg_response_time_ms": record["avg_response_time_ms"],
            "avg_total_duration_ms": record["avg_total_duration_ms"],
            "avg_results_count": record["avg_results_count"],
            "max_results_count": record["max_results_count"] or 0,
        }

    async def get_daily_stats(self, days: int = 30) -> list[dict[str, Any]]:
        """Get daily search statistics.

        Args:
            days: Number of days to include.

        Returns:
            List of daily statistics.
        """
        query = """
            SELECT
                DATE(created_at) as search_date,
                COUNT(*) as total_searches,
                COUNT(*) FILTER (WHERE status = 'success') as successful_searches,
                COUNT(*) FILTER (WHERE status = 'error') as failed_searches,
                COUNT(*) FILTER (WHERE status = 'timeout') as timed_out_searches,
                COUNT(*) FILTER (WHERE status = 'success' AND results_count = 0) as empty_result_searches,
                AVG(api_response_time_ms) FILTER (WHERE status = 'success') as avg_response_time_ms,
                AVG(total_duration_ms) as avg_total_duration_ms,
                AVG(results_count) FILTER (WHERE status = 'success') as avg_results_count
            FROM web_search_telemetry
            WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
            GROUP BY DATE(created_at)
            ORDER BY search_date DESC
        """
        records = await self._db.fetch(query, days)

        return [
            {
                "date": str(record["search_date"]),
                "total_searches": record["total_searches"] or 0,
                "successful_searches": record["successful_searches"] or 0,
                "failed_searches": record["failed_searches"] or 0,
                "timed_out_searches": record["timed_out_searches"] or 0,
                "empty_result_searches": record["empty_result_searches"] or 0,
                "avg_response_time_ms": record["avg_response_time_ms"],
                "avg_total_duration_ms": record["avg_total_duration_ms"],
                "avg_results_count": record["avg_results_count"],
            }
            for record in records
        ]

    async def get_error_types(self, days: int = 7, limit: int = 20) -> list[dict[str, Any]]:
        """Get most common error types.

        Args:
            days: Number of days to include.
            limit: Maximum number of error types to return.

        Returns:
            List of error type statistics.
        """
        query = """
            SELECT
                error_type,
                error_message,
                COUNT(*) as count,
                MAX(created_at) as last_occurrence
            FROM web_search_telemetry
            WHERE status IN ('error', 'timeout')
              AND created_at >= NOW() - ($1 || ' days')::INTERVAL
            GROUP BY error_type, error_message
            ORDER BY count DESC
            LIMIT $2
        """
        records = await self._db.fetch(query, days, limit)

        return [
            {
                "error_type": record["error_type"],
                "error_message": record["error_message"],
                "count": record["count"],
                "last_occurrence": str(record["last_occurrence"]) if record["last_occurrence"] else None,
            }
            for record in records
        ]

    async def get_popular_queries(
        self,
        days: int = 7,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get most popular search queries.

        Args:
            days: Number of days to include.
            limit: Maximum number of queries to return.

        Returns:
            List of query statistics.
        """
        query = """
            SELECT
                query,
                COUNT(*) as search_count,
                AVG(results_count) FILTER (WHERE status = 'success') as avg_results,
                COUNT(*) FILTER (WHERE status = 'success') as success_count,
                COUNT(*) FILTER (WHERE status = 'error') as error_count
            FROM web_search_telemetry
            WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
            GROUP BY query
            ORDER BY search_count DESC
            LIMIT $2
        """
        records = await self._db.fetch(query, days, limit)

        return [
            {
                "query": record["query"],
                "search_count": record["search_count"],
                "avg_results": record["avg_results"],
                "success_count": record["success_count"],
                "error_count": record["error_count"],
            }
            for record in records
        ]

    async def cleanup_old(self, days_to_keep: int = 90) -> int:
        """Delete old telemetry records.

        Args:
            days_to_keep: Number of days to keep.

        Returns:
            Number of deleted records.
        """
        query = "SELECT cleanup_old_telemetry($1)"
        await self._db.execute(query, days_to_keep)
        # Note: The function doesn't return count, so we return 0
        # In production, you might want to modify the function to return count
        return 0


def record_to_user_integration(record: Record) -> UserIntegration:
    """Convert a database record to UserIntegration model."""
    return UserIntegration(
        id=record["id"],
        user_id=record["user_id"],
        integration_type=record["integration_type"],
        encrypted_token=record["encrypted_token"],
        token_hash=record["token_hash"],
        config=record["config"] or {},
        is_active=record["is_active"],
        last_used_at=record["last_used_at"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )


class UserIntegrationRepository:
    """Repository for UserIntegration CRUD operations."""

    def __init__(self, db: DatabaseConnection | None = None):
        """Initialize the repository.

        Args:
            db: Database connection. If not provided, uses the singleton.
        """
        self._db = db or get_database()

    async def get_by_user_and_type(
        self, user_id: int, integration_type: str
    ) -> UserIntegration | None:
        """Get a user integration by user ID and type.

        Args:
            user_id: Telegram user ID.
            integration_type: Type of integration (e.g., "todoist").

        Returns:
            UserIntegration instance or None if not found.
        """
        query = """
            SELECT id, user_id, integration_type, encrypted_token, token_hash,
                   config, is_active, last_used_at, created_at, updated_at
            FROM user_integrations
            WHERE user_id = $1 AND integration_type = $2
        """
        record = await self._db.fetchrow(query, user_id, integration_type)
        return record_to_user_integration(record) if record else None

    async def get_all_for_user(self, user_id: int) -> list[UserIntegration]:
        """Get all integrations for a user.

        Args:
            user_id: Telegram user ID.

        Returns:
            List of UserIntegration instances.
        """
        query = """
            SELECT id, user_id, integration_type, encrypted_token, token_hash,
                   config, is_active, last_used_at, created_at, updated_at
            FROM user_integrations
            WHERE user_id = $1
        """
        records = await self._db.fetch(query, user_id)
        return [record_to_user_integration(record) for record in records]

    async def get_active_for_user(self, user_id: int) -> list[UserIntegration]:
        """Get all active integrations for a user.

        Args:
            user_id: Telegram user ID.

        Returns:
            List of active UserIntegration instances.
        """
        query = """
            SELECT id, user_id, integration_type, encrypted_token, token_hash,
                   config, is_active, last_used_at, created_at, updated_at
            FROM user_integrations
            WHERE user_id = $1 AND is_active = TRUE
        """
        records = await self._db.fetch(query, user_id)
        return [record_to_user_integration(record) for record in records]

    async def create(
        self,
        user_id: int,
        integration_type: str,
        encrypted_token: str | None = None,
        token_hash: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> UserIntegration:
        """Create a new user integration.

        Args:
            user_id: Telegram user ID.
            integration_type: Type of integration.
            encrypted_token: Encrypted API token.
            token_hash: Hash for token verification.
            config: Integration-specific configuration.

        Returns:
            Created UserIntegration instance.
        """
        query = """
            INSERT INTO user_integrations 
                (user_id, integration_type, encrypted_token, token_hash, config)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, user_id, integration_type, encrypted_token, token_hash,
                      config, is_active, last_used_at, created_at, updated_at
        """
        record = await self._db.fetchrow(
            query,
            user_id,
            integration_type,
            encrypted_token,
            token_hash,
            config or {},
        )
        return record_to_user_integration(record)

    async def update(
        self,
        user_id: int,
        integration_type: str,
        encrypted_token: str | None = None,
        token_hash: str | None = None,
        config: dict[str, Any] | None = None,
        is_active: bool | None = None,
    ) -> UserIntegration | None:
        """Update a user integration.

        Args:
            user_id: Telegram user ID.
            integration_type: Type of integration.
            encrypted_token: New encrypted API token.
            token_hash: New hash for token verification.
            config: New integration-specific configuration.
            is_active: New active status.

        Returns:
            Updated UserIntegration instance or None if not found.
        """
        updates = []
        params = []
        param_idx = 3

        if encrypted_token is not None:
            updates.append(f"encrypted_token = ${param_idx}")
            params.append(encrypted_token)
            param_idx += 1

        if token_hash is not None:
            updates.append(f"token_hash = ${param_idx}")
            params.append(token_hash)
            param_idx += 1

        if config is not None:
            updates.append(f"config = ${param_idx}")
            params.append(config)
            param_idx += 1

        if is_active is not None:
            updates.append(f"is_active = ${param_idx}")
            params.append(is_active)
            param_idx += 1

        if not updates:
            return await self.get_by_user_and_type(user_id, integration_type)

        query = f"""
            UPDATE user_integrations
            SET {', '.join(updates)}
            WHERE user_id = $1 AND integration_type = $2
            RETURNING id, user_id, integration_type, encrypted_token, token_hash,
                      config, is_active, last_used_at, created_at, updated_at
        """
        record = await self._db.fetchrow(query, user_id, integration_type, *params)
        return record_to_user_integration(record) if record else None

    async def update_last_used(self, user_id: int, integration_type: str) -> None:
        """Update the last_used_at timestamp for an integration.

        Args:
            user_id: Telegram user ID.
            integration_type: Type of integration.
        """
        query = """
            UPDATE user_integrations
            SET last_used_at = NOW()
            WHERE user_id = $1 AND integration_type = $2
        """
        await self._db.execute(query, user_id, integration_type)

    async def delete(self, user_id: int, integration_type: str) -> bool:
        """Delete a user integration.

        Args:
            user_id: Telegram user ID.
            integration_type: Type of integration.

        Returns:
            True if deleted, False if not found.
        """
        query = """
            DELETE FROM user_integrations
            WHERE user_id = $1 AND integration_type = $2
        """
        result = await self._db.execute(query, user_id, integration_type)
        return result == "DELETE 1"

    async def set_active(
        self, user_id: int, integration_type: str, is_active: bool
    ) -> bool:
        """Set the active status of an integration.

        Args:
            user_id: Telegram user ID.
            integration_type: Type of integration.
            is_active: New active status.

        Returns:
            True if updated, False if not found.
        """
        query = """
            UPDATE user_integrations
            SET is_active = $3
            WHERE user_id = $1 AND integration_type = $2
        """
        result = await self._db.execute(query, user_id, integration_type, is_active)
        return result == "UPDATE 1"
