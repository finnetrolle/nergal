"""Telegram bot command handlers.

This module contains all command handlers for the bot (/start, /help, /status, etc.).
"""

from telegram import Update
from telegram.ext import ContextTypes

from nergal.auth import check_user_authorized
from nergal.monitoring import get_health_checker, get_logger, run_health_checks


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


async def todoist_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /todoist_token command to set Todoist API token."""
    if not update.message or not update.message.from_user:
        return

    user_id = update.message.from_user.id

    # Check if token was provided
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "🔗 **Подключение Todoist**\n\n"
            "Для подключения Todoist отправьте команду с вашим API токеном:\n"
            "`/todoist_token ВАШ_ТОКЕН`\n\n"
            "📌 Получить токен можно на: [todoist.com/app/settings/integrations/developer](https://todoist.com/app/settings/integrations/developer)\n\n"
            "⚠️ Токен хранится безопасно и используется только для работы с вашими задачами.",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        return

    token = context.args[0].strip()

    # Validate token format (basic check)
    if len(token) < 20:
        await update.message.reply_text("❌ Неверный формат токена. Проверьте, что вы скопировали токен полностью.")
        return

    try:
        from nergal.database.repositories import UserIntegrationRepository
        from nergal.integrations.todoist import TodoistService

        # Test the token
        service = TodoistService(api_token=token)
        is_valid = await service.test_connection()
        await service.close()

        if not is_valid:
            await update.message.reply_text("❌ Не удалось подключиться к Todoist. Проверьте правильность токена.")
            return

        # Store the token
        repo = UserIntegrationRepository()
        existing = await repo.get_by_user_and_type(user_id, "todoist")

        if existing:
            await repo.update(user_id, "todoist", encrypted_token=token, is_active=True)
        else:
            await repo.create(user_id, "todoist", encrypted_token=token)

        await update.message.reply_text(
            "✅ Todoist успешно подключён!\n\n"
            "Теперь вы можете:\n"
            "• «Покажи мои задачи»\n"
            "• «Задачи на сегодня»\n"
            "• «Создай задачу Купить молоко завтра»\n"
            "• «Просроченные задачи»\n\n"
            "💡 Попробуйте написать мне что-нибудь про задачи!"
        )

        # Delete the message with token for security
        try:
            await update.message.delete()
        except Exception:
            pass  # May fail if bot doesn't have permission

    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to setup Todoist integration: {e}")
        await update.message.reply_text("❌ Произошла ошибка при подключении. Попробуйте позже.")


async def todoist_disconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /todoist_disconnect command to disconnect Todoist."""
    if not update.message or not update.message.from_user:
        return

    user_id = update.message.from_user.id

    try:
        from nergal.database.repositories import UserIntegrationRepository

        repo = UserIntegrationRepository()
        deleted = await repo.delete(user_id, "todoist")

        if deleted:
            await update.message.reply_text("✅ Todoist отключён. Ваши данные удалены из базы.")
        else:
            await update.message.reply_text("ℹ️ Todoist не был подключён.")

    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to disconnect Todoist: {e}")
        await update.message.reply_text("❌ Произошла ошибка при отключении. Попробуйте позже.")
