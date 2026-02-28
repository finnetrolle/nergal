"""Unit tests for ToolRegistry."""

import pytest

from nergal.tools.base import Tool, ToolResult
from nergal.tools.registry import ToolRegistry, get_registry, _global_registry


class SimpleTool(Tool):
    """Simple test tool."""

    @property
    def name(self) -> str:
        return "simple_tool"

    @property
    def description(self) -> str:
        return "A simple tool"

    @property
    def parameters_schema(self) -> dict:
        return {"type": "object"}

    async def execute(self, args: dict) -> ToolResult:
        return ToolResult(success=True, output="OK")


class AnotherTool(Tool):
    """Another test tool."""

    @property
    def name(self) -> str:
        return "another_tool"

    @property
    def description(self) -> str:
        return "Another tool"

    @property
    def parameters_schema(self) -> dict:
        return {"type": "object"}

    async def execute(self, args: dict) -> ToolResult:
        return ToolResult(success=True, output="OK")


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_init_creates_empty_registry(self):
        """Test that new registry is empty."""
        registry = ToolRegistry()
        assert registry.count() == 0
        assert len(registry.list_tools()) == 0

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = SimpleTool()

        registry.register(tool)

        assert registry.count() == 1
        assert registry.has_tool("simple_tool") is True

    def test_register_replaces_existing(self):
        """Test that registering same name replaces old tool."""
        registry = ToolRegistry()
        tool1 = SimpleTool()
        tool2 = SimpleTool()

        registry.register(tool1)
        assert registry.get_tool("simple_tool") is tool1

        registry.register(tool2)
        assert registry.get_tool("simple_tool") is tool2
        assert registry.count() == 1

    def test_register_empty_name_raises(self):
        """Test that registering tool with empty name raises ValueError."""

        class EmptyNameTool(Tool):
            @property
            def name(self) -> str:
                return ""

            @property
            def description(self) -> str:
                return "desc"

            @property
            def parameters_schema(self) -> dict:
                return {"type": "object"}

            async def execute(self, args: dict) -> ToolResult:
                return ToolResult(success=True, output="OK")

        registry = ToolRegistry()
        with pytest.raises(ValueError, match="Tool name cannot be empty"):
            registry.register(EmptyNameTool())

    def test_unregister_existing_tool(self):
        """Test unregistering an existing tool."""
        registry = ToolRegistry()
        tool = SimpleTool()
        registry.register(tool)

        registry.unregister("simple_tool")

        assert registry.count() == 0
        assert registry.has_tool("simple_tool") is False

    def test_unregister_nonexistent_does_nothing(self):
        """Test that unregistering nonexistent tool doesn't raise."""
        registry = ToolRegistry()
        registry.register(SimpleTool())

        registry.unregister("nonexistent_tool")

        assert registry.count() == 1

    def test_get_tool_returns_tool(self):
        """Test getting a registered tool."""
        registry = ToolRegistry()
        tool = SimpleTool()
        registry.register(tool)

        retrieved = registry.get_tool("simple_tool")

        assert retrieved is tool
        assert retrieved.name == "simple_tool"

    def test_get_tool_nonexistent_returns_none(self):
        """Test getting nonexistent tool returns None."""
        registry = ToolRegistry()
        registry.register(SimpleTool())

        result = registry.get_tool("nonexistent")

        assert result is None

    def test_list_tools_returns_all(self):
        """Test listing all tools."""
        registry = ToolRegistry()
        tool1 = SimpleTool()
        tool2 = AnotherTool()

        registry.register(tool1)
        registry.register(tool2)

        tools = registry.list_tools()

        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools

    def test_list_tools_returns_copy(self):
        """Test that list_tools returns a copy."""
        registry = ToolRegistry()
        tool = SimpleTool()
        registry.register(tool)

        tools = registry.list_tools()
        tools.clear()

        assert registry.count() == 1

    def test_get_tool_names(self):
        """Test getting tool names."""
        registry = ToolRegistry()
        registry.register(SimpleTool())
        registry.register(AnotherTool())

        names = registry.get_tool_names()

        assert set(names) == {"simple_tool", "another_tool"}

    def test_has_tool_true(self):
        """Test has_tool returns True for existing tool."""
        registry = ToolRegistry()
        registry.register(SimpleTool())

        assert registry.has_tool("simple_tool") is True

    def test_has_tool_false(self):
        """Test has_tool returns False for nonexistent tool."""
        registry = ToolRegistry()
        registry.register(SimpleTool())

        assert registry.has_tool("nonexistent") is False

    def test_count(self):
        """Test count returns correct number."""
        registry = ToolRegistry()
        assert registry.count() == 0

        registry.register(SimpleTool())
        assert registry.count() == 1

        registry.register(AnotherTool())
        assert registry.count() == 2

    def test_clear(self):
        """Test clearing all tools."""
        registry = ToolRegistry()
        registry.register(SimpleTool())
        registry.register(AnotherTool())

        registry.clear()

        assert registry.count() == 0
        assert registry.list_tools() == []

    def test_multiple_registries_independent(self):
        """Test that multiple registries are independent."""
        registry1 = ToolRegistry()
        registry2 = ToolRegistry()

        registry1.register(SimpleTool())

        assert registry1.count() == 1
        assert registry2.count() == 0


class TestGetRegistry:
    """Tests for get_registry singleton function."""

    def test_get_registry_returns_same_instance(self):
        """Test that get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_get_registry_returns_tool_registry(self):
        """Test that get_registry returns ToolRegistry instance."""
        registry = get_registry()
        assert isinstance(registry, ToolRegistry)

    def test_global_registry_shared_across_calls(self):
        """Test that tools registered via get_registry persist."""
        registry = get_registry()
        registry.register(SimpleTool())

        registry2 = get_registry()
        assert registry2.has_tool("simple_tool") is True
