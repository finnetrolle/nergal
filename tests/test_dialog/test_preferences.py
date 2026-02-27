"""Tests for user preference management."""

import pytest

from nergal.dialog.base import AgentType
from nergal.dialog.preferences import (
    AgentPreference,
    PreferenceManager,
    get_preference_manager,
    set_preference_manager,
)


class TestAgentPreference:
    """Tests for AgentPreference class."""

    def test_preference_creation(self) -> None:
        """Test basic preference creation."""
        pref = AgentPreference(
            user_id=123,
            agent_type=AgentType.WEB_SEARCH,
            weight=0.5,
            keywords=["search", "find"],
        )

        assert pref.user_id == 123
        assert pref.agent_type == AgentType.WEB_SEARCH
        assert pref.weight == 0.5
        assert pref.keywords == ["search", "find"]

    def test_weight_clamping_high(self) -> None:
        """Test that weight is clamped to max 1.0."""
        pref = AgentPreference(
            user_id=1,
            agent_type=AgentType.DEFAULT,
            weight=5.0,
        )

        assert pref.weight == 1.0

    def test_weight_clamping_low(self) -> None:
        """Test that weight is clamped to min -1.0."""
        pref = AgentPreference(
            user_id=1,
            agent_type=AgentType.DEFAULT,
            weight=-5.0,
        )

        assert pref.weight == -1.0

    def test_string_agent_type_conversion(self) -> None:
        """Test that string agent type is converted to enum."""
        pref = AgentPreference(
            user_id=1,
            agent_type="web_search",
            weight=0.5,
        )

        assert pref.agent_type == AgentType.WEB_SEARCH

    def test_default_values(self) -> None:
        """Test default values."""
        pref = AgentPreference(
            user_id=1,
            agent_type=AgentType.DEFAULT,
        )

        assert pref.weight == 0.0
        assert pref.keywords == []
        assert pref.created_at is None
        assert pref.updated_at is None

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        pref = AgentPreference(
            user_id=123,
            agent_type=AgentType.TODOIST,
            weight=0.8,
            keywords=["task", "todo"],
        )

        data = pref.to_dict()

        assert data["user_id"] == 123
        assert data["agent_type"] == "todoist"
        assert data["weight"] == 0.8
        assert data["keywords"] == ["task", "todo"]

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "user_id": 456,
            "agent_type": "news",
            "weight": -0.3,
            "keywords": ["avoid"],
        }

        pref = AgentPreference.from_dict(data)

        assert pref.user_id == 456
        assert pref.agent_type == AgentType.NEWS
        assert pref.weight == -0.3
        assert pref.keywords == ["avoid"]


