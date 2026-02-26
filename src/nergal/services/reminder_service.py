"""Reminder service for sending scheduled health notifications.

This module provides a service that checks for pending reminders and
sends notifications to users at their scheduled times.
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from telegram import Bot
from telegram.ext import Application

from nergal.database.repositories import HealthMetricsRepository

if TYPE_CHECKING:
    from nergal.database.models import HealthReminder
    from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for sending scheduled health reminders.
    
    This service is designed to be called periodically (e.g., every minute)
    to check for reminders that need to be sent and send them to users.
    
    Attributes:
        _health_repo: Repository for health metrics and reminders.
        _bot: Telegram bot instance for sending messages.
    """
    
    # Reminder messages by type (HTML formatting for reliability)
    REMINDER_MESSAGES = {
        "blood_pressure": (
            "⏰ <b>Пора измерить давление!</b>\n\n"
            "Не забудьте сделать три измерения для точности.\n\n"
            "После измерений отправьте результаты в формате:\n"
            "<code>120/80 125/82 122/78</code>\n\n"
            "💊 Берегите своё здоровье!"
        ),
        "medication": (
            "💊 <b>Напоминание о приёме лекарств</b>\n\n"
            "Пора принять назначенные препараты.\n\n"
            "Следуйте инструкции вашего врача."
        ),
        "weight": (
            "⚖️ <b>Пора взвеситься!</b>\n\n"
            "Регулярное отслеживание веса помогает контролировать здоровье."
        ),
    }
    
    # Default message for unknown reminder types
    DEFAULT_MESSAGE = "⏰ <b>Напоминание</b>\n\nПора выполнить запланированное действие."
    
    def __init__(
        self,
        health_repo: HealthMetricsRepository,
        bot: Bot | None = None,
    ) -> None:
        """Initialize the reminder service.
        
        Args:
            health_repo: Repository for health metrics and reminders.
            bot: Telegram bot instance for sending messages.
        """
        self._health_repo = health_repo
        self._bot = bot
    
    def set_bot(self, bot: Bot) -> None:
        """Set the Telegram bot instance.
        
        Args:
            bot: Telegram bot instance.
        """
        self._bot = bot
    
    async def check_and_send_reminders(self) -> int:
        """Check for pending reminders and send them.
        
        This method:
        1. Gets all reminders that match the current time
        2. Sends notification messages to users
        3. Updates the last_sent_at timestamp
        
        Returns:
            Number of reminders successfully sent.
        """
        if self._bot is None:
            logger.warning("Bot not set, cannot send reminders")
            return 0
        
        current_time = datetime.now(timezone.utc)
        
        try:
            pending = await self._health_repo.get_pending_reminders(current_time)
        except Exception as e:
            logger.error(f"Failed to get pending reminders: {e}", exc_info=True)
            return 0
        
        if not pending:
            logger.debug("No pending reminders at %s", current_time.isoformat())
            return 0
        
        sent_count = 0
        
        for reminder, chat_id in pending:
            try:
                await self._send_reminder(reminder, chat_id)
                sent_count += 1
                logger.info(
                    "Sent reminder to user %s at %s",
                    reminder.user_id,
                    reminder.reminder_time,
                )
            except Exception as e:
                logger.error(
                    "Failed to send reminder to user %s: %s",
                    reminder.user_id,
                    e,
                    exc_info=True,
                )
                # Note: last_sent_at was already updated atomically when claiming
                # the reminder. This is acceptable - we'd rather skip one reminder
                # than risk sending duplicates.
        
        return sent_count
    
    async def _send_reminder(
        self,
        reminder: "HealthReminder",
        chat_id: int,
    ) -> None:
        """Send a reminder notification to a user.
        
        Args:
            reminder: The reminder to send.
            chat_id: Telegram chat ID to send the message to.
        """
        message = self.REMINDER_MESSAGES.get(
            reminder.reminder_type,
            self.DEFAULT_MESSAGE,
        )
        
        # Use HTML for formatting (more reliable than Markdown)
        await self._bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="HTML",
        )
    
    @staticmethod
    async def check_reminders_job(context: "ContextTypes.DEFAULT_TYPE") -> None:  # type: ignore[name-defined]
        """Job callback for periodic reminder checking.
        
        This is designed to be used with telegram.ext.JobQueue.
        
        Args:
            context: Telegram bot context containing the application.
        """
        from nergal.container import get_container
        
        try:
            container = get_container()
            health_repo = container.health_metrics_repository()
            
            service = ReminderService(health_repo, context.bot)
            sent = await service.check_and_send_reminders()
            
            if sent > 0:
                logger.info("Sent %d reminder(s)", sent)
                
        except Exception as e:
            logger.error(f"Reminder job failed: {e}", exc_info=True)


def setup_reminder_jobs(application: Application, interval_seconds: int = 60) -> None:
    """Set up periodic reminder checking jobs.
    
    Args:
        application: Telegram application instance.
        interval_seconds: How often to check for reminders (default: 60 seconds).
    """
    job_queue = application.job_queue
    if job_queue is None:
        logger.warning("JobQueue not available, reminders will not work")
        return
    
    # Run the reminder check job every minute
    job_queue.run_repeating(
        ReminderService.check_reminders_job,
        interval=interval_seconds,
        first=10,  # Start 10 seconds after bot init
        name="health_reminders",
    )
    
    logger.info("Reminder job scheduled every %d seconds", interval_seconds)
