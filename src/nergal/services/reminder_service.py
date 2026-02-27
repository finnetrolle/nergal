"""Reminder service for sending scheduled notifications.

This module provides a service that checks for pending reminders and
sends notifications to users at their scheduled times.
Supports general-purpose reminders.
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from telegram import Bot
from telegram.ext import Application

from nergal.database.repositories import GeneralReminderRepository

if TYPE_CHECKING:
    from nergal.database.models import GeneralReminder
    from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for sending scheduled reminders.

    This service is designed to be called periodically (e.g., every minute)
    to check for reminders that need to be sent and send them to users.
    Handles general-purpose reminders.

    Attributes:
        _general_repo: Repository for general reminders.
        _bot: Telegram bot instance for sending messages.
    """

    def __init__(
        self,
        general_repo: GeneralReminderRepository | None = None,
        bot: Bot | None = None,
    ) -> None:
        """Initialize reminder service.

        Args:
            general_repo: Repository for general reminders.
            bot: Telegram bot instance for sending messages.
        """
        self._general_repo = general_repo
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
        1. Gets all reminders that match the current time (general)
        2. Sends notification messages to users
        3. Updates the last_sent_at timestamp

        Returns:
            Number of reminders successfully sent.
        """
        if self._bot is None:
            logger.warning("Bot not set, cannot send reminders")
            return 0

        current_time = datetime.now(timezone.utc)
        sent_count = 0

        # Check general reminders
        if self._general_repo:
            try:
                pending_general = await self._general_repo.get_pending_reminders(current_time)
                for reminder, chat_id in pending_general:
                    try:
                        await self._send_general_reminder(reminder, chat_id)
                        sent_count += 1
                        logger.info(
                            "Sent general reminder to user %s at %s",
                            reminder.user_id,
                            reminder.reminder_time,
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to send general reminder to user %s: %s",
                            reminder.user_id,
                            e,
                            exc_info=True,
                        )
            except Exception as e:
                logger.error(f"Failed to get pending general reminders: {e}", exc_info=True)

        if sent_count > 0:
            logger.debug("Sent %d reminder(s) at %s", sent_count, current_time.isoformat())

        return sent_count

    async def _send_general_reminder(
        self,
        reminder: "GeneralReminder",
        chat_id: int,
    ) -> None:
        """Send a general reminder notification to a user.

        Args:
            reminder: The general reminder to send.
            chat_id: Telegram chat ID to send the message to.
        """
        # Build message from reminder data
        title = reminder.title
        description = f"\n\n{reminder.description}" if reminder.description else ""

        message = f"⏰ <b>Напоминание: {title}</b>{description}"

        # Use HTML for formatting
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
            general_repo = container.general_reminder_repository()

            service = ReminderService(general_repo, context.bot)
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
        name="general_reminders",
    )

    logger.info("Reminder job scheduled every %d seconds", interval_seconds)
