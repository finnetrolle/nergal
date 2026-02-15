"""Memory service for managing user memory.

This module provides the main MemoryService class that coordinates
between short-term and long-term memory storage.
"""

import logging
from datetime import datetime
from typing import Any

from nergal.config import get_settings
from nergal.database.connection import DatabaseConnection, get_database
from nergal.database.models import (
    ConversationMessage,
    ConversationSession,
    ProfileFact,
    User,
    UserMemoryContext,
    UserProfile,
)
from nergal.database.repositories import (
    ConversationRepository,
    ProfileRepository,
    UserRepository,
)

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for managing user memory (short-term and long-term).

    This service provides a unified interface for:
    - Managing conversation history (short-term memory)
    - Managing user profiles and facts (long-term memory)
    - Providing memory context for agents
    """

    def __init__(self, db: DatabaseConnection | None = None) -> None:
        """Initialize the memory service.

        Args:
            db: Database connection. If not provided, uses the singleton.
        """
        self._db = db or get_database()
        self._user_repo = UserRepository(self._db)
        self._profile_repo = ProfileRepository(self._db)
        self._conversation_repo = ConversationRepository(self._db)
        self._settings = get_settings().memory

    async def get_or_create_user(
        self,
        user_id: int,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> User:
        """Get or create a user in the database.

        Args:
            user_id: Telegram user ID.
            telegram_username: Telegram username.
            first_name: User's first name.
            last_name: User's last name.
            language_code: User's language code.

        Returns:
            User instance.
        """
        return await self._user_repo.create_or_update(
            user_id=user_id,
            telegram_username=telegram_username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )

    async def get_user(self, user_id: int) -> User | None:
        """Get a user by ID.

        Args:
            user_id: Telegram user ID.

        Returns:
            User instance or None if not found.
        """
        return await self._user_repo.get_by_id(user_id)

    # =========================================================================
    # Short-term Memory (Conversation History)
    # =========================================================================

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
        return await self._conversation_repo.add_message(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            agent_type=agent_type,
            tokens_used=tokens_used,
            processing_time_ms=processing_time_ms,
        )

    async def get_conversation_history(
        self,
        user_id: int,
        session_id: str | None = None,
        limit: int | None = None,
    ) -> list[ConversationMessage]:
        """Get conversation history for a user.

        Args:
            user_id: Telegram user ID.
            session_id: Optional session ID filter.
            limit: Maximum number of messages to return.

        Returns:
            List of ConversationMessage instances.
        """
        limit = limit or self._settings.short_term_max_messages
        return await self._conversation_repo.get_messages(
            user_id=user_id,
            session_id=session_id,
            limit=limit,
        )

    async def get_recent_messages(
        self, user_id: int, limit: int | None = None
    ) -> list[ConversationMessage]:
        """Get recent messages for a user across all sessions.

        Args:
            user_id: Telegram user ID.
            limit: Maximum number of messages to return.

        Returns:
            List of ConversationMessage instances.
        """
        limit = limit or self._settings.short_term_max_messages
        return await self._conversation_repo.get_recent_messages(user_id, limit)

    async def get_or_create_session(
        self,
        user_id: int,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationSession:
        """Get or create a conversation session.

        Args:
            user_id: Telegram user ID.
            session_id: Session identifier.
            metadata: Optional session metadata.

        Returns:
            ConversationSession instance.
        """
        return await self._conversation_repo.create_session(user_id, session_id, metadata)

    async def get_active_session(self, user_id: int) -> ConversationSession | None:
        """Get the active session for a user.

        Args:
            user_id: Telegram user ID.

        Returns:
            Active ConversationSession instance or None.
        """
        return await self._conversation_repo.get_active_session(user_id)

    async def end_session(self, session_id: str) -> ConversationSession | None:
        """End a conversation session.

        Args:
            session_id: Session identifier.

        Returns:
            Updated ConversationSession instance or None.
        """
        return await self._conversation_repo.end_session(session_id)

    # =========================================================================
    # Long-term Memory (User Profile)
    # =========================================================================

    async def get_user_profile(self, user_id: int) -> UserProfile | None:
        """Get a user's profile.

        Args:
            user_id: Telegram user ID.

        Returns:
            UserProfile instance or None if not found.
        """
        return await self._profile_repo.get_profile(user_id)

    async def update_user_profile(
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
        """Update a user's profile.

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
            Updated UserProfile instance.
        """
        return await self._profile_repo.create_or_update_profile(
            user_id=user_id,
            preferred_name=preferred_name,
            age=age,
            location=location,
            timezone=timezone,
            occupation=occupation,
            languages=languages,
            interests=interests,
            expertise_areas=expertise_areas,
            communication_style=communication_style,
            custom_attributes=custom_attributes,
        )

    async def get_user_facts(
        self, user_id: int, fact_type: str | None = None
    ) -> list[ProfileFact]:
        """Get facts for a user.

        Args:
            user_id: Telegram user ID.
            fact_type: Optional filter by fact type.

        Returns:
            List of ProfileFact instances.
        """
        return await self._profile_repo.get_facts(user_id, fact_type)

    async def add_user_fact(
        self,
        user_id: int,
        fact_type: str,
        fact_key: str,
        fact_value: str,
        confidence: float = 1.0,
        source: str | None = None,
    ) -> ProfileFact:
        """Add a fact to a user's profile.

        Args:
            user_id: Telegram user ID.
            fact_type: Type of fact.
            fact_key: Key for the fact.
            fact_value: Value of the fact.
            confidence: Confidence level (0-1).
            source: Source of the fact.

        Returns:
            Created or updated ProfileFact instance.
        """
        return await self._profile_repo.upsert_fact(
            user_id=user_id,
            fact_type=fact_type,
            fact_key=fact_key,
            fact_value=fact_value,
            confidence=confidence,
            source=source,
        )

    async def remove_user_fact(
        self, user_id: int, fact_type: str, fact_key: str
    ) -> bool:
        """Remove a fact from a user's profile.

        Args:
            user_id: Telegram user ID.
            fact_type: Type of fact.
            fact_key: Key for the fact.

        Returns:
            True if fact was removed, False if not found.
        """
        return await self._profile_repo.delete_fact(user_id, fact_type, fact_key)

    # =========================================================================
    # Memory Context for Agents
    # =========================================================================

    async def get_memory_context(
        self,
        user_id: int,
        include_history: bool = True,
        history_limit: int | None = None,
    ) -> UserMemoryContext:
        """Get the complete memory context for a user.

        This is the main method for agents to get user context.

        Args:
            user_id: Telegram user ID.
            include_history: Whether to include conversation history.
            history_limit: Maximum number of messages to include.

        Returns:
            UserMemoryContext instance with all memory data.
        """
        # Get or create user
        user = await self.get_user(user_id)
        if user is None:
            # Create a minimal user if not exists
            user = User(id=user_id)

        # Get profile
        profile = await self.get_user_profile(user_id)

        # Get facts
        facts = await self.get_user_facts(user_id)

        # Get recent messages
        recent_messages = []
        if include_history:
            history_limit = history_limit or self._settings.short_term_max_messages
            recent_messages = await self.get_recent_messages(user_id, history_limit)

        # Get current session
        current_session = await self.get_active_session(user_id)

        return UserMemoryContext(
            user=user,
            profile=profile,
            facts=facts,
            recent_messages=recent_messages,
            current_session=current_session,
        )

    async def get_context_for_agent(
        self,
        user_id: int,
        agent_type: str | None = None,
    ) -> dict[str, Any]:
        """Get memory context formatted for agent use.

        Args:
            user_id: Telegram user ID.
            agent_type: Optional agent type for context filtering.

        Returns:
            Dictionary with memory context data.
        """
        context = await self.get_memory_context(user_id)

        return {
            "user_id": context.user.id,
            "user_name": context.user.full_name,
            "user_display_name": context.user.display_name,
            "profile_summary": context.get_profile_summary(),
            "conversation_summary": context.get_conversation_summary(),
            "profile": context.profile.model_dump() if context.profile else None,
            "facts": [f.model_dump() for f in context.facts],
            "recent_messages": [
                {"role": m.role, "content": m.content}
                for m in context.recent_messages[-10:]  # Last 10 messages
            ],
            "session_id": context.current_session.id if context.current_session else None,
        }

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def cleanup_old_data(self) -> dict[str, int]:
        """Clean up old data from the database.

        Returns:
            Dictionary with cleanup statistics.
        """
        stats = {}

        # Clean up old messages
        deleted_messages = await self._conversation_repo.cleanup_old_messages(
            self._settings.cleanup_days
        )
        stats["deleted_messages"] = deleted_messages
        logger.info(f"Cleaned up {deleted_messages} old messages")

        # Clean up expired facts
        deleted_facts = await self._profile_repo.delete_expired_facts()
        stats["deleted_facts"] = deleted_facts
        if deleted_facts > 0:
            logger.info(f"Cleaned up {deleted_facts} expired facts")

        return stats

    async def get_user_stats(self, user_id: int) -> dict[str, Any]:
        """Get statistics for a user.

        Args:
            user_id: Telegram user ID.

        Returns:
            Dictionary with user statistics.
        """
        context = await self.get_memory_context(user_id, include_history=False)

        return {
            "user_id": user_id,
            "has_profile": context.profile is not None,
            "fact_count": len(context.facts),
            "message_count": len(context.recent_messages),
            "has_active_session": context.current_session is not None,
        }
