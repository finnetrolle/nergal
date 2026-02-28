"""telegram_handlers_lib - A reusable Telegram bot handlers library.

This library provides a clean, independent interface for handling
Telegram bot updates (commands, messages, voice). It's designed to be reusable
across different applications without external dependencies on the main app.

The library uses dependency injection pattern, allowing you to pass all required
dependencies (dialog_manager, settings, stt_provider) via constructor.

Example:
    >>> from telegram_handlers_lib import create_handler_service
    >>>
    >>> # Create handler service
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

Features:
    - Command handlers (/start, /help)
    - Text message handlers with group chat filtering
    - Voice message handlers with STT transcription
    - Bot mention detection and cleaning
    - Proper dependency injection pattern

Configuration:
    The handler service requires the following dependencies:
    - dialog_manager: For processing messages through the dialog system
    - settings: Application configuration (must have group_chat, stt sections)
    - stt_provider: Optional STT provider for voice message transcription
"""

from telegram_handlers_lib.base import TelegramHandlerService
from telegram_handlers_lib.factory import create_handler_service

__version__ = "0.1.0"

__all__ = [
    # Core
    "TelegramHandlerService",
    "create_handler_service",
]