class TestPreferenceManager:
    """Tests for PreferenceManager class."""

    def test_set_and_get_preference(self) -> None:
        """Test setting and getting a preference."""
        manager = PreferenceManager()

        manager.set_preference(
            user_id=123,
            agent_type=AgentType.WEB_SEARCH,
            weight=0.5,
            keywords=["search"],
        )

        pref = manager.get_preference(123, AgentType.WEB_SEARCH)

        assert pref is not None
        assert pref.weight == 0.5
        assert pref.keywords == ["search"]

    def test_get_nonexistent_preference(self) -> None:
        """Test getting a preference that doesn't exist."""
        manager = PreferenceManager()

        pref = manager.get_preference(999, AgentType.WEB_SEARCH)

        assert pref is None

    def test_get_all_preferences(self) -> None:
        """Test getting all preferences for a user."""
        manager = PreferenceManager()

        manager.set_preference(123, AgentType.WEB_SEARCH, 0.5)
        manager.set_preference(123, AgentType.TODOIST, 0.3)
        manager.set_preference(456, AgentType.NEWS, -0.2)

        prefs = manager.get_all_preferences(123)

        assert len(prefs) == 2
        agent_types = {p.agent_type for p in prefs}
        assert AgentType.WEB_SEARCH in agent_types
        assert AgentType.TODOIST in agent_types

    def test_delete_preference(self) -> None:
        """Test deleting a preference."""
        manager = PreferenceManager()

        manager.set_preference(123, AgentType.WEB_SEARCH, 0.5)
        deleted = manager.delete_preference(123, AgentType.WEB_SEARCH)

        assert deleted is True
        assert manager.get_preference(123, AgentType.WEB_SEARCH) is None

    def test_delete_nonexistent_preference(self) -> None:
        """Test deleting a preference that doesn't exist."""
        manager = PreferenceManager()

        deleted = manager.delete_preference(999, AgentType.WEB_SEARCH)

        assert deleted is False

    def test_get_boost_no_preference(self) -> None:
        """Test boost when no preference is set."""
        manager = PreferenceManager()

        boost = manager.get_boost(123, AgentType.WEB_SEARCH, "search for info")

        assert boost == 0.0

    def test_get_boost_with_weight(self) -> None:
        """Test boost from weight."""
        manager = PreferenceManager()

        manager.set_preference(123, AgentType.WEB_SEARCH, weight=0.5)

        boost = manager.get_boost(123, AgentType.WEB_SEARCH, "any message")

        assert boost == 0.5

    def test_get_boost_with_keywords(self) -> None:
        """Test boost from keyword matching."""
        manager = PreferenceManager(keyword_match_boost=0.1)

        manager.set_preference(
            123,
            AgentType.WEB_SEARCH,
            weight=0.3,
            keywords=["search", "find"],
        )

        # Message with one matching keyword
        boost = manager.get_boost(123, AgentType.WEB_SEARCH, "search for info")
        assert boost == 0.4  # 0.3 weight + 0.1 keyword match

        # Message with two matching keywords
        boost = manager.get_boost(123, AgentType.WEB_SEARCH, "search and find info")
        assert boost == 0.5  # 0.3 weight + 0.2 keyword matches

        # Message with no matching keywords
        boost = manager.get_boost(123, AgentType.WEB_SEARCH, "hello world")
        assert boost == 0.3  # Just the weight

    def test_get_boost_negative_weight(self) -> None:
        """Test negative boost (avoiding agent)."""
        manager = PreferenceManager()

        manager.set_preference(123, AgentType.NEWS, weight=-0.5)

        boost = manager.get_boost(123, AgentType.NEWS, "any message")

        assert boost == -0.5

    def test_apply_preference(self) -> None:
        """Test applying preference to confidence."""
        manager = PreferenceManager()

        manager.set_preference(123, AgentType.WEB_SEARCH, weight=0.3)

        adjusted = manager.apply_preference(
            user_id=123,
            agent_type=AgentType.WEB_SEARCH,
            confidence=0.5,
            message="search for info",
        )

        assert adjusted == 0.8  # 0.5 + 0.3

    def test_apply_preference_clamping_high(self) -> None:
        """Test that adjusted confidence is clamped to 1.0."""
        manager = PreferenceManager()

        manager.set_preference(123, AgentType.WEB_SEARCH, weight=0.5)

        adjusted = manager.apply_preference(
            user_id=123,
            agent_type=AgentType.WEB_SEARCH,
            confidence=0.8,
            message="test",
        )

        assert adjusted == 1.0  # Clamped from 1.3

    def test_apply_preference_clamping_low(self) -> None:
        """Test that adjusted confidence is clamped to 0.0."""
        manager = PreferenceManager()

        manager.set_preference(123, AgentType.NEWS, weight=-0.8)

        adjusted = manager.apply_preference(
            user_id=123,
            agent_type=AgentType.NEWS,
            confidence=0.3,
            message="test",
        )

        assert adjusted == 0.0  # Clamped from -0.5

    def test_clear_cache_for_user(self) -> None:
        """Test clearing cache for a specific user."""
        manager = PreferenceManager()

        manager.set_preference(123, AgentType.WEB_SEARCH, 0.5)
        manager.set_preference(456, AgentType.WEB_SEARCH, 0.3)

        manager.clear_cache(user_id=123)

        # User 123 should still have preference (in storage)
        assert manager.get_preference(123, AgentType.WEB_SEARCH) is not None
        # User 456 should still have preference
        assert manager.get_preference(456, AgentType.WEB_SEARCH) is not None

    def test_clear_cache_all(self) -> None:
        """Test clearing entire cache."""
        manager = PreferenceManager()

        manager.set_preference(123, AgentType.WEB_SEARCH, 0.5)
        manager.set_preference(456, AgentType.TODOIST, 0.3)

        manager.clear_cache()

        # Preferences should still exist (in storage)
        assert manager.get_preference(123, AgentType.WEB_SEARCH) is not None
        assert manager.get_preference(456, AgentType.TODOIST) is not None

    def test_get_stats(self) -> None:
        """Test getting statistics."""
        manager = PreferenceManager()

        manager.set_preference(123, AgentType.WEB_SEARCH, 0.5)
        manager.set_preference(123, AgentType.TODOIST, 0.3)
        manager.set_preference(456, AgentType.NEWS, -0.2)

        stats = manager.get_stats()

        assert stats["total_preferences"] == 3
        assert stats["users_with_preferences"] == 2
        assert stats["agent_distribution"]["web_search"] == 1
        assert stats["agent_distribution"]["todoist"] == 1
        assert stats["agent_distribution"]["news"] == 1


