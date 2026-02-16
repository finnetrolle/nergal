"""Tests for authorization service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nergal.auth import AuthorizationService, check_user_authorized, get_auth_service
from nergal.database.models import User


@pytest.fixture
def mock_user_repo() -> MagicMock:
    """Create a mock user repository."""
    repo = MagicMock()
    repo.is_user_allowed = AsyncMock()
    repo.create_or_update = AsyncMock()
    repo.set_allowed = AsyncMock()
    repo.get_all_allowed = AsyncMock()
    repo.get_all = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def auth_service(mock_user_repo: MagicMock) -> AuthorizationService:
    """Create an authorization service with mock repository."""
    return AuthorizationService(user_repo=mock_user_repo)


class TestAuthorizationService:
    """Tests for AuthorizationService."""

    @pytest.mark.asyncio
    async def test_is_user_authorized_returns_true(
        self, auth_service: AuthorizationService, mock_user_repo: MagicMock
    ) -> None:
        """Test that is_user_authorized returns True for authorized user."""
        mock_user_repo.is_user_allowed.return_value = True

        result = await auth_service.is_user_authorized(123456789)

        assert result is True
        mock_user_repo.is_user_allowed.assert_called_once_with(123456789)

    @pytest.mark.asyncio
    async def test_is_user_authorized_returns_false(
        self, auth_service: AuthorizationService, mock_user_repo: MagicMock
    ) -> None:
        """Test that is_user_authorized returns False for unauthorized user."""
        mock_user_repo.is_user_allowed.return_value = False

        result = await auth_service.is_user_authorized(123456789)

        assert result is False
        mock_user_repo.is_user_allowed.assert_called_once_with(123456789)

    @pytest.mark.asyncio
    async def test_authorize_user_creates_new_user(
        self, auth_service: AuthorizationService, mock_user_repo: MagicMock
    ) -> None:
        """Test that authorize_user creates a new user with is_allowed=True."""
        expected_user = User(
            id=123456789,
            telegram_username="testuser",
            first_name="Test",
            last_name="User",
            is_allowed=True,
        )
        mock_user_repo.create_or_update.return_value = expected_user

        result = await auth_service.authorize_user(
            user_id=123456789,
            telegram_username="testuser",
            first_name="Test",
            last_name="User",
        )

        assert result == expected_user
        assert result.is_allowed is True
        mock_user_repo.create_or_update.assert_called_once_with(
            user_id=123456789,
            telegram_username="testuser",
            first_name="Test",
            last_name="User",
            language_code=None,
            is_allowed=True,
        )

    @pytest.mark.asyncio
    async def test_deauthorize_user(
        self, auth_service: AuthorizationService, mock_user_repo: MagicMock
    ) -> None:
        """Test that deauthorize_user sets is_allowed to False."""
        mock_user_repo.set_allowed.return_value = True

        result = await auth_service.deauthorize_user(123456789)

        assert result is True
        mock_user_repo.set_allowed.assert_called_once_with(123456789, False)

    @pytest.mark.asyncio
    async def test_deauthorize_user_not_found(
        self, auth_service: AuthorizationService, mock_user_repo: MagicMock
    ) -> None:
        """Test that deauthorize_user returns False if user not found."""
        mock_user_repo.set_allowed.return_value = False

        result = await auth_service.deauthorize_user(999999999)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_authorized_users(
        self, auth_service: AuthorizationService, mock_user_repo: MagicMock
    ) -> None:
        """Test getting all authorized users."""
        expected_users = [
            User(id=1, telegram_username="user1", is_allowed=True),
            User(id=2, telegram_username="user2", is_allowed=True),
        ]
        mock_user_repo.get_all_allowed.return_value = expected_users

        result = await auth_service.get_authorized_users()

        assert result == expected_users
        mock_user_repo.get_all_allowed.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_users(
        self, auth_service: AuthorizationService, mock_user_repo: MagicMock
    ) -> None:
        """Test getting all users with pagination."""
        expected_users = [
            User(id=1, telegram_username="user1", is_allowed=True),
            User(id=2, telegram_username="user2", is_allowed=False),
        ]
        mock_user_repo.get_all.return_value = expected_users

        result = await auth_service.get_all_users(limit=10, offset=0)

        assert result == expected_users
        mock_user_repo.get_all.assert_called_once_with(limit=10, offset=0)

    @pytest.mark.asyncio
    async def test_delete_user(
        self, auth_service: AuthorizationService, mock_user_repo: MagicMock
    ) -> None:
        """Test deleting a user."""
        mock_user_repo.delete.return_value = True

        result = await auth_service.delete_user(123456789)

        assert result is True
        mock_user_repo.delete.assert_called_once_with(123456789)


class TestCheckUserAuthorized:
    """Tests for the check_user_authorized convenience function."""

    @pytest.mark.asyncio
    async def test_check_user_authorized(self, mock_user_repo: MagicMock) -> None:
        """Test the convenience function for checking authorization."""
        mock_user_repo.is_user_allowed.return_value = True

        with patch("nergal.auth.get_auth_service") as mock_get_service:
            mock_get_service.return_value = AuthorizationService(user_repo=mock_user_repo)
            result = await check_user_authorized(123456789)

        assert result is True


class TestGetAuthService:
    """Tests for get_auth_service singleton."""

    def test_get_auth_service_returns_singleton(self) -> None:
        """Test that get_auth_service returns the same instance."""
        # Clear any existing instance
        import nergal.auth
        nergal.auth._auth_service = None

        service1 = get_auth_service()
        service2 = get_auth_service()

        assert service1 is service2

    def test_get_auth_service_creates_new_if_none(self) -> None:
        """Test that get_auth_service creates a new instance if none exists."""
        import nergal.auth
        nergal.auth._auth_service = None

        service = get_auth_service()

        assert service is not None
        assert isinstance(service, AuthorizationService)
