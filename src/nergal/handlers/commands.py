"""Telegram bot command handlers.

This module contains all command handlers for bot (/start, /help, /status, etc.).
"""

from telegram import Update
from telegram.ext import ContextTypes

from nergal.auth import check_user_authorized
from nergal.monitoring import get_health_checker, run_health_checks


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if update.message:
        await update.message.reply_text("Привет! Я бот Sil. Напиши мне вопрос, и я постараюсь ответить!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if update.message:
        await update.message.reply_text("Просто напиши мне сообщение, и я отвечу с помощью AI!")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command to show bot health."""
    if not update.message:
        return

    # Import here to avoid circular imports
    from nergal.main import BotApplication

    app = BotApplication.get_instance()
    checker = get_health_checker()

    # Run health checks
    await run_health_checks(
        llm_provider=app.dialog_manager._llm_provider if app._container else None,
        bot_application=app,
        web_search_provider=app.web_search_provider,
        stt_provider=app.stt_provider,
    )

    health = checker.to_dict()
    status_emoji = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}

    status_text = f"{status_emoji.get(health['status'], '❓')} Статус: {health['status']}\n\n"

    for name, component in health.get("components", {}).items():
        emoji = status_emoji.get(component["status"], "❓")
        status_text += f"{emoji} {name}: {component.get('message', component['status'])}\n"

    if "uptime_seconds" in health:
        uptime = int(health["uptime_seconds"])
        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)
        uptime_str = f"{days}д {hours}ч {minutes}м" if days else f"{hours}ч {minutes}м"
        status_text += f"\n⏱ Uptime: {uptime_str}"

    await update.message.reply_text(status_text)
