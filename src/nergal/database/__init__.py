"""Database module for Nergal bot.

This module provides database connection management and repositories
for user memory storage.
"""

from nergal.database.connection import DatabaseConnection, get_database
from nergal.database.models import (
    ConversationMessage,
    ConversationSession,
    ProfileFact,
    User,
    UserProfile,
)
from nergal.database.repositories import (
    ConversationRepository,
    ProfileRepository,
    UserRepository,
)

__all__ = [
    "DatabaseConnection",
    "get_database",
    "User",
    "UserProfile",
    "ProfileFact",
    "ConversationMessage",
    "ConversationSession",
    "UserRepository",
    "ProfileRepository",
    "ConversationRepository",
]
