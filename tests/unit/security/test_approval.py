"""Tests for approval manager."""

import pytest

from nergal.security.approval import (
    ApprovalManager,
    ApprovalResponse,
    NoOpApprovalManager,
)


class TestApprovalResponse:
    """Tests for ApprovalResponse dataclass."""

    def test_approval_response_approved(self):
        """Test approval response with approved=True."""
        response = ApprovalResponse(approved=True)

        assert response.approved is True
        assert response.remember is False
        assert response.reason is None

    def test_approval_response_with_remember(self):
        """Test approval response with remember=True."""
        response = ApprovalResponse(approved=True, remember=True)

        assert response.approved is True
        assert response.remember is True

    def test_approval_response_with_reason(self):
        """Test approval response with reason."""
        response = ApprovalResponse(
            approved=False,
            reason="Action too dangerous",
        )

        assert response.approved is False
        assert response.reason == "Action too dangerous"

    def test_approval_response_all_fields(self):
        """Test approval response with all fields."""
        response = ApprovalResponse(
            approved=True,
            remember=True,
            reason="For testing purposes",
        )

        assert response.approved is True
        assert response.remember is True
        assert response.reason == "For testing purposes"


class TestApprovalManager:
    """Tests for ApprovalManager class."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        manager = ApprovalManager()

        assert manager.auto_approve is False
        assert manager.approve_read_only is True
        assert manager._approved_cache == {}

    def test_init_auto_approve_true(self):
        """Test initialization with auto_approve=True."""
        manager = ApprovalManager(auto_approve=True)

        assert manager.auto_approve is True

    def test_init_approve_read_only_false(self):
        """Test initialization with approve_read_only=False."""
        manager = ApprovalManager(approve_read_only=False)

        assert manager.approve_read_only is False

    def test_requires_approval_auto_approve(self):
        """Test requires_approval with auto_approve=True."""
        manager = ApprovalManager(auto_approve=True)

        requires = manager.requires_approval("any_tool", {})

        assert requires is False

    def test_requires_approval_dangerous_tool(self):
        """Test dangerous tools require approval."""
        manager = ApprovalManager(auto_approve=False, approve_read_only=False)

        dangerous_tools = ["file_write", "shell_execute", "http_request", "memory_store"]
        for tool in dangerous_tools:
            requires = manager.requires_approval(tool, {})
            assert requires is True

    def test_requires_approval_read_only_tool_with_auto(self):
        """Test read-only tools don't require approval when approve_read_only=True."""
        manager = ApprovalManager(auto_approve=False, approve_read_only=True)

        read_only_tools = ["file_read", "memory_recall"]
        for tool in read_only_tools:
            requires = manager.requires_approval(tool, {})
            assert requires is False

    def test_requires_approval_read_only_tool_without_auto(self):
        """Test read-only tools may require approval when approve_read_only=False."""
        manager = ApprovalManager(auto_approve=False, approve_read_only=False)

        # Read-only tools are NOT in dangerous_tools list, so they don't require approval
        # They would only be auto-approved when approve_read_only=True
        read_only_tools = ["file_read", "memory_recall"]
        for tool in read_only_tools:
            requires = manager.requires_approval(tool, {})
            assert requires is False

    def test_requires_approval_cache_hit(self):
        """Test cache is used for remembered approvals."""
        manager = ApprovalManager(auto_approve=False, approve_read_only=False)

        # Cache approval
        manager.remember_approval("file_write", {"path": "/tmp/test"}, approved=True)

        # Should not require approval because it's cached
        requires = manager.requires_approval("file_write", {"path": "/tmp/test"})

        assert requires is False

    def test_requires_approval_cache_deny(self):
        """Test cached denials still require approval."""
        manager = ApprovalManager(auto_approve=False, approve_read_only=False)

        # Cache denial
        manager.remember_approval("shell_execute", {"cmd": "rm"}, approved=False)

        # Should still require approval
        requires = manager.requires_approval("shell_execute", {"cmd": "rm"})

        assert requires is True

    @pytest.mark.asyncio
    async def test_request_approval_default_denies(self):
        """Test default request_approval denies all requests."""
        manager = ApprovalManager()

        response = await manager.request_approval("file_write", {"path": "/tmp/file"})

        assert response.approved is False
        assert response.remember is False
        assert response.reason == "No approval UI available"

    @pytest.mark.asyncio
    async def test_request_approval_different_tools(self):
        """Test request_approval for different tools."""
        manager = ApprovalManager()

        tools = [
            ("file_write", {"path": "/tmp/file"}),
            ("shell_execute", {"cmd": "ls"}),
            ("http_request", {"url": "https://example.com"}),
        ]

        for tool_name, args in tools:
            response = await manager.request_approval(tool_name, args)

            assert response.approved is False
            assert response.reason == "No approval UI available"

    def test_remember_approval(self):
        """Test remembering approval decision."""
        manager = ApprovalManager()

        manager.remember_approval("file_write", {"path": "/tmp/test"}, approved=True)

        cache_key = ("file_write", "{'path': '/tmp/test'}")
        assert cache_key in manager._approved_cache
        assert manager._approved_cache[cache_key] is True

    def test_remember_approval_multiple(self):
        """Test remembering multiple approvals."""
        manager = ApprovalManager()

        approvals = [
            ("file_write", {"path": "/tmp/test1"}, True),
            ("shell_execute", {"cmd": "ls"}, False),
            ("http_request", {"url": "https://example.com"}, True),
        ]

        for tool, args, approved in approvals:
            manager.remember_approval(tool, args, approved)

        assert len(manager._approved_cache) == 3

    def test_clear_cache(self):
        """Test clearing approval cache."""
        manager = ApprovalManager()

        manager.remember_approval("file_write", {"path": "/tmp/test"}, approved=True)
        manager.remember_approval("shell_execute", {"cmd": "ls"}, approved=True)

        assert len(manager._approved_cache) == 2

        manager.clear_cache()

        assert len(manager._approved_cache) == 0

    def test_clear_cache_when_empty(self):
        """Test clearing cache when it's already empty."""
        manager = ApprovalManager()

        manager.clear_cache()

        assert len(manager._approved_cache) == 0


