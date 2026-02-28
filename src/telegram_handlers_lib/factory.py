"""Factory for creating Telegram handler services."""

import logging
from typing import TYPE_CHECKING

from telegram_handlers_lib.base import TelegramHandlerService

if TYPE_CHECKING:
    from nergal.config import Settings
    from nergal.dialog.manager import DialogManager
    from stt_lib.base import BaseSTTProvider


def create_handler_service(
    dialog_manager: "DialogManager",
    settings: "Settings",
    stt_provider: "BaseSTTProvider | None" = None,
) -> TelegramHandlerService:
    """Create a Telegram handler service instance.

    This factory function creates a configured handler service that can
    process Telegram updates. The service accepts all its dependencies
    via constructor for proper dependency injection.

    Args:
        dialog_manager: Dialog manager for processing messages.
        settings: Application settings configuration.
        stt_provider: Optional STT provider for voice messages.

    Returns:
        Configured Telegram handler service instance.

    Example:
        >>> from telegram_handlers_lib import create_handler_service
        >>>
        >>> handler_service = create_handler_service(
        ...     dialog_manager=my_dialog_manager,
        ...     settings=my_settings,
        ...     stt_provider=my_stt_provider
        ... )
        >>>
        >>> # Register handlers with Telegram app
        >>> from telegram.ext import CommandHandler, MessageHandler, filters
        >>> app.add_handler(CommandHandler("start", handler_service.start_command))
        >>> app.add_handler(CommandHandler("help", handler_service.help_command))
        >>> app.add_handler(MessageHandler(filters.TEXT, handler_service.handle_message))
        >>> app.add_handler(MessageHandler(filters.VOICE, handler_service.handle_voice))
    """
    logger = logging.getLogger(__name__)
    logger.info("Creating TelegramHandlerService")

    return TelegramHandlerService(
        dialog_manager=dialog_manager,
        settings=settings,
        stt_provider=stt_provider,
    )
