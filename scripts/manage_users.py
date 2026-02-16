#!/usr/bin/env python3
"""CLI tool for managing bot users.

This script provides commands to add, remove, list, and manage
user authorization for the Telegram bot.

Usage:
    python -m scripts.manage_users add <user_id> [--username USERNAME] [--first-name NAME] [--last-name NAME]
    python -m scripts.manage_users remove <user_id>
    python -m scripts.manage_users list [--all] [--allowed]
    python -m scripts.manage_users allow <user_id>
    python -m scripts.manage_users deny <user_id>
    python -m scripts.manage_users show <user_id>
"""

import argparse
import asyncio
import sys
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(__file__).rsplit("/scripts", 1)[0])

from nergal.auth import AuthorizationService, get_auth_service
from nergal.config import get_settings


async def add_user(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> None:
    """Add a new user and authorize them."""
    auth = get_auth_service()
    user = await auth.authorize_user(
        user_id=user_id,
        telegram_username=username,
        first_name=first_name,
        last_name=last_name,
    )
    print(f"✅ User added and authorized:")
    print(f"   ID: {user.id}")
    if user.telegram_username:
        print(f"   Username: @{user.telegram_username}")
    if user.first_name or user.last_name:
        print(f"   Name: {user.full_name}")
    print(f"   Allowed: {user.is_allowed}")


async def remove_user(user_id: int) -> None:
    """Remove a user from the database."""
    auth = get_auth_service()
    result = await auth.delete_user(user_id)
    if result:
        print(f"✅ User {user_id} removed from database")
    else:
        print(f"❌ User {user_id} not found")


async def list_users(show_all: bool = False, show_allowed: bool = False) -> None:
    """List users in the database."""
    auth = get_auth_service()
    
    if show_allowed:
        users = await auth.get_authorized_users()
        print(f"📋 Authorized users ({len(users)}):")
    else:
        users = await auth.get_all_users(limit=1000)
        print(f"📋 All users ({len(users)}):")
    
    if not users:
        print("   No users found")
        return
    
    for user in users:
        status = "✅" if user.is_allowed else "❌"
        name_parts = []
        if user.telegram_username:
            name_parts.append(f"@{user.telegram_username}")
        if user.first_name or user.last_name:
            name_parts.append(user.full_name)
        
        name_str = f" ({', '.join(name_parts)})" if name_parts else ""
        print(f"   {status} {user.id}{name_str}")


async def allow_user(user_id: int) -> None:
    """Authorize a user to use the bot."""
    auth = get_auth_service()
    
    # First check if user exists
    from nergal.database.repositories import UserRepository
    repo = UserRepository()
    user = await repo.get_by_id(user_id)
    
    if user:
        result = await auth.deauthorize_user(user_id)  # This sets is_allowed = False, we need the opposite
        # Actually let's use the repo directly
        result = await repo.set_allowed(user_id, True)
        if result:
            print(f"✅ User {user_id} is now authorized")
        else:
            print(f"❌ Failed to authorize user {user_id}")
    else:
        print(f"❌ User {user_id} not found. Add them first with 'add' command.")


async def deny_user(user_id: int) -> None:
    """Remove a user's authorization."""
    auth = get_auth_service()
    result = await auth.deauthorize_user(user_id)
    if result:
        print(f"✅ User {user_id} authorization revoked")
    else:
        print(f"❌ User {user_id} not found or already unauthorized")


async def show_user(user_id: int) -> None:
    """Show detailed information about a user."""
    from nergal.database.repositories import UserRepository
    repo = UserRepository()
    user = await repo.get_by_id(user_id)
    
    if not user:
        print(f"❌ User {user_id} not found")
        return
    
    print(f"📋 User details:")
    print(f"   ID: {user.id}")
    print(f"   Username: @{user.telegram_username or 'not set'}")
    print(f"   First name: {user.first_name or 'not set'}")
    print(f"   Last name: {user.last_name or 'not set'}")
    print(f"   Language: {user.language_code or 'not set'}")
    print(f"   Authorized: {'✅ Yes' if user.is_allowed else '❌ No'}")
    print(f"   Created: {user.created_at or 'unknown'}")
    print(f"   Updated: {user.updated_at or 'unknown'}")


async def main_async() -> None:
    """Main async entry point."""
    parser = argparse.ArgumentParser(
        description="Manage bot users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Add and authorize a user:
    python -m scripts.manage_users add 123456789 --username johndoe --first-name John
    
  List all authorized users:
    python -m scripts.manage_users list --allowed
    
  Revoke user access:
    python -m scripts.manage_users deny 123456789
""",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Add user command
    add_parser = subparsers.add_parser("add", help="Add and authorize a new user")
    add_parser.add_argument("user_id", type=int, help="Telegram user ID")
    add_parser.add_argument("--username", "-u", help="Telegram username (without @)")
    add_parser.add_argument("--first-name", "-f", help="User's first name")
    add_parser.add_argument("--last-name", "-l", help="User's last name")
    
    # Remove user command
    remove_parser = subparsers.add_parser("remove", help="Remove a user from database")
    remove_parser.add_argument("user_id", type=int, help="Telegram user ID")
    
    # List users command
    list_parser = subparsers.add_parser("list", help="List users")
    list_parser.add_argument("--all", "-a", action="store_true", help="Show all users")
    list_parser.add_argument("--allowed", action="store_true", help="Show only authorized users")
    
    # Allow user command
    allow_parser = subparsers.add_parser("allow", help="Authorize a user")
    allow_parser.add_argument("user_id", type=int, help="Telegram user ID")
    
    # Deny user command
    deny_parser = subparsers.add_parser("deny", help="Revoke user authorization")
    deny_parser.add_argument("user_id", type=int, help="Telegram user ID")
    
    # Show user command
    show_parser = subparsers.add_parser("show", help="Show user details")
    show_parser.add_argument("user_id", type=int, help="Telegram user ID")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize database connection
    from nergal.database.connection import create_pool, close_pool
    settings = get_settings()
    
    try:
        await create_pool(settings.database)
        
        if args.command == "add":
            await add_user(
                user_id=args.user_id,
                username=args.username,
                first_name=args.first_name,
                last_name=args.last_name,
            )
        elif args.command == "remove":
            await remove_user(args.user_id)
        elif args.command == "list":
            await list_users(show_all=args.all, show_allowed=args.allowed)
        elif args.command == "allow":
            await allow_user(args.user_id)
        elif args.command == "deny":
            await deny_user(args.user_id)
        elif args.command == "show":
            await show_user(args.user_id)
    
    finally:
        await close_pool()


def main() -> None:
    """Main entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
