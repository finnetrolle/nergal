"""Approval manager for dangerous actions.

This module provides the ApprovalManager class which handles
requests for user approval before executing dangerous actions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


@dataclass
class ApprovalResponse:
    """Response to an approval request.

    Attributes:
        approved: Whether the action was approved.
        remember: Whether to remember this decision.
        reason: Optional reason for the decision.
    """

    approved: bool
    """Whether the action was approved."""

    remember: bool = False
    """Whether to remember this decision for future."""

    reason: str | None = None
    """Optional reason for the decision."""


class ApprovalManager:
    """Manages approval requests for dangerous actions.

    The approval manager handles requests for user approval
    before executing dangerous actions like file writes,
    shell commands, etc.

    Currently this is a no-op implementation. Channel-specific
    implementations (Telegram, Slack, etc.) should override
    or extend this class.

    Args:
        auto_approve: If True, all actions are auto-approved.
        approve_read_only: If True, read-only actions are auto-approved.

    Example:
        >>> from nergal.security.approval import ApprovalManager
        >>>
        >>> manager = ApprovalManager(auto_approve=False)
        >>> response = await manager.request_approval(
        ...     "file_write",
        ...     {"path": "/tmp/file.txt"},
        ... )
        >>> if response.approved:
        ...     # Execute the action
        ...     pass
    """

    def __init__(
        self,
        auto_approve: bool = False,
        approve_read_only: bool = True,
    ) -> None:
        """Initialize approval manager.

        Args:
            auto_approve: If True, all actions are auto-approved.
            approve_read_only: If True, read-only actions are auto-approved.
        """
        self.auto_approve = auto_approve
        self.approve_read_only = approve_read_only
        self._approved_cache: dict[tuple[str, str], bool] = {}

    def requires_approval(
        self,
        tool_name: str,
        arguments: dict,
    ) -> bool:
        """Check if an action needs approval.

        Args:
            tool_name: The name of the tool being called.
            arguments: The arguments for the tool call.

        Returns:
            True if approval is required, False otherwise.
        """
        # Auto-approve everything
        if self.auto_approve:
            return False

        # Check cache
        cache_key = (tool_name, str(arguments))
        if cache_key in self._approved_cache:
            return not self._approved_cache[cache_key]

        # Read-only actions might not need approval
        read_only_tools = {
            "file_read",
            "memory_recall",
        }

        if self.approve_read_only and tool_name in read_only_tools:
            return False

        # Dangerous tools need approval
        dangerous_tools = {
            "file_write",
            "shell_execute",
            "http_request",
            "memory_store",
        }

        return tool_name in dangerous_tools

    async def request_approval(
        self,
        tool_name: str,
        arguments: dict,
    ) -> ApprovalResponse:
        """Request approval from user.

        This is a no-op implementation that always denies
        approval. Channel-specific implementations should
        override this method to implement actual approval flow.

        Args:
            tool_name: The name of the tool being called.
            arguments: The arguments for the tool call.

        Returns:
            ApprovalResponse with decision.

        Note:
            This base implementation denies all requests. Override
            in subclasses to implement channel-specific approval UI.
        """
        logger.warning(f"Approval requested for {tool_name}, but no UI available. Denying.")

        return ApprovalResponse(
            approved=False,
            remember=False,
            reason="No approval UI available",
        )

    def remember_approval(
        self,
        tool_name: str,
        arguments: dict,
        approved: bool,
    ) -> None:
        """Remember an approval decision.

        Args:
            tool_name: The name of the tool.
            arguments: The arguments for the tool call.
            approved: Whether the action was approved.
        """
        cache_key = (tool_name, str(arguments))
        self._approved_cache[cache_key] = approved
        logger.debug(f"Remembered approval for {tool_name}: {approved}")

    def clear_cache(self) -> None:
        """Clear the approval cache.

        Useful for testing or resetting remembered approvals.
        """
        self._approved_cache.clear()
        logger.debug("Approval cache cleared")


class NoOpApprovalManager(ApprovalManager):
    """No-op approval manager that auto-approves everything.

    Useful for testing or environments where approval is not needed.
    """

    def __init__(self) -> None:
        """Initialize no-op approval manager."""
        super().__init__(auto_approve=True)

    async def request_approval(
        self,
        tool_name: str,
        arguments: dict,
    ) -> ApprovalResponse:
        """Auto-approve all requests.

        Args:
            tool_name: The name of the tool being called.
            arguments: The arguments for the tool call.

        Returns:
            ApprovalResponse with approved=True.
        """
        logger.debug(f"Auto-approving {tool_name} (no-op manager)")
        return ApprovalResponse(approved=True)
