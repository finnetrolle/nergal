"""User preference management for agent prioritization.

This module provides a system for users to set preferences for different
agent types, affecting agent selection confidence scores.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from nergal.dialog.base import AgentType

logger = logging.getLogger(__name__)


@dataclass
class AgentPreference:
    """A user's preference for a specific agent type.

    Attributes:
        user_id: The user's ID.
        agent_type: The agent type this preference applies to.
        weight: Preference weight from -1.0 (avoid) to 1.0 (prefer).
        keywords: List of keywords that boost this agent's confidence.
        created_at: When this preference was created.
        updated_at: When this preference was last updated.
    """

    user_id: int
    agent_type: AgentType
    weight: float = 0.0
    keywords: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate the preference."""
        # Clamp weight to valid range
        self.weight = max(-1.0, min(1.0, self.weight))

        # Convert agent_type string to enum if needed
        if isinstance(self.agent_type, str):
            self.agent_type = AgentType(self.agent_type)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "user_id": self.user_id,
            "agent_type": self.agent_type.value,
            "weight": self.weight,
            "keywords": self.keywords,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentPreference":
        """Create from dictionary.

        Args:
            data: Dictionary with preference data.

        Returns:
            AgentPreference instance.
        """
        return cls(
            user_id=data["user_id"],
            agent_type=AgentType(data["agent_type"]),
            weight=data.get("weight", 0.0),
            keywords=data.get("keywords", []),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            updated_at=datetime.fromisoformat(data["updated_at"])
            if data.get("updated_at")
            else None,
        )


