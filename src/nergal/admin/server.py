"""Web admin interface for user management.

This module provides a simple web interface for managing bot users.
"""

from typing import Optional

from aiohttp import web

from nergal.auth import AuthorizationService, get_auth_service
from nergal.database.repositories import (
    ConversationRepository,
    UserRepository,
    WebSearchTelemetryRepository,
)
from nergal.monitoring.logging_config import get_logger

logger = get_logger(__name__)


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
        .nav {{
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
        }}
        .nav a {{
            padding: 8px 16px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }}
        .nav a:hover {{
            background: #0056b3;
        }}
        .nav a.active {{
            background: #0056b3;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-success {{ background: #d4edda; color: #155724; }}
        .badge-error {{ background: #f8d7da; color: #721c24; }}
        .badge-warning {{ background: #fff3cd; color: #856404; }}
        .badge-info {{ background: #d1ecf1; color: #0c5460; }}
        .telemetry-details {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        .error-message {{
            color: #721c24;
            background: #f8d7da;
            padding: 10px;
            border-radius: 4px;
            margin-top: 5px;
        }}
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .tab {{
            padding: 10px 20px;
            background: #e9ecef;
            border-radius: 4px 4px 0 0;
            text-decoration: none;
            color: #333;
        }}
        .tab:hover {{
            background: #dee2e6;
        }}
        .tab.active {{
            background: #007bff;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Nergal Bot Admin</h1>
    </div>
    <div class="nav">
        <a href="/admin" class="{nav_users}">Пользователи</a>
        <a href="/admin/telemetry" class="{nav_telemetry}">Web Search Telemetry</a>
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

# Telemetry page templates
HTML_TELEMETRY_DASHBOARD = """
<div class="stats">
    <div class="stat-card">
        <div class="stat-value">{total_searches}</div>
        <div class="stat-label">Всего поисков</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{successful_searches}</div>
        <div class="stat-label">Успешных</div>
    </div>
    <div class="stat-card">
        <div class="stat-value" style="color: #dc3545;">{failed_searches}</div>
        <div class="stat-label">Ошибок</div>
    </div>
    <div class="stat-card">
        <div class="stat-value" style="color: #ffc107;">{empty_results}</div>
        <div class="stat-label">Пустых результатов</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{avg_response_time}ms</div>
        <div class="stat-label">Среднее время ответа</div>
    </div>
</div>

<div class="tabs">
    <a href="/admin/telemetry" class="tab {tab_recent_active}">Последние поиски</a>
    <a href="/admin/telemetry/failures" class="tab {tab_failures_active}">Ошибки</a>
    <a href="/admin/telemetry/empty" class="tab {tab_empty_active}">Пустые результаты</a>
    <a href="/admin/telemetry/stats" class="tab {tab_stats_active}">Статистика</a>
</div>

{content}
"""

HTML_TELEMETRY_TABLE = """
<div class="card">
    <h2>{title}</h2>
    <table>
        <thead>
            <tr>
                <th>Время</th>
                <th>Запрос</th>
                <th>Статус</th>
                <th>Результатов</th>
                <th>Время (мс)</th>
                <th>Категория</th>
                <th>Retries</th>
                <th class="actions">Действия</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</div>
"""

HTML_TELEMETRY_ROW = """
<tr>
    <td>{created_at}</td>
    <td>{query}</td>
    <td><span class="badge {badge_class}">{status}</span></td>
    <td>{results_count}</td>
    <td>{duration}</td>
    <td>{error_category}</td>
    <td>{retry_info}</td>
    <td class="actions">
        <a href="/admin/telemetry/{id}" class="btn-primary" style="text-decoration:none; padding: 5px 10px;">Детали</a>
    </td>
</tr>
"""

HTML_TELEMETRY_DETAIL = """
<div class="card">
    <h2>🔍 Детали поиска</h2>
    <p><a href="/admin/telemetry">← Назад к списку</a></p>
    
    <table>
        <tr><th>Запрос</th><td>{query}</td></tr>
        <tr><th>Статус</th><td><span class="badge {badge_class}">{status}</span></td></tr>
        <tr><th>Категория ошибки</th><td>{error_category}</td></tr>
        <tr><th>Результатов</th><td>{results_count}</td></tr>
        <tr><th>Время</th><td>{created_at}</td></tr>
        <tr><th>User ID</th><td>{user_id}</td></tr>
        <tr><th>Session ID</th><td>{session_id}</td></tr>
    </table>
</div>

{retry_section}

{error_section}

<div class="card">
    <h2>⏱️ Тайминги</h2>
    <table>
        <tr><th>Общее время</th><td>{total_duration_ms} ms</td></tr>
        <tr><th>MCP Init</th><td>{init_duration_ms} ms</td></tr>
        <tr><th>Tools List</th><td>{tools_list_duration_ms} ms</td></tr>
        <tr><th>Search Call</th><td>{search_call_duration_ms} ms</td></tr>
        <tr><th>Retry Delay</th><td>{total_retry_delay_ms} ms</td></tr>
    </table>
</div>

<div class="card">
    <h2>🔧 Технические детали</h2>
    <table>
        <tr><th>Provider</th><td>{provider_name}</td></tr>
        <tr><th>Tool Used</th><td>{tool_used}</td></tr>
        <tr><th>HTTP Status</th><td>{http_status_code}</td></tr>
        <tr><th>API Session ID</th><td>{api_session_id}</td></tr>
    </table>
</div>

{results_section}

{raw_response_section}
"""

HTML_ERROR_SECTION = """
<div class="card">
    <h2>❌ Информация об ошибке</h2>
    <table>
        <tr><th>Тип ошибки</th><td>{error_type}</td></tr>
    </table>
    <div class="error-message">
        <strong>Сообщение:</strong><br>
        {error_message}
    </div>
    {stack_trace_section}
</div>
"""

HTML_STACK_TRACE = """
<div style="margin-top: 10px;">
    <strong>Stack Trace:</strong>
    <div class="telemetry-details">{error_stack_trace}</div>
</div>
"""

HTML_RETRY_SECTION = """
<div class="card">
    <h2>🔄 Информация о повторных попытках</h2>
    <table>
        <tr><th>Количество попыток</th><td>{retry_count}</td></tr>
        <tr><th>Общая задержка</th><td>{total_retry_delay_ms} ms</td></tr>
    </table>
    {retry_reasons_section}
</div>
"""

HTML_RETRY_REASONS_SECTION = """
<div style="margin-top: 10px;">
    <strong>Причины повторных попыток:</strong>
    <ul style="margin: 5px 0; padding-left: 20px;">
        {retry_reasons_list}
    </ul>
</div>
"""

HTML_RESULTS_SECTION = """
<div class="card">
    <h2>📋 Результаты поиска ({count})</h2>
    {results_list}
</div>
"""

HTML_RESULT_ITEM = """
<div style="padding: 10px; border-bottom: 1px solid #ddd;">
    <strong>{title}</strong><br>
    <small style="color: #666;">{link}</small><br>
    <p style="margin: 5px 0;">{content}</p>
</div>
"""

HTML_RAW_RESPONSE = """
<div class="card">
    <h2>📄 Raw Response {truncated_badge}</h2>
    <div class="telemetry-details">{raw_response}</div>
</div>
"""

HTML_STATS_SECTION = """
<div class="card">
    <h2>📊 Статистика за {days} дней</h2>
    {content}
</div>
"""

HTML_DAILY_STATS_TABLE = """
<table>
    <thead>
        <tr>
            <th>Дата</th>
            <th>Всего</th>
            <th>Успешных</th>
            <th>Ошибок</th>
            <th>Пустых</th>
            <th>Среднее время (мс)</th>
            <th>Среднее результатов</th>
        </tr>
    </thead>
    <tbody>
        {rows}
    </tbody>
</table>
"""

HTML_ERROR_TYPES_TABLE = """
<div class="card">
    <h2>🐛 Частые ошибки</h2>
    <table>
        <thead>
            <tr>
                <th>Тип ошибки</th>
                <th>Сообщение</th>
                <th>Количество</th>
                <th>Последнее появление</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</div>
"""

HTML_POPULAR_QUERIES_TABLE = """
<div class="card">
    <h2>🔍 Популярные запросы</h2>
    <table>
        <thead>
            <tr>
                <th>Запрос</th>
                <th>Поисков</th>
                <th>Успешных</th>
                <th>Ошибок</th>
                <th>Среднее результатов</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</div>
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
            # Telemetry routes
            web.get("/admin/telemetry", self.handle_telemetry_dashboard),
            web.get("/admin/telemetry/failures", self.handle_telemetry_failures),
            web.get("/admin/telemetry/empty", self.handle_telemetry_empty),
            web.get("/admin/telemetry/stats", self.handle_telemetry_stats),
            web.get("/admin/telemetry/{telemetry_id}", self.handle_telemetry_detail),
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
        
        html = HTML_BASE.format(content=content, nav_users="active", nav_telemetry="")
        return web.Response(text=html, content_type="text/html")

    async def handle_telemetry_dashboard(self, request: web.Request) -> web.Response:
        """Show telemetry dashboard with recent searches."""
        repo = WebSearchTelemetryRepository()
        
        # Get stats and recent searches
        stats = await repo.get_stats(days=7)
        recent = await repo.get_recent(limit=50)
        
        # Build rows
        rows = []
        for t in recent:
            rows.append(self._format_telemetry_row(t))
        
        content = HTML_TELEMETRY_DASHBOARD.format(
            total_searches=stats["total_searches"],
            successful_searches=stats["successful_searches"],
            failed_searches=stats["failed_searches"],
            empty_results=stats["empty_result_searches"],
            avg_response_time=int(stats["avg_response_time_ms"] or 0),
            tab_recent_active="active",
            tab_failures_active="",
            tab_empty_active="",
            tab_stats_active="",
            content=HTML_TELEMETRY_TABLE.format(
                title="Последние поиски",
                rows="".join(rows) if rows else "<tr><td colspan='7'>Нет данных</td></tr>",
            ),
        )
        
        html = HTML_BASE.format(content=content, nav_users="", nav_telemetry="active")
        return web.Response(text=html, content_type="text/html")

    async def handle_telemetry_failures(self, request: web.Request) -> web.Response:
        """Show failed searches."""
        repo = WebSearchTelemetryRepository()
        
        stats = await repo.get_stats(days=7)
        failures = await repo.get_failures(limit=100)
        
        rows = []
        for t in failures:
            rows.append(self._format_telemetry_row(t))
        
        content = HTML_TELEMETRY_DASHBOARD.format(
            total_searches=stats["total_searches"],
            successful_searches=stats["successful_searches"],
            failed_searches=stats["failed_searches"],
            empty_results=stats["empty_result_searches"],
            avg_response_time=int(stats["avg_response_time_ms"] or 0),
            tab_recent_active="",
            tab_failures_active="active",
            tab_empty_active="",
            tab_stats_active="",
            content=HTML_TELEMETRY_TABLE.format(
                title="Ошибки поиска",
                rows="".join(rows) if rows else "<tr><td colspan='7'>Нет ошибок</td></tr>",
            ),
        )
        
        html = HTML_BASE.format(content=content, nav_users="", nav_telemetry="active")
        return web.Response(text=html, content_type="text/html")

    async def handle_telemetry_empty(self, request: web.Request) -> web.Response:
        """Show searches with empty results."""
        repo = WebSearchTelemetryRepository()
        
        stats = await repo.get_stats(days=7)
        empty = await repo.get_empty_results(limit=100)
        
        rows = []
        for t in empty:
            rows.append(self._format_telemetry_row(t))
        
        content = HTML_TELEMETRY_DASHBOARD.format(
            total_searches=stats["total_searches"],
            successful_searches=stats["successful_searches"],
            failed_searches=stats["failed_searches"],
            empty_results=stats["empty_result_searches"],
            avg_response_time=int(stats["avg_response_time_ms"] or 0),
            tab_recent_active="",
            tab_failures_active="",
            tab_empty_active="active",
            tab_stats_active="",
            content=HTML_TELEMETRY_TABLE.format(
                title="Поиски без результатов",
                rows="".join(rows) if rows else "<tr><td colspan='7'>Нет пустых результатов</td></tr>",
            ),
        )
        
        html = HTML_BASE.format(content=content, nav_users="", nav_telemetry="active")
        return web.Response(text=html, content_type="text/html")

    async def handle_telemetry_stats(self, request: web.Request) -> web.Response:
        """Show telemetry statistics."""
        repo = WebSearchTelemetryRepository()
        
        days = int(request.query.get("days", 30))
        stats = await repo.get_stats(days=7)
        daily_stats = await repo.get_daily_stats(days=days)
        error_types = await repo.get_error_types(days=days)
        popular_queries = await repo.get_popular_queries(days=days)
        
        # Daily stats rows
        daily_rows = []
        for ds in daily_stats:
            daily_rows.append(f"""
                <tr>
                    <td>{ds['date']}</td>
                    <td>{ds['total_searches']}</td>
                    <td>{ds['successful_searches']}</td>
                    <td>{ds['failed_searches']}</td>
                    <td>{ds['empty_result_searches']}</td>
                    <td>{int(ds['avg_total_duration_ms'] or 0)}</td>
                    <td>{ds['avg_results_count'] or 0:.1f}</td>
                </tr>
            """)
        
        # Error types rows
        error_rows = []
        for et in error_types:
            error_rows.append(f"""
                <tr>
                    <td>{et['error_type'] or '-'}</td>
                    <td>{(et['error_message'] or '-')[:100]}</td>
                    <td>{et['count']}</td>
                    <td>{et['last_occurrence'] or '-'}</td>
                </tr>
            """)
        
        # Popular queries rows
        query_rows = []
        for pq in popular_queries:
            query_rows.append(f"""
                <tr>
                    <td>{pq['query'][:50]}{'...' if len(pq['query']) > 50 else ''}</td>
                    <td>{pq['search_count']}</td>
                    <td>{pq['success_count']}</td>
                    <td>{pq['error_count']}</td>
                    <td>{pq['avg_results'] or 0:.1f}</td>
                </tr>
            """)
        
        stats_content = HTML_DAILY_STATS_TABLE.format(
            rows="".join(daily_rows) if daily_rows else "<tr><td colspan='7'>Нет данных</td></tr>",
        )
        
        stats_content += HTML_ERROR_TYPES_TABLE.format(
            rows="".join(error_rows) if error_rows else "<tr><td colspan='4'>Нет ошибок</td></tr>",
        )
        
        stats_content += HTML_POPULAR_QUERIES_TABLE.format(
            rows="".join(query_rows) if query_rows else "<tr><td colspan='5'>Нет данных</td></tr>",
        )
        
        content = HTML_TELEMETRY_DASHBOARD.format(
            total_searches=stats["total_searches"],
            successful_searches=stats["successful_searches"],
            failed_searches=stats["failed_searches"],
            empty_results=stats["empty_result_searches"],
            avg_response_time=int(stats["avg_response_time_ms"] or 0),
            tab_recent_active="",
            tab_failures_active="",
            tab_empty_active="",
            tab_stats_active="active",
            content=HTML_STATS_SECTION.format(days=days, content=stats_content),
        )
        
        html = HTML_BASE.format(content=content, nav_users="", nav_telemetry="active")
        return web.Response(text=html, content_type="text/html")

    async def handle_telemetry_detail(self, request: web.Request) -> web.Response:
        """Show detailed telemetry for a single search."""
        import json
        from uuid import UUID
        
        telemetry_id = UUID(request.match_info["telemetry_id"])
        repo = WebSearchTelemetryRepository()
        
        telemetry = await repo.get_by_id(telemetry_id)
        if not telemetry:
            raise web.HTTPFound("/admin/telemetry")
        
        # Determine badge class
        badge_class = {
            "success": "badge-success",
            "error": "badge-error",
            "timeout": "badge-error",
            "empty": "badge-warning",
        }.get(telemetry.status, "badge-info")
        
        # Build retry section if applicable
        retry_section = ""
        if telemetry.retry_count and telemetry.retry_count > 0:
            retry_reasons_section = ""
            if telemetry.retry_reasons:
                reasons_list = "".join([f"<li>{r}</li>" for r in telemetry.retry_reasons])
                retry_reasons_section = HTML_RETRY_REASONS_SECTION.format(
                    retry_reasons_list=reasons_list
                )
            retry_section = HTML_RETRY_SECTION.format(
                retry_count=telemetry.retry_count,
                total_retry_delay_ms=telemetry.total_retry_delay_ms or 0,
                retry_reasons_section=retry_reasons_section,
            )
        
        # Build error section if applicable
        error_section = ""
        if telemetry.is_error():
            stack_trace_section = ""
            if telemetry.error_stack_trace:
                stack_trace_section = HTML_STACK_TRACE.format(
                    error_stack_trace=telemetry.error_stack_trace.replace("<", "&lt;").replace(">", "&gt;")
                )
            error_section = HTML_ERROR_SECTION.format(
                error_type=telemetry.error_type or "-",
                error_message=telemetry.error_message or "-",
                stack_trace_section=stack_trace_section,
            )
        
        # Format error category
        error_category_display = telemetry.error_category or "-"
        
        # Build results section
        results_section = ""
        if telemetry.results:
            results_list = []
            for r in telemetry.results[:10]:
                results_list.append(HTML_RESULT_ITEM.format(
                    title=r.get("title", "-"),
                    link=r.get("link", "-"),
                    content=(r.get("content", "") or "")[:200],
                ))
            results_section = HTML_RESULTS_SECTION.format(
                count=len(telemetry.results),
                results_list="".join(results_list),
            )
        
        # Build raw response section
        raw_response_section = ""
        if telemetry.raw_response:
            truncated_badge = ""
            if telemetry.raw_response_truncated:
                truncated_badge = '<span class="badge badge-warning">Truncated</span>'
            
            raw_response_section = HTML_RAW_RESPONSE.format(
                truncated_badge=truncated_badge,
                raw_response=json.dumps(telemetry.raw_response, indent=2, ensure_ascii=False).replace("<", "&lt;").replace(">", "&gt;"),
            )
        
        content = HTML_TELEMETRY_DETAIL.format(
            query=telemetry.query,
            status=telemetry.status,
            badge_class=badge_class,
            error_category=error_category_display,
            results_count=telemetry.results_count,
            created_at=telemetry.created_at.strftime("%Y-%m-%d %H:%M:%S") if telemetry.created_at else "-",
            user_id=telemetry.user_id or "-",
            session_id=telemetry.session_id or "-",
            retry_section=retry_section,
            error_section=error_section,
            total_duration_ms=telemetry.total_duration_ms or "-",
            init_duration_ms=telemetry.init_duration_ms or "-",
            tools_list_duration_ms=telemetry.tools_list_duration_ms or "-",
            search_call_duration_ms=telemetry.search_call_duration_ms or "-",
            total_retry_delay_ms=telemetry.total_retry_delay_ms or "-",
            provider_name=telemetry.provider_name or "-",
            tool_used=telemetry.tool_used or "-",
            http_status_code=telemetry.http_status_code or "-",
            api_session_id=telemetry.api_session_id or "-",
            results_section=results_section,
            raw_response_section=raw_response_section,
        )
        
        html = HTML_BASE.format(content=content, nav_users="", nav_telemetry="active")
        return web.Response(text=html, content_type="text/html")

    def _format_telemetry_row(self, telemetry) -> str:
        """Format a telemetry record as a table row."""
        badge_class = {
            "success": "badge-success",
            "error": "badge-error",
            "timeout": "badge-error",
            "empty": "badge-warning",
        }.get(telemetry.status, "badge-info")
        
        # Format error category with color coding
        error_category = "-"
        if telemetry.error_category:
            category_colors = {
                "TRANSIENT": "badge-warning",
                "AUTHENTICATION": "badge-error",
                "QUOTA": "badge-error",
                "INVALID_REQUEST": "badge-info",
                "SERVICE_ERROR": "badge-error",
                "INVALID_RESPONSE": "badge-warning",
            }
            cat_class = category_colors.get(telemetry.error_category, "badge-info")
            error_category = f'<span class="badge {cat_class}">{telemetry.error_category}</span>'
        
        # Format retry info
        retry_info = "-"
        if telemetry.retry_count and telemetry.retry_count > 0:
            retry_info = f'<span class="badge badge-warning">{telemetry.retry_count} retries</span>'
        
        return HTML_TELEMETRY_ROW.format(
            id=telemetry.id,
            created_at=telemetry.created_at.strftime("%Y-%m-%d %H:%M") if telemetry.created_at else "-",
            query=telemetry.query[:50] + ("..." if len(telemetry.query) > 50 else ""),
            status=telemetry.status,
            badge_class=badge_class,
            results_count=telemetry.results_count,
            duration=telemetry.total_duration_ms or "-",
            error_category=error_category,
            retry_info=retry_info,
        )

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
        except web.HTTPFound:
            raise  # Re-raise HTTP redirects
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
        except web.HTTPFound:
            raise  # Re-raise HTTP redirects
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
        except web.HTTPFound:
            raise  # Re-raise HTTP redirects
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
        except web.HTTPFound:
            raise  # Re-raise HTTP redirects
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
