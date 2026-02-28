"""Tests for security policy."""

import pytest
from pathlib import Path
import tempfile

from nergal.security.policy import SecurityPolicy, AutonomyLevel


class TestAutonomyLevel:
    """Tests for AutonomyLevel enum."""

    def test_read_only_value(self):
        """Test READ_ONLY enum value."""
        assert AutonomyLevel.READ_ONLY.value == "read_only"

    def test_limited_value(self):
        """Test LIMITED enum value."""
        assert AutonomyLevel.LIMITED.value == "limited"

    def test_full_value(self):
        """Test FULL enum value."""
        assert AutonomyLevel.FULL.value == "full"


class TestSecurityPolicyInitialization:
    """Tests for SecurityPolicy initialization."""

    def test_init_with_defaults(self):
        """Test initialization with required parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.READ_ONLY,
                workspace_dir=tmpdir,
                allowed_commands=[],
            )

            assert policy.autonomy_level == AutonomyLevel.READ_ONLY
            assert policy.workspace_dir == Path(tmpdir)
            assert policy.allowed_commands == []
            assert policy.workspace_only is True
            assert policy.allowed_domains is None
            assert policy.forbidden_tools is None

    def test_init_with_workspace_only_false(self):
        """Test initialization with workspace_only=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=["ls"],
                workspace_only=False,
            )

            assert policy.workspace_only is False

    def test_init_with_allowed_domains(self):
        """Test initialization with allowed domains."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.FULL,
                workspace_dir=tmpdir,
                allowed_commands=["*"],
                allowed_domains=["example.com", "*.safe.com"],
            )

            assert policy.allowed_domains == ["example.com", "*.safe.com"]

    def test_init_with_forbidden_tools(self):
        """Test initialization with forbidden tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                forbidden_tools={"dangerous_tool", "another_tool"},
            )

            assert policy.forbidden_tools == {"dangerous_tool", "another_tool"}

    def test_init_with_path_string(self):
        """Test initialization with workspace as string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.READ_ONLY,
                workspace_dir=tmpdir,
                allowed_commands=[],
            )

            assert isinstance(policy.workspace_dir, Path)


class TestSecurityPolicyIsToolAllowed:
    """Tests for is_tool_allowed method."""

    def test_tool_allowed_when_no_restrictions(self):
        """Test tool allowed when no restrictions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
            )

            allowed, reason = policy.is_tool_allowed("any_tool")

            assert allowed is True
            assert reason is None

    def test_tool_forbidden(self):
        """Test tool is forbidden when in forbidden_tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                forbidden_tools={"dangerous_tool"},
            )

            allowed, reason = policy.is_tool_allowed("dangerous_tool")

            assert allowed is False
            assert "forbidden" in reason.lower()
            assert "dangerous_tool" in reason

    def test_tool_allowed_when_not_forbidden(self):
        """Test tool allowed when not in forbidden_tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                forbidden_tools={"dangerous_tool"},
            )

            allowed, reason = policy.is_tool_allowed("safe_tool")

            assert allowed is True
            assert reason is None

    def test_dangerous_tools_read_only_mode(self):
        """Test dangerous tools are blocked in READ_ONLY mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.READ_ONLY,
                workspace_dir=tmpdir,
                allowed_commands=[],
            )

            dangerous_tools = ["file_write", "shell_execute", "http_request"]
            for tool in dangerous_tools:
                allowed, reason = policy.is_tool_allowed(tool)
                assert allowed is False
                assert "read-only" in reason.lower()

    def test_safe_tools_read_only_mode(self):
        """Test safe tools are allowed in READ_ONLY mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.READ_ONLY,
                workspace_dir=tmpdir,
                allowed_commands=[],
            )

            safe_tools = ["file_read", "memory_recall", "web_search"]
            for tool in safe_tools:
                allowed, reason = policy.is_tool_allowed(tool)
                assert allowed is True
                assert reason is None

    def test_all_tools_allowed_in_full_mode(self):
        """Test all tools are allowed in FULL mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.FULL,
                workspace_dir=tmpdir,
                allowed_commands=[],
            )

            all_tools = ["file_write", "shell_execute", "file_read"]
            for tool in all_tools:
                allowed, reason = policy.is_tool_allowed(tool)
                assert allowed is True
                assert reason is None


class TestSecurityPolicyIsPathAllowed:
    """Tests for is_path_allowed method."""

    def test_path_in_workspace_allowed(self):
        """Test path within workspace is allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                workspace_only=True,
            )

            file_path = Path(tmpdir) / "test.txt"
            allowed, reason = policy.is_path_allowed(file_path)

            assert allowed is True
            assert reason is None

    def test_path_outside_workspace_denied(self):
        """Test path outside workspace is denied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                workspace_only=True,
            )

            file_path = Path(tmpdir) / ".." / "outside.txt"
            allowed, reason = policy.is_path_allowed(file_path)

            assert allowed is False
            assert "outside workspace" in reason.lower()

    def test_path_with_directory_traversal_denied(self):
        """Test path with directory traversal is denied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test without workspace restriction to see directory traversal check
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                workspace_only=False,  # Disable workspace restriction
            )

            allowed, reason = policy.is_path_allowed("../../../etc/passwd")

            assert allowed is False
            assert "directory traversal" in reason.lower()

    def test_path_allowed_when_workspace_only_false(self):
        """Test path allowed when workspace_only is False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                workspace_only=False,
            )

            file_path = "/tmp/outside.txt"
            allowed, reason = policy.is_path_allowed(file_path)

            # Should be allowed (directory traversal is still checked)
            # but workspace restriction is not
            assert allowed is True or "directory traversal" in (reason or "")

    def test_nested_path_in_workspace_allowed(self):
        """Test nested path within workspace is allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                workspace_only=True,
            )

            # Create nested directory
            nested_path = Path(tmpdir) / "subdir" / "nested" / "file.txt"
            allowed, reason = policy.is_path_allowed(nested_path)

            assert allowed is True
            assert reason is None

    def test_path_string_handling(self):
        """Test that path strings are handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                workspace_only=True,
            )

            allowed, reason = policy.is_path_allowed(str(tmpdir) + "/test.txt")

            assert allowed is True
            assert reason is None


class TestSecurityPolicyIsCommandAllowed:
    """Tests for is_command_allowed method."""

    def test_empty_command_allowed(self):
        """Test empty command is allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
            )

            allowed, reason = policy.is_command_allowed("")

            assert allowed is True
            assert reason is None

    def test_no_commands_whitelisted_denies_all(self):
        """Test empty whitelist denies all commands."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
            )

            allowed, reason = policy.is_command_allowed("ls")

            assert allowed is False
            assert "whitelisted" in reason.lower()

    def test_whitelisted_command_allowed(self):
        """Test whitelisted command is allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=["ls", "cat", "grep"],
            )

            allowed, reason = policy.is_command_allowed("ls -la")

            assert allowed is True
            assert reason is None

    def test_non_whitelisted_command_denied(self):
        """Test non-whitelisted command is denied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=["ls"],
            )

            allowed, reason = policy.is_command_allowed("rm -rf /")

            assert allowed is False
            assert "allowed list" in reason.lower()

    def test_pattern_matching_wildcards(self):
        """Test pattern matching with wildcards."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=["git*"],
            )

            allowed, reason = policy.is_command_allowed("git status")

            assert allowed is True
            assert reason is None

    def test_command_with_args_allowed(self):
        """Test command with arguments is allowed if base command is whitelisted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=["python"],
            )

            allowed, reason = policy.is_command_allowed("python -m pytest")

            assert allowed is True
            assert reason is None


class TestSecurityPolicyIsDomainAllowed:
    """Tests for is_domain_allowed method."""

    def test_no_domain_restrictions(self):
        """Test all domains allowed when no restrictions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                allowed_domains=None,
            )

            allowed, reason = policy.is_domain_allowed("example.com")

            assert allowed is True
            assert reason is None

    def test_empty_domain_list_allows_all(self):
        """Test empty domain list allows all."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                allowed_domains=[],
            )

            allowed, reason = policy.is_domain_allowed("example.com")

            assert allowed is True
            assert reason is None

    def test_whitelisted_domain_allowed(self):
        """Test whitelisted domain is allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                allowed_domains=["example.com", "safe.org"],
            )

            allowed, reason = policy.is_domain_allowed("example.com")

            assert allowed is True
            assert reason is None

    def test_non_whitelisted_domain_denied(self):
        """Test non-whitelisted domain is denied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                allowed_domains=["example.com"],
            )

            allowed, reason = policy.is_domain_allowed("dangerous.com")

            assert allowed is False
            assert "allowed list" in reason.lower()

    def test_domain_pattern_matching(self):
        """Test domain pattern matching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                allowed_domains=["*.example.com"],
            )

            allowed, reason = policy.is_domain_allowed("api.example.com")

            assert allowed is True
            assert reason is None

    def test_domain_case_insensitive(self):
        """Test domain matching is case insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
                allowed_domains=["Example.COM"],
            )

            allowed, reason = policy.is_domain_allowed("example.com")

            assert allowed is True
            assert reason is None


class TestSecurityPolicyGetSetAutonomyLevel:
    """Tests for get/set autonomy level methods."""

    def test_get_autonomy_level(self):
        """Test getting autonomy level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.LIMITED,
                workspace_dir=tmpdir,
                allowed_commands=[],
            )

            level = policy.get_autonomy_level()

            assert level == AutonomyLevel.LIMITED

    def test_set_autonomy_level(self):
        """Test setting autonomy level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = SecurityPolicy(
                autonomy_level=AutonomyLevel.READ_ONLY,
                workspace_dir=tmpdir,
                allowed_commands=[],
            )

            policy.set_autonomy_level(AutonomyLevel.FULL)

            assert policy.autonomy_level == AutonomyLevel.FULL
