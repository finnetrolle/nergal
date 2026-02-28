"""Authorization service for user access control.

This module provides functionality to check if users are authorized
to use bot and manage allowed users list (all in-memory).
"""

import logging
from dataclasses import dataclass
from typing import Literal

from nergal.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class User:
    """User information for authorization."""

    id: int
    telegram_username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None
    is_allowed: bool = True

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts)) or f"User {self.id}"


class AuthorizationService:
    """Service for managing user authorization.

    This service provides methods to check if a user is authorized
    to use bot and manage the list of allowed users.
    """

    def __init__(self) -> None:
        """Initialize the in-memory authorization service."""
        self._users: dict[int, User] = {}
        self._settings = get_settings()

        # Pre-authorize admin users from config
        for admin_id in self._settings.auth.admin_user_ids:
            self._users[admin_id] = User(id=admin_id, is_allowed=True)

        if self._settings.auth.admin_user_ids:
            logger.info(
                f"Pre-authorized admin users: {self._settings.auth.admin_user_ids}"
            )

    async def is_user_authorized(self, user_id: int) -> bool:
        """Check if a user is authorized to use bot.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if user is authorized, False otherwise.
        """
        user = self._users.get(user_id)
        return user is not None and user.is_allowed

    async def authorize_user(
        self,
        user_id: int,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> User:
        """Authorize a user to use bot.

        Creates user if they don't exist, or updates their info
        and sets is_allowed to True.

        Args:
            user_id: Telegram user ID.
            telegram_username: Telegram username.
            first_name: User's first name.
            last_name: User's last name.
            language_code: User's language code.

        Returns:
            The created/updated User instance.
        """
        if user_id in self._users:
            user = self._users[user_id]
            # Update user info
            if telegram_username is not None:
                user.telegram_username = telegram_username
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            if language_code is not None:
                user.language_code = language_code
            user.is_allowed = True
        else:
            # Create new user
            user = User(
                id=user_id,
                telegram_username=telegram_username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                is_allowed=True,
            )
            self._users[user_id] = user

        logger.info(
            "User authorized",
            user_id=user_id,
            username=telegram_username,
        )
        return user

    async def deauthorize_user(self, user_id: int) -> bool:
        """Remove a user's authorization.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if user was deauthorized, False if not found.
        """
        user = self._users.get(user_id)
        if user:
            user.is_allowed = False
            logger.info("User deauthorized", user_id=user_id)
            return True
        return False

    async def get_authorized_users(self) -> list[User]:
        """Get all authorized users.

        Returns:
            List of User instances with is_allowed=True.
        """
        return [u for u in self._users.values() if u.is_allowed]

    async def get_all_users(self, limit: int = 100, offset: int = 0) -> list[User]:
        """Get all users with pagination.

        Args:
            limit: Maximum number of users to return.
            offset: Number of users to skip.

        Returns:
            List of User instances.
        """
        users = list(self._users.values())
        total = len(users)
        end = min(offset + limit, total)
        return users[offset:end]

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user completely from memory.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if user was deleted, False if not found.
        """
        if user_id in self._users:
            del self._users[user_id]
            logger.info("User deleted", user_id=user_id)
            return True
        return False


# Global authorization service instance
_auth_service: AuthorizationService | None = None


def get_auth_service() -> AuthorizationService:
    """Get the global authorization service instance.

    Returns:
        AuthorizationService instance.
    """
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthorizationService()
    return _auth_service


async def check_user_authorized(user_id: int) -> bool:
    """Convenience function to check if a user is authorized.

    Args:
        user_id: Telegram user ID.

    Returns:
        True if user is authorized, False otherwise.
    """
    return await get_auth_service().is_user_authorized(user_id)
