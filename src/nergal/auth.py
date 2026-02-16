"""Authorization service for user access control.

This module provides functionality to check if users are authorized
to use the bot and manage the allowed users list.
"""

import logging
from typing import Literal

from nergal.database.connection import get_database
from nergal.database.repositories import UserRepository

logger = logging.getLogger(__name__)


class AuthorizationService:
    """Service for managing user authorization.

    This service provides methods to check if a user is authorized
    to use the bot and manage the list of allowed users.
    """

    def __init__(self, user_repo: UserRepository | None = None) -> None:
        """Initialize the authorization service.

        Args:
            user_repo: User repository. If not provided, creates one with default database.
        """
        self._user_repo = user_repo or UserRepository()

    async def is_user_authorized(self, user_id: int) -> bool:
        """Check if a user is authorized to use the bot.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if user is authorized, False otherwise.
        """
        return await self._user_repo.is_user_allowed(user_id)

    async def authorize_user(
        self,
        user_id: int,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> bool:
        """Authorize a user to use the bot.

        Creates the user if they don't exist, or updates their info
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
        user = await self._user_repo.create_or_update(
            user_id=user_id,
            telegram_username=telegram_username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_allowed=True,
        )
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
        result = await self._user_repo.set_allowed(user_id, False)
        if result:
            logger.info("User deauthorized", user_id=user_id)
        return result

    async def get_authorized_users(self) -> list:
        """Get all authorized users.

        Returns:
            List of User instances with is_allowed=True.
        """
        return await self._user_repo.get_all_allowed()

    async def get_all_users(self, limit: int = 100, offset: int = 0) -> list:
        """Get all users with pagination.

        Args:
            limit: Maximum number of users to return.
            offset: Number of users to skip.

        Returns:
            List of User instances.
        """
        return await self._user_repo.get_all(limit=limit, offset=offset)

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user completely from the database.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if user was deleted, False if not found.
        """
        result = await self._user_repo.delete(user_id)
        if result:
            logger.info("User deleted", user_id=user_id)
        return result


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
