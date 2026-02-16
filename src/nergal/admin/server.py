"""Web admin interface for user management.

This module provides a simple web interface for managing bot users.
"""

import logging
from typing import Optional

from aiohttp import web

from nergal.auth import AuthorizationService, get_auth_service
from nergal.database.repositories import ConversationRepository, UserRepository

logger = logging.getLogger(__name__)


# HTML Templates
HTML_BASE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nergal Bot - Admin Panel</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1, h2 {{ color: #333; }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .form-group {{ margin-bottom: 15px; }}
        label {{ display: block; margin-bottom: 5px; font-weight: 500; }}
        input[type="text"],
        input[type="number"] {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        button {{
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-right: 5px;
        }}
        .btn-primary {{ background: #007bff; color: white; }}
        .btn-danger {{ background: #dc3545; color: white; }}
        .btn-success {{ background: #28a745; color: white; }}
        .btn-secondary {{ background: #6c757d; color: white; }}
        button:hover {{ opacity: 0.9; }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{ background: #f8f9fa; }}
        .status-allowed {{ color: #28a745; font-weight: bold; }}
        .status-denied {{ color: #dc3545; }}
        .alert {{
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
        .alert-success {{ background: #d4edda; color: #155724; }}
        .alert-error {{ background: #f8d7da; color: #721c24; }}
        .actions {{ white-space: nowrap; }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Nergal Bot Admin</h1>
    </div>
    {content}
</body>
</html>
"""

HTML_USERS_LIST = """
<div class="stats">
    <div class="stat-card">
        <div class="stat-value">{total_users}</div>
        <div class="stat-label">Всего пользователей</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{allowed_users}</div>
        <div class="stat-label">Авторизовано</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{total_tokens}</div>
        <div class="stat-label">Всего токенов</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{total_web_searches}</div>
        <div class="stat-label">Web-поисков</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{total_requests}</div>
        <div class="stat-label">Всего запросов</div>
    </div>
</div>

<div class="card">
    <h2>➕ Добавить пользователя</h2>
    <form action="/admin/users/add" method="post">
        <div class="form-group">
            <label for="user_id">Telegram User ID *</label>
            <input type="number" id="user_id" name="user_id" required placeholder="123456789">
        </div>
        <div class="form-group">
            <label for="username">Username (без @)</label>
            <input type="text" id="username" name="username" placeholder="johndoe">
        </div>
        <div class="form-group">
            <label for="first_name">Имя</label>
            <input type="text" id="first_name" name="first_name" placeholder="John">
        </div>
        <div class="form-group">
            <label for="last_name">Фамилия</label>
            <input type="text" id="last_name" name="last_name" placeholder="Doe">
        </div>
        <button type="submit" class="btn-primary">Добавить и авторизовать</button>
    </form>
</div>

<div class="card">
    <h2>📋 Пользователи</h2>
    {message}
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Username</th>
                <th>Имя</th>
                <th>Статус</th>
                <th>Токены</th>
                <th>Web-поиск</th>
                <th>Запросы</th>
                <th>Создан</th>
                <th class="actions">Действия</th>
            </tr>
        </thead>
        <tbody>
            {users_rows}
        </tbody>
    </table>
</div>
"""

HTML_USER_ROW = """
<tr>
    <td>{user_id}</td>
    <td>{username}</td>
    <td>{full_name}</td>
    <td class="{status_class}">{status}</td>
    <td>{tokens_used}</td>
    <td>{web_searches}</td>
    <td>{requests}</td>
    <td>{created_at}</td>
    <td class="actions">
        {action_buttons}
    </td>
</tr>
"""


class AdminServer:
    """Web admin server for user management."""

    def __init__(
        self,
        port: int = 8001,
        auth_service: AuthorizationService | None = None,
    ) -> None:
        """Initialize the admin server.

        Args:
            port: Port to run the server on.
            auth_service: Authorization service instance.
        """
        self.port = port
        self.auth_service = auth_service or get_auth_service()
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up web routes."""
        self.app.add_routes([
            web.get("/", self.handle_root),
            web.get("/admin", self.handle_users_list),
            web.get("/admin/users", self.handle_users_list),
            web.post("/admin/users/add", self.handle_user_add),
            web.post("/admin/users/{user_id}/allow", self.handle_user_allow),
            web.post("/admin/users/{user_id}/deny", self.handle_user_deny),
            web.post("/admin/users/{user_id}/delete", self.handle_user_delete),
        ])

    async def handle_root(self, request: web.Request) -> web.Response:
        """Redirect root to admin panel."""
        raise web.HTTPFound("/admin")

    async def handle_users_list(self, request: web.Request) -> web.Response:
        """Show list of all users."""
        message = request.query.get("message", "")
        message_type = request.query.get("message_type", "success")
        
        # Get users
        users = await self.auth_service.get_all_users(limit=100)
        allowed_users = await self.auth_service.get_authorized_users()
        
        # Get user statistics with error handling
        all_stats: dict[int, dict[str, int]] = {}
        try:
            conv_repo = ConversationRepository()
            all_stats = await conv_repo.get_all_users_stats()
        except Exception as e:
            logger.warning("Could not fetch user statistics", error=str(e))
            all_stats = {}
        
        # Calculate totals for summary (ensure int conversion for PostgreSQL bigint)
        total_tokens = int(sum(stats.get("tokens_used", 0) for stats in all_stats.values()))
        total_web_searches = int(sum(stats.get("web_searches", 0) for stats in all_stats.values()))
        total_requests = int(sum(stats.get("requests", 0) for stats in all_stats.values()))
        
        # Build user rows
        users_rows = []
        for user in users:
            # Get stats for this user, default to zeros if not found (ensure int conversion)
            raw_stats = all_stats.get(user.id, {"tokens_used": 0, "web_searches": 0, "requests": 0})
            stats = {
                "tokens_used": int(raw_stats.get("tokens_used", 0)),
                "web_searches": int(raw_stats.get("web_searches", 0)),
                "requests": int(raw_stats.get("requests", 0)),
            }
            
            if user.is_allowed:
                status = "✅ Авторизован"
                status_class = "status-allowed"
                action_buttons = """
                    <form action="/admin/users/{user_id}/deny" method="post" style="display:inline">
                        <button type="submit" class="btn-secondary">Заблокировать</button>
                    </form>
                """.format(user_id=user.id)
            else:
                status = "❌ Не авторизован"
                status_class = "status-denied"
                action_buttons = """
                    <form action="/admin/users/{user_id}/allow" method="post" style="display:inline">
                        <button type="submit" class="btn-success">Разрешить</button>
                    </form>
                """.format(user_id=user.id)
            
            action_buttons += """
                <form action="/admin/users/{user_id}/delete" method="post" style="display:inline"
                      onsubmit="return confirm('Удалить пользователя?')">
                    <button type="submit" class="btn-danger">Удалить</button>
                </form>
            """.format(user_id=user.id)
            
            users_rows.append(HTML_USER_ROW.format(
                user_id=user.id,
                username=f"@{user.telegram_username}" if user.telegram_username else "-",
                full_name=user.full_name,
                status=status,
                status_class=status_class,
                tokens_used=stats.get("tokens_used", 0),
                web_searches=stats.get("web_searches", 0),
                requests=stats.get("requests", 0),
                created_at=user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "-",
                action_buttons=action_buttons,
            ))
        
        # Build message alert
        message_html = ""
        if message:
            alert_class = "alert-success" if message_type == "success" else "alert-error"
            message_html = f'<div class="alert {alert_class}">{message}</div>'
        
        content = HTML_USERS_LIST.format(
            total_users=len(users),
            allowed_users=len(allowed_users),
            total_tokens=total_tokens,
            total_web_searches=total_web_searches,
            total_requests=total_requests,
            message=message_html,
            users_rows="".join(users_rows) if users_rows else "<tr><td colspan='9'>Нет пользователей</td></tr>",
        )
        
        html = HTML_BASE.format(content=content)
        return web.Response(text=html, content_type="text/html")

    async def handle_user_add(self, request: web.Request) -> web.Response:
        """Add a new user."""
        data = await request.post()
        
        try:
            user_id = int(data.get("user_id", 0))
            if user_id <= 0:
                raise ValueError("Invalid user ID")
        except (ValueError, TypeError):
            raise web.HTTPFound("/admin/users?message=Неверный User ID&message_type=error")
        
        username = data.get("username") or None
        first_name = data.get("first_name") or None
        last_name = data.get("last_name") or None
        
        try:
            await self.auth_service.authorize_user(
                user_id=user_id,
                telegram_username=username,
                first_name=first_name,
                last_name=last_name,
            )
            logger.info("User added via admin panel", user_id=user_id)
            raise web.HTTPFound("/admin/users?message=Пользователь добавлен и авторизован")
        except Exception as e:
            logger.error("Error adding user", error=str(e))
            raise web.HTTPFound(f"/admin/users?message=Ошибка: {e}&message_type=error")

    async def handle_user_allow(self, request: web.Request) -> web.Response:
        """Authorize a user."""
        user_id = int(request.match_info["user_id"])
        
        try:
            repo = UserRepository()
            result = await repo.set_allowed(user_id, True)
            if result:
                logger.info("User authorized via admin panel", user_id=user_id)
                raise web.HTTPFound("/admin/users?message=Пользователь авторизован")
            else:
                raise web.HTTPFound("/admin/users?message=Пользователь не найден&message_type=error")
        except Exception as e:
            logger.error("Error authorizing user", error=str(e))
            raise web.HTTPFound(f"/admin/users?message=Ошибка: {e}&message_type=error")

    async def handle_user_deny(self, request: web.Request) -> web.Response:
        """Deauthorize a user."""
        user_id = int(request.match_info["user_id"])
        
        try:
            result = await self.auth_service.deauthorize_user(user_id)
            if result:
                logger.info("User deauthorized via admin panel", user_id=user_id)
                raise web.HTTPFound("/admin/users?message=Доступ пользователя отозван")
            else:
                raise web.HTTPFound("/admin/users?message=Пользователь не найден&message_type=error")
        except Exception as e:
            logger.error("Error deauthorizing user", error=str(e))
            raise web.HTTPFound(f"/admin/users?message=Ошибка: {e}&message_type=error")

    async def handle_user_delete(self, request: web.Request) -> web.Response:
        """Delete a user."""
        user_id = int(request.match_info["user_id"])
        
        try:
            result = await self.auth_service.delete_user(user_id)
            if result:
                logger.info("User deleted via admin panel", user_id=user_id)
                raise web.HTTPFound("/admin/users?message=Пользователь удален")
            else:
                raise web.HTTPFound("/admin/users?message=Пользователь не найден&message_type=error")
        except Exception as e:
            logger.error("Error deleting user", error=str(e))
            raise web.HTTPFound(f"/admin/users?message=Ошибка: {e}&message_type=error")

    def run(self) -> None:
        """Run the admin server."""
        web.run_app(self.app, host="0.0.0.0", port=self.port, print=None)


def run_admin_server(port: int = 8001) -> None:
    """Run the admin server standalone."""
    import asyncio
    from nergal.database.connection import create_pool, close_pool
    from nergal.config import get_settings
    
    async def main() -> None:
        settings = get_settings()
        await create_pool(settings.database)
        
        server = AdminServer(port=port)
        runner = web.AppRunner(server.app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        
        print(f"Admin panel running at http://localhost:{port}")
        print("Press Ctrl+C to stop")
        
        await site.start()
        
        try:
            # Run forever
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            await runner.cleanup()
            await close_pool()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped")


if __name__ == "__main__":
    run_admin_server()