class TestNoOpApprovalManager:
    """Tests for NoOpApprovalManager class."""

    def test_init(self):
        """Test NoOpApprovalManager initialization."""
        manager = NoOpApprovalManager()

        assert manager.auto_approve is True

    def test_requires_approval_always_false(self):
        """Test requires_approval always returns False."""
        manager = NoOpApprovalManager()

        tools = [
            ("file_write", {"path": "/tmp/file"}),
            ("shell_execute", {"cmd": "rm -rf /"}),
            ("http_request", {"url": "https://example.com"}),
        ]

        for tool_name, args in tools:
            requires = manager.requires_approval(tool_name, args)
            assert requires is False

    @pytest.mark.asyncio
    async def test_request_approval_always_approves(self):
        """Test request_approval always approves."""
        manager = NoOpApprovalManager()

        tools = [
            ("file_write", {"path": "/tmp/file"}),
            ("shell_execute", {"cmd": "ls"}),
            ("http_request", {"url": "https://example.com"}),
        ]

        for tool_name, args in tools:
            response = await manager.request_approval(tool_name, args)

            assert response.approved is True
            assert response.remember is False
            assert response.reason is None

    def test_inheritance(self):
        """Test NoOpApprovalManager inherits from ApprovalManager."""
        manager = NoOpApprovalManager()

        assert isinstance(manager, ApprovalManager)

    def test_cache_still_works(self):
        """Test cache functionality still works in NoOpApprovalManager."""
        manager = NoOpApprovalManager()

        manager.remember_approval("file_write", {"path": "/tmp/test"}, approved=True)

        cache_key = ("file_write", "{'path': '/tmp/test'}")
        assert cache_key in manager._approved_cache
        assert manager._approved_cache[cache_key] is True
