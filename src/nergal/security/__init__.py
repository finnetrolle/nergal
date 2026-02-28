"""Security system for controlling agent behavior.

This package provides security controls for agent operations,
including autonomy levels, policy enforcement, and approval system.

Components:
    - policy: Security policy with autonomy levels
    - approval: Approval manager for dangerous actions
"""

from nergal.security.approval import ApprovalManager
from nergal.security.policy import AutonomyLevel, SecurityPolicy

__all__ = ["SecurityPolicy", "AutonomyLevel", "ApprovalManager"]
