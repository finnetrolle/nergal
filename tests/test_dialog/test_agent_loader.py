"""Tests for AgentFactory decorator-based registry."""

import pytest
from unittest.mock import MagicMock, patch

from nergal.dialog.base import AgentType, BaseAgent
from nergal.dialog.styles import StyleType


class TestAgentFactory:
    """Tests for AgentFactory class."""

    def test_register_decorator(self) -> None:
        """Test that register decorator works."""
        from nergal.dialog.agent_loader import AgentFactory

        # Save original factories
        original_factories = dict(AgentFactory._factories)
        original_deps = dict(AgentFactory._dependencies)

        try:
            AgentFactory.clear()

            mock_agent = MagicMock(spec=BaseAgent)

            @AgentFactory.register(AgentType.DEFAULT)
            def test_factory(llm_provider, **kwargs):
                return mock_agent

            assert AgentType.DEFAULT in AgentFactory._factories
            assert AgentFactory._factories[AgentType.DEFAULT] == test_factory
        finally:
            # Restore original factories
            AgentFactory._factories = original_factories
            AgentFactory._dependencies = original_deps

    def test_has_factory(self) -> None:
        """Test has_factory method."""
        from nergal.dialog.agent_loader import AgentFactory

        # The module should have registered some factories at import time
        # Check that common agents are registered
        assert AgentFactory.has_factory(AgentType.WEB_SEARCH)
        assert AgentFactory.has_factory(AgentType.TODOIST)

    def test_get_registered_types(self) -> None:
        """Test get_registered_types method."""
        from nergal.dialog.agent_loader import AgentFactory

        types = AgentFactory.get_registered_types()

        # Should have multiple registered types from module load
        assert len(types) > 0
        assert AgentType.WEB_SEARCH in types
        assert AgentType.TODOIST in types

    def test_create_agent(self) -> None:
        """Test creating an agent through factory."""
        from nergal.dialog.agent_loader import AgentFactory

        # Skip if factory not available
        if not AgentFactory.has_factory(AgentType.HEALTH):
            pytest.skip("HEALTH factory not registered")

        llm = MagicMock()
        result = AgentFactory.create(AgentType.HEALTH, llm_provider=llm, style_type=StyleType.DEFAULT)

        assert result is not None
        assert result.agent_type == AgentType.HEALTH

    def test_create_agent_not_registered(self) -> None:
        """Test creating an agent that's not registered."""
        from nergal.dialog.agent_loader import AgentFactory

        llm = MagicMock()
        # Use a mock agent type that's not registered
        unregistered_type = MagicMock()
        unregistered_type.value = "unregistered_agent_type"
        result = AgentFactory.create(unregistered_type, llm_provider=llm)

        assert result is None

    def test_create_agent_with_dependencies(self) -> None:
        """Test creating an agent with dependencies."""
        from nergal.dialog.agent_loader import AgentFactory

        llm = MagicMock()
        search = MagicMock()

        # With search provider - should work
        result = AgentFactory.create(
            AgentType.WEB_SEARCH,
            llm_provider=llm,
            search_provider=search,
            style_type=StyleType.DEFAULT,
        )
        assert result is not None

        # Without search provider - should return None
        result = AgentFactory.create(
            AgentType.WEB_SEARCH,
            llm_provider=llm,
            search_provider=None,
        )
        assert result is None

    def test_clear(self) -> None:
        """Test clearing all factories."""
        from nergal.dialog.agent_loader import AgentFactory

        # Save original factories
        original_factories = dict(AgentFactory._factories)
        original_deps = dict(AgentFactory._dependencies)

        try:
            AgentFactory.clear()
            assert len(AgentFactory._factories) == 0
            assert len(AgentFactory._dependencies) == 0
        finally:
            # Restore original factories
            AgentFactory._factories = original_factories
            AgentFactory._dependencies = original_deps


class TestAgentConfigMap:
    """Tests for AGENT_CONFIG_MAP."""

    def test_config_map_contains_all_enabled_settings(self) -> None:
        """Test that config map has entries for all agent settings."""
        from nergal.dialog.agent_loader import AGENT_CONFIG_MAP

        expected_keys = [
            "web_search_enabled",
            "todoist_enabled",
            "health_enabled",
            "reminder_enabled",
        ]

        for key in expected_keys:
            assert key in AGENT_CONFIG_MAP, f"Missing key: {key}"

    def test_config_map_values_are_agent_types(self) -> None:
        """Test that all values are AgentType instances."""
        from nergal.dialog.agent_loader import AGENT_CONFIG_MAP

        for key, value in AGENT_CONFIG_MAP.items():
            assert isinstance(value, AgentType), f"Invalid type for {key}: {type(value)}"


class TestRegisterConfiguredAgents:
    """Tests for register_configured_agents function."""

    def _create_mock_settings(self, enabled_agents: list[str]) -> MagicMock:
        """Create mock settings with specific agents enabled.

        Args:
            enabled_agents: List of agent config keys to enable.

        Returns:
            Mock Settings object.
        """
        from nergal.dialog.agent_loader import AGENT_CONFIG_MAP

        settings = MagicMock()
        settings.style = StyleType.DEFAULT
        settings.web_search.max_results = 5

        # Create agent settings with all disabled by default
        agent_settings = MagicMock()
        all_keys = list(AGENT_CONFIG_MAP.keys())
        for key in all_keys:
            setattr(agent_settings, key, key in enabled_agents)

        settings.agents = agent_settings
        return settings

    def test_register_no_agents(self) -> None:
        """Test registering with no agents enabled."""
        from nergal.dialog.agent_loader import register_configured_agents

        registry = MagicMock()
        settings = self._create_mock_settings([])
        llm = MagicMock()

        registered = register_configured_agents(
            registry=registry,
            settings=settings,
            llm_provider=llm,
        )

        assert registered == []

    def test_register_with_search_dependency_missing(self) -> None:
        """Test that agents requiring search are skipped if provider missing."""
        from nergal.dialog.agent_loader import register_configured_agents

        registry = MagicMock()
        settings = self._create_mock_settings(["web_search_enabled"])
        llm = MagicMock()

        registered = register_configured_agents(
            registry=registry,
            settings=settings,
            llm_provider=llm,
            search_provider=None,  # Missing!
        )

        # WebSearchAgent should be skipped due to missing dependency
        assert "web_search" not in registered

    def test_register_with_all_dependencies(self) -> None:
        """Test registering agents when all dependencies are available."""
        from nergal.dialog.agent_loader import register_configured_agents

        registry = MagicMock()
        settings = self._create_mock_settings(["health_enabled"])
        llm = MagicMock()

        registered = register_configured_agents(
            registry=registry,
            settings=settings,
            llm_provider=llm,
        )

        # These agents don't require special dependencies
        assert "health" in registered


class TestLegacyCompatibility:
    """Tests for legacy compatibility functions."""

    def test_create_web_search_agent_legacy(self) -> None:
        """Test legacy create_web_search_agent function."""
        from nergal.dialog.agent_loader import create_web_search_agent

        llm = MagicMock()
        search = MagicMock()

        agent = create_web_search_agent(
            llm_provider=llm,
            search_provider=search,
            style_type=StyleType.DEFAULT,
        )

        assert agent is not None
        assert agent.agent_type == AgentType.WEB_SEARCH
