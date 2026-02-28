"""Main entry point for the Telegram bot."""

# Suppress pydub SyntaxWarning for invalid escape sequences (third-party library issue)
# Must be done before any imports that trigger pydub loading
import warnings

warnings.filterwarnings("ignore", message=".*invalid escape sequence.*", category=SyntaxWarning, module="pydub")

import logging
import re

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from nergal.config import get_settings
from nergal.container import Container, get_container, init_container
from nergal.dialog import DialogManager
from stt_lib import BaseSTTProvider
from web_search_lib.providers import ZaiMcpHttpSearchProvider


class HttpxLogFilter(logging.Filter):
    """Filter for httpx logs that suppresses successful requests but keeps 4XX errors."""

    _http_status_pattern = re.compile(r'"HTTP/\d\.\d (\d{3})')

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records based on HTTP status code.

        Args:
            record: The log record to filter.

        Returns:
            True if the record should be logged, False to suppress.
        """
        if record.levelno != logging.INFO:
            return True

        message = record.getMessage()
        match = self._http_status_pattern.search(message)

        if match:
            status_code = int(match.group(1))
            return 400 <= status_code < 500

        return True


def configure_logging(log_level: str) -> None:
    """Configure logging for the application.

    Args:
        log_level: The logging level to use.
    """
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # Suppress verbose HTTP logs from httpx
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.INFO)
    httpx_logger.addFilter(HttpxLogFilter())
    logging.getLogger("httpcore").setLevel(logging.WARNING)


class BotApplication:
    """Telegram bot application with singleton pattern.

    Manages dialog manager and web search provider lifecycle.
    This class now delegates to the DI container for dependency management.
    """

    _instance: "BotApplication | None" = None

    def __init__(self) -> None:
        """Initialize the bot application."""
        self._container: Container | None = None
        self._logger = logging.getLogger(__name__)

    @classmethod
    def get_instance(cls) -> "BotApplication":
        """Get the singleton instance of the bot application."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def container(self) -> Container:
        """Get the DI container instance."""
        if self._container is None:
            self._container = get_container()
        return self._container

    @property
    def dialog_manager(self) -> DialogManager:
        """Get or create the dialog manager instance from DI container."""
        return self.container.dialog_manager()

    @property
    def web_search_provider(self) -> ZaiMcpHttpSearchProvider | None:
        """Get or create the web search provider instance from DI container."""
        return self.container.web_search_provider()

    @property
    def stt_provider(self) -> BaseSTTProvider | None:
        """Get or create the STT provider instance from DI container."""
        return self.container.stt_provider()

    @property
    def _settings(self):
        """Get settings from DI container."""
        return self.container.settings()

    async def initialize_memory(self) -> None:
        """Initialize the memory service."""
        # Memory service was removed - no-op
        self._logger.info("Memory service disabled (removed)")


def main() -> None:
    """Start the bot."""
    # Configure logging first
    configure_logging(get_settings().log_level)
    logger = logging.getLogger(__name__)

    # Initialize DI container
    container = init_container()
    settings = container.settings()

    if not settings.llm.api_key:
        logger.warning("LLM_API_KEY is not set. Bot will not be able to generate AI responses.")

    # Initialize bot application
    app = BotApplication.get_instance()

    # Pre-initialize dialog manager
    _ = app.dialog_manager

    # Pre-load Whisper model if STT is enabled to avoid timeout on first transcription
    if settings.stt.enabled:
        stt_provider = app.stt_provider
        if stt_provider is not None:
            logger.info("Pre-loading Whisper model...")
            stt_provider.preload_model()
            logger.info("Whisper model pre-loaded successfully")

    # Initialize memory service (async, in event loop)
    async def post_init(_application: Application) -> None:
        """Initialize async resources after application is ready."""
        await app.initialize_memory()

    async def post_shutdown(_application: Application) -> None:
        """Cleanup async resources on shutdown."""
        pass

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Get handler service from DI container
    handler_service = container.handler_service()

    # Register handlers
    application.add_handler(CommandHandler("start", handler_service.start_command))
    application.add_handler(CommandHandler("help", handler_service.help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handler_service.handle_message)
    )

    # Add voice message handler if STT is enabled
    if settings.stt.enabled:
        application.add_handler(MessageHandler(filters.VOICE, handler_service.handle_voice))
        logger.info("Voice message handler registered")

    logger.info("Starting bot")
    application.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()
