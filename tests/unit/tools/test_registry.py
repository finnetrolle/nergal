"""Unit tests for ToolRegistry.

Tests follow TDD Red-Green-Refactor pattern.
"""

import pytest

from nergal.tools.base import Tool, ToolResult


class MockTool1(Tool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "tool_1"

    @property
    def description(self) -> str:
        return "First mock tool"

    @property
    def parameters_schema(self) -> dict:
        return {"type": "object"}

    async def execute(self, args: dict) -> ToolResult:
        return ToolResult(success=True, output="tool_1 result")


class MockTool2(Tool):
    """Another mock tool for testing."""

    @property
    def name(self) -> str:
        return "tool_2"

    @property
    def description(self) -> str:
        return "Second mock tool"

    @property
    def parameters_schema(self) -> dict:
        return {"type": "object"}

    async def execute(self, args: dict) -> ToolResult:
        return ToolResult(success=True, output="tool_2 result")


class TestToolRegistry:
    """Tests for ToolRegistry functionality."""

    def test_registry_starts_empty(self) -> None:
        """Test that a new registry is empty."""
        from nergal.tools.registry import ToolRegistry

        registry = ToolRegistry()

        assert len(registry.list_tools()) == 0
        assert registry.get_tool("nonexistent") is None

    def test_register_tool(self) -> None:
        """Test registering a single tool."""
        from nergal.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool = MockTool1()

        registry.register(tool)

        assert len(registry.list_tools()) == 1
        assert registry.get_tool("tool_1") is tool

    def test_register_multiple_tools(self) -> None:
        """Test registering multiple tools."""
        from nergal.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool1 = MockTool1()
        tool2 = MockTool2()

        registry.register(tool1)
        registry.register(tool2)

        tools = registry.list_tools()
        assert len(tools) == 2
        assert "tool_1" in [t.name for t in tools]
        assert "tool_2" in [t.name for t in tools]

    def test_register_duplicate_tool_overwrites(self) -> None:
        """Test that registering a tool with same name overwrites."""
        from nergal.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool1 = MockTool1()
        tool2 = MockTool1()  # Same name

        registry.register(tool1)
        registry.register(tool2)

        # Should still have one tool, but it's the new one
        assert len(registry.list_tools()) == 1
        assert registry.get_tool("tool_1") is tool2

    def test_unregister_tool(self) -> None:
        """Test unregistering a tool."""
        from nergal.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool1 = MockTool1()
        tool2 = MockTool2()

        registry.register(tool1)
        registry.register(tool2)

        registry.unregister("tool_1")

        assert len(registry.list_tools()) == 1
        assert registry.get_tool("tool_1") is None
        assert registry.get_tool("tool_2") is tool2

    def test_unregister_nonexistent_tool(self) -> None:
        """Test unregistering a non-existent tool doesn't raise."""
        from nergal.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool1 = MockTool1()

        registry.register(tool1)

        # Should not raise
        registry.unregister("nonexistent")

        # Original tool still there
        assert len(registry.list_tools()) == 1

    def test_get_tool_names(self) -> None:
        """Test getting tool names."""
        from nergal.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool1 = MockTool1()
        tool2 = MockTool2()

        registry.register(tool1)
        registry.register(tool2)

        names = registry.get_tool_names()

        assert set(names) == {"tool_1", "tool_2"}

    def test_clear_all_tools(self) -> None:
        """Test clearing all tools."""
        from nergal.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool1 = MockTool1()
        tool2 = MockTool2()

        registry.register(tool1)
        registry.register(tool2)

        registry.clear()

        assert len(registry.list_tools()) == 0
        assert registry.get_tool("tool_1") is None
        assert registry.get_tool("tool_2") is None

    def test_register_with_duplicate_names_case_sensitive(self) -> None:
        """Test that tool names are case-sensitive."""
        from nergal.tools.registry import ToolRegistry

        registry = ToolRegistry()

        # Create tools with different case
        class ToolLower(Tool):
            @property
            def name(self) -> str:
                return "my_tool"

            @property
            def description(self) -> str:
                return "Lower case"

            @property
            def parameters_schema(self) -> dict:
                return {"type": "object"}

            async def execute(self, args: dict) -> ToolResult:
                return ToolResult(success=True, output="lower")

        class ToolUpper(Tool):
            @property
            def name(self) -> str:
                return "My_Tool"  # Different case

            @property
            def description(self) -> str:
                return "Upper case"

            @property
            def parameters_schema(self) -> dict:
                return {"type": "object"}

            async def execute(self, args: dict) -> ToolResult:
                return ToolResult(success=True, output="upper")

        registry.register(ToolLower())
        registry.register(ToolUpper())

        # Both should be registered (case-sensitive)
        assert len(registry.list_tools()) == 2
        assert registry.get_tool("my_tool") is not None
        assert registry.get_tool("My_Tool") is not None
        assert registry.get_tool("MY_TOOL") is None  # Different name

    def test_list_tools_returns_copy(self) -> None:
        """Test that list_tools returns a copy, not the internal list."""
        from nergal.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool1 = MockTool1()

        registry.register(tool1)

        tools1 = registry.list_tools()
        tools2 = registry.list_tools()

        # Should be different list objects
        assert tools1 is not tools2
        # But should have same content
        assert len(tools1) == len(tools2)
        assert tools1[0] is tools2[0]

    def test_has_tool(self) -> None:
        """Test checking if a tool exists."""
        from nergal.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool1 = MockTool1()

        registry.register(tool1)

        assert registry.has_tool("tool_1") is True
        assert registry.has_tool("tool_2") is False
        assert registry.has_tool("") is False

    def test_count_tools(self) -> None:
        """Test counting tools in registry."""
        from nergal.tools.registry import ToolRegistry

        registry = ToolRegistry()

        assert registry.count() == 0

        registry.register(MockTool1())
        assert registry.count() == 1

        registry.register(MockTool2())
        assert registry.count() == 2

        registry.unregister("tool_1")
        assert registry.count() == 1