class PreferenceManager:
    """Manages user preferences for agent prioritization.

    This class provides methods to get, set, and apply user preferences
    to affect agent selection confidence scores.

    The preference system works by applying a "boost" to an agent's
    confidence score based on:
    1. The user's explicit weight for that agent type
    2. Keyword matching in the message
    """

    def __init__(
        self,
        cache_ttl_seconds: int = 300,
        keyword_match_boost: float = 0.1,
    ) -> None:
        """Initialize the preference manager.

        Args:
            cache_ttl_seconds: How long to cache preferences (seconds).
            keyword_match_boost: Boost per matching keyword.
        """
        self._cache_ttl = cache_ttl_seconds
        self._keyword_match_boost = keyword_match_boost

        # In-memory cache: user_id -> {agent_type -> AgentPreference}
        self._cache: dict[int, dict[AgentType, AgentPreference]] = {}
        self._cache_timestamps: dict[int, datetime] = {}

        # TODO: Replace in-memory storage with database persistence
        # See database/migrations/002_add_agent_preferences.sql for schema
        # Storage backend (can be replaced with database)
        self._storage: dict[int, dict[AgentType, AgentPreference]] = {}

    def get_preference(
        self, user_id: int, agent_type: AgentType
    ) -> AgentPreference | None:
        """Get a user's preference for an agent type.

        Args:
            user_id: The user's ID.
            agent_type: The agent type.

        Returns:
            AgentPreference if set, None otherwise.
        """
        self._ensure_cache_fresh(user_id)

        if user_id in self._cache:
            return self._cache[user_id].get(agent_type)
        return None

    def get_all_preferences(self, user_id: int) -> list[AgentPreference]:
        """Get all preferences for a user.

        Args:
            user_id: The user's ID.

        Returns:
            List of all preferences for the user.
        """
        self._ensure_cache_fresh(user_id)

        if user_id in self._cache:
            return list(self._cache[user_id].values())
        return []

    def set_preference(
        self,
        user_id: int,
        agent_type: AgentType,
        weight: float,
        keywords: list[str] | None = None,
    ) -> AgentPreference:
        """Set a user's preference for an agent type.

        Args:
            user_id: The user's ID.
            agent_type: The agent type.
            weight: Preference weight (-1.0 to 1.0).
            keywords: Optional keywords for boosting.

        Returns:
            The created/updated preference.
        """
        now = datetime.now(UTC)

        preference = AgentPreference(
            user_id=user_id,
            agent_type=agent_type,
            weight=weight,
            keywords=keywords or [],
            created_at=now,
            updated_at=now,
        )

        # Update storage
        if user_id not in self._storage:
            self._storage[user_id] = {}
        self._storage[user_id][agent_type] = preference

        # Update cache
        if user_id not in self._cache:
            self._cache[user_id] = {}
        self._cache[user_id][agent_type] = preference
        self._cache_timestamps[user_id] = now

        logger.debug(
            f"Set preference for user {user_id}, agent {agent_type.value}: weight={weight}"
        )

        return preference

    def delete_preference(
        self, user_id: int, agent_type: AgentType
    ) -> bool:
        """Delete a user's preference for an agent type.

        Args:
            user_id: The user's ID.
            agent_type: The agent type.

        Returns:
            True if deleted, False if not found.
        """
        deleted = False

        # Remove from storage
        if user_id in self._storage and agent_type in self._storage[user_id]:
            del self._storage[user_id][agent_type]
            deleted = True

        # Remove from cache
        if user_id in self._cache and agent_type in self._cache[user_id]:
            del self._cache[user_id][agent_type]
            self._cache_timestamps[user_id] = datetime.now(UTC)

        if deleted:
            logger.debug(
                f"Deleted preference for user {user_id}, agent {agent_type.value}"
            )

        return deleted

    def get_boost(
        self, user_id: int, agent_type: AgentType, message: str
    ) -> float:
        """Get the confidence boost for an agent based on user preferences.

        The boost is calculated as:
        - Base weight from user preference
        - Plus keyword match boosts

        Args:
            user_id: The user's ID.
            agent_type: The agent type.
            message: The user's message.

        Returns:
            Boost value to add to confidence (-1.0 to 1.0+).
        """
        preference = self.get_preference(user_id, agent_type)

        if preference is None:
            return 0.0

        # Start with base weight
        boost = preference.weight

        # Add keyword matches
        if preference.keywords:
            message_lower = message.lower()
            for keyword in preference.keywords:
                if keyword.lower() in message_lower:
                    boost += self._keyword_match_boost

        logger.debug(
            f"Preference boost for user {user_id}, agent {agent_type.value}: {boost}"
        )

        return boost

    def apply_preference(
        self, user_id: int, agent_type: AgentType, confidence: float, message: str
    ) -> float:
        """Apply user preference to a confidence score.

        Args:
            user_id: The user's ID.
            agent_type: The agent type.
            confidence: Original confidence score.
            message: The user's message.

        Returns:
            Adjusted confidence score (clamped to 0.0-1.0).
        """
        boost = self.get_boost(user_id, agent_type, message)
        adjusted = confidence + boost

        # Clamp to valid range
        return max(0.0, min(1.0, adjusted))

    def _ensure_cache_fresh(self, user_id: int) -> None:
        """Ensure the cache is fresh for a user.

        Args:
            user_id: The user's ID.
        """
        now = datetime.now(UTC)

        # Check if cache is fresh
        if user_id in self._cache_timestamps:
            cache_age = (now - self._cache_timestamps[user_id]).total_seconds()
            if cache_age < self._cache_ttl:
                return

        # Refresh cache from storage
        if user_id in self._storage:
            self._cache[user_id] = dict(self._storage[user_id])
        else:
            self._cache[user_id] = {}

        self._cache_timestamps[user_id] = now

    def clear_cache(self, user_id: int | None = None) -> None:
        """Clear the preference cache.

        Args:
            user_id: Optional user ID to clear cache for. If None, clears all.
        """
        if user_id is not None:
            self._cache.pop(user_id, None)
            self._cache_timestamps.pop(user_id, None)
        else:
            self._cache.clear()
            self._cache_timestamps.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about preferences.

        Returns:
            Dictionary with stats.
        """
        total_preferences = sum(
            len(prefs) for prefs in self._storage.values()
        )
        users_with_preferences = len(self._storage)

        agent_counts: dict[str, int] = {}
        for prefs in self._storage.values():
            for agent_type in prefs:
                agent_counts[agent_type.value] = (
                    agent_counts.get(agent_type.value, 0) + 1
                )

        return {
            "total_preferences": total_preferences,
            "users_with_preferences": users_with_preferences,
            "cached_users": len(self._cache),
            "agent_distribution": agent_counts,
        }


# Global preference manager instance
_preference_manager: PreferenceManager | None = None


def get_preference_manager() -> PreferenceManager:
    """Get the global preference manager instance.

    Returns:
        The global PreferenceManager.
    """
    global _preference_manager
    if _preference_manager is None:
        _preference_manager = PreferenceManager()
    return _preference_manager


def set_preference_manager(manager: PreferenceManager) -> None:
    """Set the global preference manager instance.

    Args:
        manager: The PreferenceManager to use globally.
    """
    global _preference_manager
    _preference_manager = manager
