"""Unit tests for ShellExecuteTool."""

import pytest

from nergal.tools.exceptions import (
    SecurityPolicyViolationError,
    ToolExecutionError,
    ToolTimeoutError,
    ToolValidationError,
)
from nergal.tools.shell.execute import ShellExecuteTool


class TestShellExecuteTool:
    """Tests for ShellExecuteTool."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        tool = ShellExecuteTool()
        assert tool._timeout == 30.0
        assert tool._max_output_size == 10000
        assert tool._allowed_commands == []
        assert tool._working_dir is None

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        tool = ShellExecuteTool(
            allowed_commands=["ls", "cat"],
            timeout=60.0,
            max_output_size=50000,
            working_dir="/tmp",
        )
        assert tool._timeout == 60.0
        assert tool._max_output_size == 50000
        assert tool._allowed_commands == ["ls", "cat"]
        assert tool._working_dir == "/tmp"

    def test_init_invalid_timeout(self):
        """Test that invalid timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            ShellExecuteTool(timeout=0)

        with pytest.raises(ValueError, match="Timeout must be positive"):
            ShellExecuteTool(timeout=-10)

    def test_init_invalid_max_output_size(self):
        """Test that invalid max_output_size raises ValueError."""
        with pytest.raises(ValueError, match="Max output size must be positive"):
            ShellExecuteTool(max_output_size=0)

        with pytest.raises(ValueError, match="Max output size must be positive"):
            ShellExecuteTool(max_output_size=-100)

    def test_name_property(self):
        """Test name property."""
        tool = ShellExecuteTool()
        assert tool.name == "shell_execute"

    def test_description_without_whitelist(self):
        """Test description property without whitelist."""
        tool = ShellExecuteTool()
        desc = tool.description
        assert "Execute a shell command" in desc
        assert "timeout" in desc

    def test_description_with_whitelist(self):
        """Test description property with whitelist."""
        tool = ShellExecuteTool(allowed_commands=["ls", "cat"])
        desc = tool.description
        assert "ls, cat" in desc

    def test_parameters_schema(self):
        """Test parameters_schema property."""
        tool = ShellExecuteTool()
        schema = tool.parameters_schema

        assert schema["type"] == "object"
        assert "command" in schema["properties"]
        assert schema["properties"]["command"]["type"] == "string"
        assert "command" in schema["required"]

    @pytest.mark.asyncio
    async def test_execute_missing_command(self):
        """Test execute with missing command argument."""
        tool = ShellExecuteTool()

        with pytest.raises(ToolValidationError, match="Command must be a non-empty string"):
            await tool.execute({})

    @pytest.mark.asyncio
    async def test_execute_empty_command(self):
        """Test execute with empty command."""
        tool = ShellExecuteTool()

        with pytest.raises(ToolValidationError, match="Command cannot be empty or whitespace"):
            await tool.execute({"command": ""})

        with pytest.raises(ToolValidationError, match="Command cannot be empty or whitespace"):
            await tool.execute({"command": "   "})

    @pytest.mark.asyncio
    async def test_execute_invalid_command_type(self):
        """Test execute with non-string command."""
        tool = ShellExecuteTool()

        with pytest.raises(ToolValidationError, match="Command must be a non-empty string"):
            await tool.execute({"command": 123})

    @pytest.mark.asyncio
    async def test_execute_blocked_command(self):
        """Test execute with command not in whitelist."""
        tool = ShellExecuteTool(allowed_commands=["ls", "cat"])

        with pytest.raises(SecurityPolicyViolationError, match="not in the allowed commands list"):
            await tool.execute({"command": "rm -rf /"})

    @pytest.mark.asyncio
    async def test_execute_echo_command(self):
        """Test executing a simple echo command."""
        tool = ShellExecuteTool()

        result = await tool.execute({"command": "echo 'Hello, World!'"})

        assert result.success is True
        assert "Hello, World!" in result.output
        assert result.metadata["return_code"] == 0
        assert "execution_time" in result.metadata

    @pytest.mark.asyncio
    async def test_execute_echo_with_whitelist(self):
        """Test executing echo with whitelist allowing it."""
        tool = ShellExecuteTool(allowed_commands=["echo"])

        result = await tool.execute({"command": "echo test"})

        assert result.success is True
        assert "test" in result.output

    @pytest.mark.asyncio
    async def test_execute_command_with_stderr(self):
        """Test executing command that outputs to stderr."""
        tool = ShellExecuteTool()

        # This command writes to both stdout and stderr
        result = await tool.execute({"command": "echo 'stdout' && echo 'stderr' >&2"})

        assert result.success is True
        assert "stdout" in result.output
        assert "stderr" in result.output

    @pytest.mark.asyncio
    async def test_execute_failing_command(self):
        """Test executing a command that fails."""
        tool = ShellExecuteTool()

        result = await tool.execute({"command": "false"})

        assert result.success is False
        assert result.error is not None
        assert result.metadata["return_code"] != 0

    @pytest.mark.asyncio
    async def test_execute_ls_command(self):
        """Test executing ls command."""
        tool = ShellExecuteTool(allowed_commands=["ls"])

        result = await tool.execute({"command": "ls /tmp"})

        assert result.success is True
        assert result.output is not None

    @pytest.mark.asyncio
    async def test_execute_with_working_dir(self):
        """Test executing command with custom working directory."""
        tool = ShellExecuteTool(working_dir="/tmp")

        result = await tool.execute({"command": "echo 'test'"})

        assert result.success is True
        assert "test" in result.output

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        """Test that long-running commands timeout."""
        tool = ShellExecuteTool(timeout=0.1)

        with pytest.raises(ToolTimeoutError, match="timed out after 0.1 seconds"):
            await tool.execute({"command": "sleep 1"})

    @pytest.mark.asyncio
    async def test_execute_command_with_quotes(self):
        """Test executing command with quotes."""
        tool = ShellExecuteTool(allowed_commands=["echo"])

        result = await tool.execute({"command": 'echo "Hello, World!"'})

        assert result.success is True
        assert "Hello, World!" in result.output
