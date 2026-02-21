"""Database module for Nergal bot.

This module provides database connection management and repositories
for user memory storage.
"""

from nergal.database.connection import DatabaseConnection, get_database
from nergal.database.migrations import run_migrations
from nergal.database.models import (
    ConversationMessage,
    ConversationSession,
    ProfileFact,
    User,
    UserIntegration,
    UserProfile,
)
from nergal.database.repositories import (
    ConversationRepository,
    ProfileRepository,
    UserIntegrationRepository,
    UserRepository,
)

__all__ = [
    "DatabaseConnection",
    "get_database",
    "run_migrations",
    "User",
    "UserProfile",
    "UserIntegration",
    "ProfileFact",
    "ConversationMessage",
    "ConversationSession",
    "UserRepository",
    "ProfileRepository",
    "UserIntegrationRepository",
    "ConversationRepository",
]