class TestGlobalPreferenceManager:
    """Tests for global preference manager functions."""

    @pytest.fixture(autouse=True)
    def reset_global_state(self):
        """Reset global state before each test in this class."""
        set_preference_manager(PreferenceManager())
        yield
        # Reset again after test
        set_preference_manager(PreferenceManager())

    def test_get_preference_manager(self) -> None:
        """Test getting global manager."""
        manager1 = get_preference_manager()
        manager2 = get_preference_manager()

        assert manager1 is manager2

    def test_set_preference_manager(self) -> None:
        """Test setting global manager."""
        new_manager = PreferenceManager()
        set_preference_manager(new_manager)

        assert get_preference_manager() is new_manager


class TestPreferenceManagerIntegration:
    """Integration tests for preference manager."""

    def test_multi_user_scenario(self) -> None:
        """Test scenario with multiple users."""
        manager = PreferenceManager()

        # User 1 prefers web search, avoids news
        manager.set_preference(1, AgentType.WEB_SEARCH, 0.5, ["search", "find"])
        manager.set_preference(1, AgentType.NEWS, -0.5)

        # User 2 prefers todoist
        manager.set_preference(2, AgentType.TODOIST, 0.8, ["task", "todo"])

        # User 3 has no preferences

        # Check user 1
        assert manager.get_boost(1, AgentType.WEB_SEARCH, "search this") == 0.6  # 0.5 + 0.1
        assert manager.get_boost(1, AgentType.NEWS, "news") == -0.5
        assert manager.get_boost(1, AgentType.TODOIST, "create task") == 0.0

        # Check user 2
        assert manager.get_boost(2, AgentType.TODOIST, "new task") == 0.9  # 0.8 + 0.1
        assert manager.get_boost(2, AgentType.WEB_SEARCH, "search") == 0.0

        # Check user 3
        assert manager.get_boost(3, AgentType.WEB_SEARCH, "search") == 0.0

    def test_preference_update(self) -> None:
        """Test updating an existing preference."""
        manager = PreferenceManager()

        # Set initial preference
        manager.set_preference(123, AgentType.WEB_SEARCH, 0.5)
        assert manager.get_preference(123, AgentType.WEB_SEARCH).weight == 0.5

        # Update preference
        manager.set_preference(123, AgentType.WEB_SEARCH, 0.8)
        assert manager.get_preference(123, AgentType.WEB_SEARCH).weight == 0.8

    def test_keyword_case_insensitivity(self) -> None:
        """Test that keyword matching is case-insensitive."""
        manager = PreferenceManager(keyword_match_boost=0.1)

        manager.set_preference(
            123,
            AgentType.WEB_SEARCH,
            0.3,
            keywords=["SEARCH", "Find"],
        )

        # Lowercase message
        boost = manager.get_boost(123, AgentType.WEB_SEARCH, "search for this")
        assert boost == 0.4  # 0.3 + 0.1

        # Uppercase message
        boost = manager.get_boost(123, AgentType.WEB_SEARCH, "FIND THIS")
        assert boost == 0.4  # 0.3 + 0.1
